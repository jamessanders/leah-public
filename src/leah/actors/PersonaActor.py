import asyncio
from datetime import datetime
import json
import traceback
from typing import List
from leah.actions import Actions
from leah.llm.LlmConnector import LlmConnector
from leah.llm.StreamProcessor import StreamProcessor
from leah.tools.tools import getTools
from leah.utils.ChannelContextManager import ChannelContextManager, ContextType
from leah.utils.FileManager import FileManager
from leah.utils.Message import MessageType
from leah.utils.SubscriptionService import SubscriptionService
from leah.utils.TokenCounter import TokenCounter, TokenLimiter
from leah.utils.PubSub import PubSub, Message
from leah.config.LocalConfigManager import LocalConfigManager
from leah.llm.ChatApp import ChatApp
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
import random
import time
from queue import Queue
from threading import Thread
from langchain_mcp_adapters.client import MultiServerMCPClient
from src.leah.llm.McpConnector import McpToolsSingleton

class ToolContent:
    def __init__(self, channel_id: str):
        self.channel_id = channel_id

class PersonaActor:

    def __init__(self, persona: str):
        self._processing_queue = Queue()
        self.persona = persona
        self.handle = "@" + persona
        self._subscribed_channels = set()
        self._pubsub = PubSub.get_instance()
        self.file_manager = FileManager(LocalConfigManager("default", self.persona))
        self.memories_path = f"_{self.persona}_memories.txt"
        self.channel_seen_history = {}
        self.seen_ids = []
        self.config_manager = LocalConfigManager("default", "default")
        self.processing_message = None

        self.tool_history = {}
        self.llm_response_history = {}
        self.messages_sent = {}

        ## MCP tools are not working yet
        ## self.mcp_tools = McpToolsSingleton.get_instance().get_tools()

    def format_message(self, message: Message):
        if message.from_user == self.handle:
            return AIMessage(message.content, id=message.id)
        else:
            return HumanMessage(message.from_user + " said: " + message.content + " in channel " + message.via_channel + " (Sent " + message.relative_sent_at() + ")", id=message.id)


    def build_channel_history(self, channel: str):
        token_counter = TokenLimiter(5000)
        channel_messages = self._pubsub.get_channel_messages(channel)
       
        if channel_messages and len(channel_messages) > 0:
            self.channel_seen_history[channel] = channel_messages[-1].sent_at

        new_channel_messages = []
        for message in channel_messages:
            if message.id not in self.messages_sent.get(channel, []):  
                new_channel_messages.append(message)

        channel_messages = new_channel_messages

        history = []

        llm_messages = [(message.sent_at, self.format_message(message)) for message in channel_messages] + self.llm_response_history.get(channel, [])
        llm_messages.sort(key=lambda x: float(x[0]), reverse=True)
        

        for (sent_at, message) in llm_messages:
            history.append(message)



        history.reverse()
        
        while not isinstance(history[0], HumanMessage):
            history.pop(0)

        print("PHASE 1")
        print("--------------------------------")
        for item in history:
            print(item.__class__.__name__ + ": " + str(item.text()[0:100]))
        print("--------------------------------")
        
        new_history = []
        for item in history:
            if isinstance(item, AIMessage) and item.tool_calls:
                tool_messages = []
                for tool_call in item.tool_calls:
                    if tool_call.get("id", "") in self.tool_history:
                        tool_messages.append(self.tool_history[tool_call.get("id", "")])
                # append the tool_messages to the history after the item
                new_history.append(item)
                new_history.extend(tool_messages)
            else:
                new_history.append(item)

        new_history.reverse()

        trimmed_history = []
        for item in new_history:
            if not token_counter.count(item.text()):
                break
            else:
                trimmed_history.append(item)

        trimmed_history.reverse()

        last = None
        final_history = []
        for item in trimmed_history:
            if isinstance(item, ToolMessage):
                if not last or not last.tool_calls or item.tool_call_id not in [x.get("id", "") for x in last.tool_calls]:
                    continue   
            final_history.append(item)
            last = item

        while not isinstance(final_history[0], HumanMessage):
            final_history.pop(0)

        print("--------------------------------")
        for item in final_history:
            print(item.__class__.__name__ + ": " + str(item.text()[0:100]))
            if isinstance(item, AIMessage) and item.tool_calls:
                for tool_call in item.tool_calls:
                    print(" - " + tool_call.get("id", "") + " " + tool_call.get("function", {}).get("name", ""))
            if isinstance(item, ToolMessage):
                print(" + " + item.tool_call_id)
        print("--------------------------------")
        
        return final_history

    def get_context_items(self):
        channel_context = ChannelContextManager()
        items = channel_context.get_context(self.processing_message.via_channel) or []
        out = []
        print("Context items:")
        print("--------------------------------")
        print(items)
        print("--------------------------------")
        for id, context_type, context in items:
            if context_type == ContextType.NOTE:
                out.append(SystemMessage(context.get("text", "")))
        return out

    def get_memories(self):
        token_counter = TokenCounter(3000)
        file = self.file_manager.get_file(self.memories_path)
        if file:
            if isinstance(file, bytes):
                file = file.decode('utf-8')
            for line in file.split("\n"):
                token_counter.feed(f"{line}\n")
            return "\n".join(token_counter.tail())
        else:
            return ""
        
    def update_memories(self, response: str):
        connector = self.get_llm_connector(self.processing_message)
        new_memories = connector.query(self.get_memories() + "\n\n" + response.replace("! done !", "").strip() + "\n\nSummarize the content above, use first person past tense, skip prose.")
        if new_memories:
            self.file_manager.put_file(self.memories_path, new_memories)

    def get_llm_connector(self, message: Message):
        connector = LlmConnector(self.config_manager, self.persona)
        connector.bind_tools(getTools(self.persona, message.via_channel))
        ## MCP tools are not working yet
        ## connector.bind_tools(self.mcp_tools)
        return connector

    def get_persona_system_content(self):
        return SystemMessage(self.config_manager.get_system_content(self.persona))
    
    def get_tools_system_content(self):
        return SystemMessage("")
        #return SystemMessage(Actions.Actions(self.config_manager, self.persona, "", self).get_actions_prompt())

    def response_loop(self, message: Message, depth: int = 0):
        self.processing_message = message
        max_depth = 2
        if depth > max_depth:
            print("Max depth reached, stopping")
            self.hangup(message.via_channel)
            return

        print(" Processing request to " + self.handle + " in channel " + message.via_channel)

        if (message.type == MessageType.SYSTEM):
            print("Skipping system message")
            self.hangup(message.via_channel)
            return
        if (message.from_user == self.handle):
            print("Skipping message from self")
            return
        if (message.type == MessageType.HANGUP):
            print("Skipping hangup message")
            return
        if message.via_channel in self.channel_seen_history and message.sent_at < self.channel_seen_history[message.via_channel]:
            print("Skipping message because we have already seen it")
            self.hangup(message.via_channel)
            return

        print("Processing message: " + str(message))

        is_admin = False
        if message.type == MessageType.CHANNEL:
            is_admin = SubscriptionService.get_instance().is_admin(self.handle, message.via_channel)
            if not self.handle in message.content and not is_admin:
                print("Skipping message because we are not mentioned and we are not an admin")
                self.hangup(message.via_channel)
                return
            else:
                sleep_time = random.uniform(1, 3)   
                time.sleep(sleep_time)
     
        self.system_message(self.persona + " is thinking about responding to message " + message.content + " from " + message.from_user + " on " + message.via_channel + " (" + message.id + ")")
        
        connector = self.get_llm_connector(message)

        memories = SystemMessage("These are your most recent memories: \n\n" + self.get_memories())

        base_history = [self.get_persona_system_content(), self.get_tools_system_content(), memories] + self.get_context_items() + self.build_channel_history(message.via_channel)
        print("Base history:")
        for item in base_history:
            print(item.__class__.__name__ + ": " + str(item.text()[0:100]))
    
        query = self.query_template(message.content)

        response = ""
        tool_attempts = []


        full_query = base_history + [HumanMessage(query)]
        while True:
            for type,content in connector.stream(full_query):
                if type == "content":
                    response += content + "\n"
                    if "! no action needed !" in content:
                        print("Skipping response because it is a no action needed message")
                        if content.replace("! no action needed !", "").strip() != "":
                            self._pubsub.publish(message.via_channel, Message(self.handle, message.via_channel, content.replace("! no action needed !", "").strip(), MessageType.CHANNEL))
                        self.system_message(self.persona + " will not take any action on this message")
                        self.hangup(message.via_channel)
                        return
                    if message.via_channel not in self.messages_sent:
                        self.messages_sent[message.via_channel] = []
                    output_message = Message(self.handle, message.via_channel, content, message.type)
                    self.messages_sent[message.via_channel].append(output_message.id)
                    self._pubsub.publish(output_message.via_channel, output_message)
                    
                if type == "tool_attempt":
                    tool_attempts.append(content)
                if type == "system":
                    self.system_message(content)

            self.tool_history = {}
            self.llm_response_history = {}

            for item in connector.history:
                if isinstance(item, ToolMessage):  
                    self.tool_history[item.tool_call_id] = item
                if isinstance(item, AIMessage):
                    if not message.via_channel in self.llm_response_history:
                        self.llm_response_history[message.via_channel] = []
                    ## if item has sent_at, add it to the history
                    if hasattr(item, "sent_at"):
                        self.llm_response_history[message.via_channel].append((item.sent_at, item))
                   

            if "! continue !" in response:
                response = response.replace("! continue !", "").strip()
                full_query = connector.history + [HumanMessage("Please continue")]
                self.system_message("Continuing...")
                continue
            else:
                break

        self.update_memories(f"User {message.from_user} sent a message: {message.content}\n\nMy response: {response}")

        already_sent_dm = False
        for tool,args in tool_attempts:
            if tool == "MessageAction.send_direct_message" and args.get("handle", "") == message.from_user:
                already_sent_dm = True
                break

        
        self.hangup(message.via_channel)

    def system_message(self, content: str):
        self._pubsub.publish("#system", Message(self.handle, self.handle, content, MessageType.SYSTEM))

    def hangup(self, channel: str):
        self._pubsub.publish(channel, Message(self.handle, channel, "! hangup !", MessageType.HANGUP))

    def _handle_message(self,  message: Message):      
        self._processing_queue.put(message)

    def _thread_loop(self):
        try:
            while True:
                if not self._processing_queue.empty():
                    message = self._processing_queue.get()
                    if message.id in self.seen_ids:
                        print(" !! DUPLICATE MESSAGE !!")
                        continue
                    self.seen_ids.append(message.id)
                else:
                    time.sleep(0.1)
                    continue
                self.response_loop(message, 0)
        except Exception as e:
            print(e)
            traceback.print_exc()
            time.sleep(1)
            self._thread_loop()

    def listen(self):
        self._pubsub.subscribe(self.handle, self._handle_message)
        Thread(target=self._thread_loop).start()

    def query_template(self, query: str):
        return f"""
Respond to the user's query. If you do not have a response just say ! no action needed ! and nothing else. 
If you have used a tool and need to continue say ! continue !

    User Query:

        {query}
    
"""

    def _long_query_template(self, query: str):
         return f"""
    Query: {query}

    1. Task Identification and Role Clarification: Task Summary: Start by summarizing the task as described by the user. Identify the key elements: A, B, and C. Subject Matter Identification: Determine the subject matter related to the task. Ask the user: "I see that this task relates to [subject X]. Would you like me to assume the role of an expert in this area to provide relevant suggestions and guidance?" Role Confirmation: If the user agrees, acknowledge your role as a subject matter expert. If not, clarify the role they want you to take.

    2. Expert Suggestions and Refinement: Expert Insight: As an expert in [subject X], identify related ideas, potential considerations, or common challenges associated with tasks like A, B, and C. Present these insights to the user: "When addressing tasks like A, B, and C, it's common to consider the following aspects: 1) Thing 1, 2) Thing 2, 3) Thing 3." User Engagement: Ask the user: "Would these considerations be helpful in refining your task? Should we incorporate them?" Task Reframing: If the user agrees, reframe the task with the new considerations. Present the updated task to the user: "Based on your input, the task is now A, B, and C with considerations X, Y, and Z."

    3. Clarification and Confirmation: Process Outline: Summarize the reframed task and outline the steps you plan to take, including the expected results. Clearly state the goal: "Before proceeding, I will clarify each step with you to ensure alignment with your expectations." Iterative Feedback Loop: Engage in a feedback loop where you ask clarifying questions about the task, the expected outcomes, and any specific details the user wants to emphasize. Continue this process until you reach a "Very High" confidence level. Progress Tracking: Throughout this process, maintain a progress table that includes: Task/Step, Initial Understanding, Confidence Level, Clarifying Questions/Suggestions, Revised Understanding, and Updated Confidence Level.

    4.Final Check and Execution: Final Summary: Once the task is fully clarified, provide a final summary of the task, including any additional considerations and the steps you will take to complete it. User Confirmation: Ask the user for final confirmation: "Do you have anything more to add, or should I proceed with the task?" Execution: Only proceed with the task once you've reached a 95% confidence level in your understanding and execution plan.

    Do not stop working until all steps are completed!
    """
