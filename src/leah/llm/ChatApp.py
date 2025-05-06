from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, trim_messages, ToolMessage
from dotenv import load_dotenv
import os
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

def count_tokens(text: str) -> int:
    """Calculate num tokens for OpenAI with tiktoken package."""
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    num_tokens = len(encoding.encode(text))
    return num_tokens

class ChatApp:
    def __init__(self, config_manager: LocalConfigManager, persona: str = 'default', conversation_id: str = None):
        # Store config instance
        self.persona = persona
        self.config_manager = config_manager
        self.config = config_manager.get_config()
        self.history = []
        self.tool_ban_list = []
        self.conversation_id = conversation_id
        self.system_content = self.config.get_system_content(persona)
        self.max_tokens = 22000
        self.conversation_store = ConversationStore(self.config_manager.get_file_manager())
        if not self.system_content:
            self.system_content = ""
        if self.conversation_id:
            self.load_conversation_with_id(self.conversation_id)
        
        # Initialize the appropriate LLM based on connector type
        connector_type = self.config.get_connector_type(persona)
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
        elif connector_type == 'chatgpt':
            self.llm = ChatOpenAI(
                model=model,
                temperature=temperature,
                openai_api_key=api_key
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
        try:
            if tool in self.tool_ban_list:
                return
            try:
                self.tool_ban_list.append(tool)
                parsed_response = json.loads(tool.strip())
                tool_name = parsed_response.get("action", "")
                tool_arguments = parsed_response.get("arguments", "{}")
            except Exception as e:
                error_message = f"An error occurred: {str(e)}\n"
                error_message += traceback.format_exc()
                yield ("system", 'Invalid tool call')
                yield ("tool_response", "That is not a valid tool call syntax.")
                return
            if isinstance(tool_arguments, str):
                try:
                    tool_arguments = json.loads(tool_arguments)
                except:
                    tool_arguments = {}
            print("Tool arguments: " + str(tool_arguments))
            if (not tool_name):
                yield ("system", 'Invalid tool call')
                yield ("tool_response", "That is not a valid tool call.")
                return 
            self.config_manager.get_log_manager().log("tool", tool_name + " " + str(tool_arguments))
            actions = Actions.Actions(self.config_manager, self.persona, query, self)
            for type,message in self.run_tool(lambda: actions.run_tool(tool_name, tool_arguments)):
                if type == "result":
                    yield ("tool_response", message)
                else:
                    yield (type, message)
        except Exception as e:
            error_message = f"An error occurred: {str(e)}\n"
            error_message += traceback.format_exc()
            print(error_message)
            yield ("tool_response", error_message)
    
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
            out.append({"type": name, "content": content})
        return out
    
    def set_conversation_history_from_dicts(self, history):
        self.history = []
        for item in history:
            role = item.get("role", "system")
            content = item.get("content","...")
            if not content:
                content = "..."
            if role == "user":
                self.history.append(HumanMessage(content))
            elif role == "assistant":
                self.history.append(AIMessage(content))
            elif role == "system":
                self.history.append(SystemMessage(content))
            elif role == "tool":
                self.history.append(ToolMessage(content, tool_call_id=item.get("tool_call_id","null_id")))
    
    def save_history(self):
        if self.conversation_id:
            self.conversation_store.save_conversation(self.conversation_id, self.history)

    def unstream(stream):
        full_content = ""
        for type, message in stream:
            if type == "content":
                full_content += message
        return full_content
    
    def stream(self, user_input, use_tools=True, depth=0):
        """
        Process user input and return chatbot response
        """
        if depth >= 10:
            use_tools = False
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
        
        # yield ("system", "Total tokens: " + str(total_tokens))
        
        self.history.append(HumanMessage(user_input))
        
        history = [x for x in self.history if x.type != "system"]
        system_content = self.system_content
        
        if use_tools:
            actions = Actions.Actions(self.config_manager, self.persona, user_input, history)
            actions_prompt = actions.get_actions_prompt()
            system_content = system_content + "\n\n" + actions_prompt
            
        history.insert(0, SystemMessage(system_content))

        """
        print("-"*72)   
        for item in history:
            print(item.type + " history item: " + item.text())
        print("-"*72)
        """

        for content in chain.invoke(history):
            raw_content += content
            content = think_stream_processor.process_chunk(content)
            content = tool_stream_processor.process_chunk(content)
            if content:
                full_content += content
                yield ("content", content)
        
        if not raw_content:
            raw_content = "...silence..."
            
        history.append(AIMessage(raw_content))
        self.history.append(AIMessage(raw_content))

        self.save_history()
        
        yield ("break","")

        if use_tools:
            responses = []
            for tool in tool_stream_processor.matches:
                for type, message in self.process_tool(tool, user_input):
                    if type == "tool_response":
                        responses.append(f"Response from {tool}\n\n{message}\n\nThe user has not seen this data yet.\n\nThis is context to answer the previous query '{user_input}'")
                    elif type == "end":
                        if message:
                            yield from self.stream("That tool returned the following result (tell the user): " + message, use_tools=False)
                    else:
                        yield (type, message)
            if responses:
                yield from self.stream("\n\n".join(responses), depth=depth+1)
            
