from hashlib import sha256
import time
import uuid
import threading
from datetime import datetime
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, trim_messages, ToolMessage, ToolCall
from dotenv import load_dotenv
import os
from leah.config.GlobalConfig import GlobalConfig
from leah.utils.ConversationStore import ConversationStore
from leah.actions import Actions
from leah.config.LocalConfigManager import LocalConfigManager
import json
from leah.llm.StreamProcessor import StreamProcessor
import traceback
from langchain.callbacks.base import BaseCallbackHandler
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from typing import List, Optional, Union, Dict, Any
from langchain_core.language_models.llms import BaseLLM
import tiktoken
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

from leah.utils.PostOffice import PostOffice

def count_tokens(text: str) -> int:
    """Calculate num tokens for OpenAI with tiktoken package."""
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    num_tokens = len(encoding.encode(text))
    return num_tokens

class ChatApp:
    _rate_limiter_lock = threading.Lock()
    _last_request_times = {}  # Dictionary to store lists of request timestamps per connector
    
    @classmethod
    def _check_rate_limit(cls, connector_type: str) -> bool:
        """
        Check if we can make a request for this connector type based on rate limits.
        Returns True if request is allowed, False if we need to wait.
        """
        config = GlobalConfig()
        rate_limit = config.get_connector_rate_limit(connector_type)  # Requests per minute
        print(" - Checking rate limit for " + connector_type + " with rate limit " + str(rate_limit))
        with cls._rate_limiter_lock:
            current_time = time.time()
            # Initialize or get the list of request times for this connector
            if connector_type not in cls._last_request_times:
                cls._last_request_times[connector_type] = []
            
            # Remove timestamps older than 1 minute
            one_minute_ago = current_time - 60
            cls._last_request_times[connector_type] = [t for t in cls._last_request_times[connector_type] if t > one_minute_ago]

            print(" - We have made " + str(len(cls._last_request_times[connector_type])) + " requests in the last minute to " + connector_type)
            # Check if we've exceeded the rate limit
            if len(cls._last_request_times[connector_type]) >= rate_limit:
                return False
                
            # Add current request time and allow the request
            cls._last_request_times[connector_type].append(current_time)
            return True

    def __init__(self, config_manager: LocalConfigManager, persona: str = 'default', conversation_id: str = None, parent = None, channel_id: str = None):
        # Store config instance
        self.persona = persona
        self.config_manager = config_manager
        self.config = config_manager.get_config()
        self.history = []
        self.tool_ban_list = []
        self.conversation_id = conversation_id
        self.system_content = self.config_manager.get_system_content(persona)
        self.max_tokens = 10000
        self.conversation_store = ConversationStore(self.config_manager.get_file_manager())
        self.parent = parent
        self.children = []
        self.channel_id = channel_id
        if not self.system_content:
            self.system_content = ""
        if self.conversation_id:
            self.load_conversation_with_id(self.conversation_id)
        
        # Initialize the appropriate LLM based on connector type
        connector_type = self.config.get_connector_type(persona)
        self.connector_type = connector_type
        model = self.config.get_model(persona)
        temperature = self.config.get_temperature(persona)
        api_key = self.config.get_ollama_api_key(persona)
        base_url = self.config.get_ollama_url(persona)

        if connector_type == 'gemini':
            self.llm = ChatGoogleGenerativeAI(
                model=model,
                temperature=temperature,
                google_api_key=api_key
            )
        elif connector_type == 'openai':
            self.llm = ChatOpenAI(
                model=model,
                temperature=temperature,
                openai_api_key=api_key
            )
        elif connector_type == 'lmstudio':
            self.llm = ChatOpenAI(
                model=model,
                temperature=temperature,
                openai_api_key=api_key,
                base_url=base_url
            )
        else:  # local connector for Ollama/LMStudio
            self.llm = ChatOllama(
                model=model,
                temperature=temperature,
                base_url=base_url
            )

    def trimmer(self):
        return trim_messages(
            max_tokens=22000,
            strategy="last",
            token_counter=self.llm,
            include_system=True,
            allow_partial=False,
            start_on="human",
        )

    def get_watch_status(self):
        # Get all watched inboxes for this conversation
        watched_inboxes = self.conversation_store.get_watched_inboxes(self.conversation_id)
        
        post_office = PostOffice.get_instance()
        
        for inbox_id in watched_inboxes:
            if not post_office.has_inbox(inbox_id):
                self.conversation_store.remove_watched_inbox(self.conversation_id, inbox_id)
                continue
            if post_office.is_inbox_closed(inbox_id) and not post_office.has_messages(inbox_id):
                post_office.delete_inbox(inbox_id)
                self.conversation_store.remove_watched_inbox(self.conversation_id, inbox_id)
                continue
        
        watched_inboxes = self.conversation_store.get_watched_inboxes(self.conversation_id)
        
        # Count statistics
        total_inboxes = len(watched_inboxes)
        open_inboxes = 0
        closed_inboxes = 0

        for inbox_id in watched_inboxes:
            if post_office.has_inbox(inbox_id):
                if post_office.is_inbox_closed(inbox_id):
                    closed_inboxes += 1
                else:
                    open_inboxes += 1
            else:
                self.conversation_store.remove_watched_inbox(self.conversation_id, inbox_id)
                total_inboxes -= 1
                
        return {
            "total_inboxes": total_inboxes,
            "open_inboxes": open_inboxes,
            "closed_inboxes": closed_inboxes
        }

    def is_watching(self):
        watch_status = self.get_watch_status()
        return watch_status["total_inboxes"] > 0

    def is_watching_complete(self):
        watch_status = self.get_watch_status()
        return watch_status["closed_inboxes"] > 0 and watch_status["open_inboxes"] == 0

    def watch(self, timeout=10):
        if not self.is_watching():
            return
        inboxs = list(self.conversation_store.get_watched_inboxes(self.conversation_id))
        postoffice = PostOffice.get_instance()
        timeout = timeout/len(inboxs)
        for inbox in inboxs:
            for message in postoffice.stream_messages_till_closed_or_timeout(inbox, timeout):
                type, content, source = message.body
                yield (type, content, source)
            if postoffice.is_inbox_closed(inbox) and not postoffice.has_messages(inbox):
                inboxs.remove(inbox)
                postoffice.delete_inbox(inbox)

    def fork_conversation(self, query):
        quid = sha256(query.encode('utf-8') + "." + str(time.time())).hexdigest()
        app = ChatApp(self.config_manager, self.persona, quid, parent=self)
        app.history = self.history.copy()
        self.conversation_store.add_thread(self.conversation_id, quid)
        self.children.append(app)
        return app

    def load_conversation_with_id(self, conversation_id):
        self.conversation_id = conversation_id
        self.history = self.conversation_store.load_conversation(conversation_id)
        if not self.history:
            self.history = []
    
    def run_tool(self, run):
        persona = self.persona
        for type,message in run():
            if type == "feedback":
                query, callback = message
                app = ChatApp(self.config_manager, self.persona)
                response = ChatApp.unstream(app.stream(query, use_tools=False))
                yield from self.run_tool(lambda: callback(response))
            elif type == "conversate":
                query, callback, conversation_history = message
                app = ChatApp(self.config_manager, self.persona)
                app.set_conversation_history_from_dicts(conversation_history)
                response = ChatApp.unstream(app.stream(query, use_tools=False))
                yield from self.run_tool(lambda: callback(response))
            else:
                yield (type, message)
    
    def process_tool(self, tool, query):
        tool_name = "Unknown tool"
        try:
            try:
                self.tool_ban_list.append(tool)
                parsed_response = json.loads(tool.strip())
                tool_name = parsed_response.get("tool", "")
                tool_arguments = parsed_response.get("arguments", "{}")
            except Exception as e:
                error_message = f"An error occurred: {str(e)}\n"
                error_message += traceback.format_exc()
                yield ("system", self.persona + ': Invalid tool call')
                yield ("tool_response", (tool_name, "I attepted to use a tool but it returned a tool syntax error saying I must provide the tool name and arguments.  The tool call was: " + tool))
                return
            if isinstance(tool_arguments, str):
                try:
                    tool_arguments = json.loads(tool_arguments)
                except:
                    tool_arguments = {}
            if (not tool_name):
                yield ("system", self.persona + ': Invalid tool call')
                yield ("tool_response", (tool_name, "I attepted to use a tool but it returned a tool syntax error saying I must provide the tool name and arguments.  The tool call was: " + tool))
                return 
            self.config_manager.get_log_manager().log("tool", tool_name + " " + str(tool_arguments))
            yield ("tool_attempt", (tool_name, tool_arguments))
            actions = Actions.Actions(self.config_manager, self.persona, query, self)
            for type,message in self.run_tool(lambda: actions.run_tool(tool_name, tool_arguments)):
                if type == "result":
                    yield ("tool_response", (tool_name, message))
                else:
                    yield (type, message)
        except Exception as e:
            error_message = f"An error occurred: {str(e)}\n"
            error_message += traceback.format_exc()
            yield ("tool_response", (tool_name, error_message))
            print(error_message)
    
    def set_system_content(self, content):
        self.system_content = content
    
    def history_to_dicts(self, history=[]):
        if not history:
            history = self.history
        out = []
        for item in history:
            name = item.type
            content = item.text()
            if not content:
                content = "..."
            if name == 'ai':
                name = 'assistant'
            if name == 'human':
                name = 'user'
            out.append({"type": name, "content": content, "id": item.id, "hidden": item.name == "hidden"})
        return out
    
    def set_conversation_history_from_dicts(self, history):
        self.history = []
        for item in history:
            role = item.get("role", "system")
            content = item.get("content","...")
            hidden = item.get("hidden", False)
            if not content:
                content = "..."
            if role == "user":
                self.history.append(HumanMessage(content, id=item.get("id",""), name=(hidden and "hidden" or "user")))
            elif role == "assistant":
                self.history.append(AIMessage(content, id=item.get("id","")))
            elif role == "system":
                self.history.append(SystemMessage(content, id=item.get("id","")))
            elif role == "tool":
                self.history.append(ToolMessage(content, tool_call_id=item.get("tool_call_id","null_id"), id=item.get("id","")))
    
    def save_history(self):
        for item in self.history:
            if not item.id:
                item.id = str(uuid.uuid4())
        if self.conversation_id:
            self.conversation_store.save_conversation(self.conversation_id, self.history)

    def unstream(stream):
        full_content = ""
        for type, message in stream:
            if type == "content":
                full_content += message
        return full_content
    
    def tool_query_context_template(self, you_said, tool_said, query):
        return f"""
In regards to the following query:

{query}

You said the following:

{you_said}

{tool_said}

Please continue based on the above information or respond with "! done !" if all instructions have been completed.
        """

    def query(self, query, use_system_content=False):
        chain = self.llm | StrOutputParser()
        history = []
        if use_system_content:
            history.append(SystemMessage(self.system_content))
        history.append(HumanMessage(query))
        return "".join([content for content in chain.invoke(history)])
    

    def stream(self, user_input, use_tools=True, depth=0, wait_timeout=1, check_inboxes=False, require_reply=False, use_history=True, tool_responses=[], prevent_tool_execution=False, continuation=False):
        """
        Process user input and return chatbot response
        """
        responded = False
        if depth >= 10:
            use_tools = False
            return

        # Check rate limit for this connector type
        connector_type = self.config.get_connector_type(self.persona)
        while not self._check_rate_limit(connector_type):
            print(" !! Rate limit exceeded, waiting 1 second before checking again")
            time.sleep(1)  # Wait 1 second before checking again
            
        # Create the chain using runnables
        chain = self.llm | StrOutputParser()
        raw_content = ""
        full_content = ""
        think_stream_processor = StreamProcessor("<think>", "</think>")
        tool_stream_processor = StreamProcessor("```tool_code", "```")
        
        total_tokens = count_tokens(self.system_content)
        if (user_input):
            total_tokens += count_tokens(user_input)
        for message in self.history:
            total_tokens += count_tokens(message.text())
                    
        # Remove oldest messages if total tokens exceed max limit
        while total_tokens > self.max_tokens and len(self.history) > 0:
            # Remove oldest message
            removed_message = self.history.pop(0)
            # Recalculate total tokens
            total_tokens -= count_tokens(removed_message.text())
        
        final_input = user_input
        if tool_responses:
            final_input = self.tool_query_context_template("", "\n".join(tool_responses), user_input)

        input_message = HumanMessage(final_input)
        if (continuation):
            input_message = AIMessage(final_input)

        hm_id = str(uuid.uuid4())
        self.history.append(input_message)

        history = [x for x in self.history if x.type != "system"]
        system_content = self.system_content
        if use_tools:
            actions = Actions.Actions(self.config_manager, self.persona, final_input, history)
            actions_prompt = actions.get_actions_prompt()
            system_content = system_content + "\n\n" + actions_prompt
            
        history.insert(0, SystemMessage(system_content))

        for content in chain.invoke(use_history and history or [SystemMessage(system_content), input_message]):
            raw_content += content
            content = think_stream_processor.process_chunk(content)
            content = tool_stream_processor.process_chunk(content)
            if tool_stream_processor.matches and not prevent_tool_execution:
                for tool in tool_stream_processor.matches:
                    for type, message in self.process_tool(tool, user_input):
                        if type == "tool_response":
                            tool, message = message
                            yield ("content", message)
                            full_content += "\n" + message + "\n"
                        else:
                            yield (type, message)
            tool_stream_processor.reset()
            if content:
                full_content += content
                responded = True
                yield ("content", content)
        
        if full_content:
            ai_id = str(uuid.uuid4())
            history.append(AIMessage(full_content, id=ai_id))
            self.history.append(AIMessage(full_content, id=ai_id))
            self.save_history()            

        yield ("break","")