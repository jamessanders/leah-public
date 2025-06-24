import asyncio
from hashlib import sha256
import time
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from leah.actions import Actions
from leah.config.LocalConfigManager import LocalConfigManager
import json
from leah.llm.StreamProcessor import StreamProcessor
from langchain_core.messages import BaseMessage
from typing import Any, List
import tiktoken
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from leah.llm.TokenRateLimiter import TokenRateLimiter
from leah.utils.TokenCounter import TokenLimiter


def count_tokens(text: str) -> int:
    """Calculate num tokens for OpenAI with tiktoken package."""
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    num_tokens = len(encoding.encode(text))
    return num_tokens

class LlmConnector:
    def __init__(self, 
                 config_manager: LocalConfigManager, 
                 persona: str = 'default'):
        self.persona = persona
        self.config_manager = config_manager
        self.config = config_manager.get_config()
        self.max_tokens = 30000
        self.max_output_tokens = 15000
        self.processors = []
        self.tools = []
        self.history = []
        
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
                google_api_key=api_key,
                max_output_tokens=self.max_output_tokens
            )
        elif connector_type == 'openai':
            self.llm = ChatOpenAI(
                model=model,
                temperature=temperature,
                openai_api_key=api_key,
                max_output_tokens=self.max_output_tokens
            )
        elif connector_type == 'lmstudio':
            self.llm = ChatOpenAI(
                model=model,
                temperature=temperature,
                openai_api_key=api_key,
                base_url=base_url,
                max_output_tokens=self.max_output_tokens
            )
        else:  # local connector for Ollama/LMStudio
            self.llm = ChatOllama(
                model=model,
                temperature=temperature,
                base_url=base_url,
                max_output_tokens=self.max_output_tokens
            )
    
    def add_processor(self, processor: StreamProcessor):
        self.processors.append(processor)

    def query(self, query):
        
        # Calculate estimated tokens for rate limiting
        estimated_tokens = 0
        estimated_tokens += count_tokens(query)
        
        # Check rate limit
        connector_type = self.config.get_connector_type(self.persona)
        rate_limiter = TokenRateLimiter()
        while not rate_limiter.check_rate_limit(connector_type, estimated_tokens):
            print(" !! Token rate limit exceeded, waiting 1 second before checking again")
            time.sleep(1)  # Wait 1 second before checking again
            
        chain = self.llm | StrOutputParser()
        history = [HumanMessage(query)]
        response = "".join([content for content in chain.invoke(history)])
        
        total_tokens = estimated_tokens + count_tokens(response)
        rate_limiter.add_tokens(connector_type, total_tokens)
        
        return response
    
    def bind_tools(self, tools: List[Any]):
        self.tools = tools
        self.llm = self.llm.bind_tools(tools)

    def stream(self, input:List[BaseMessage]=[]):
        """
        Process input and return chatbot response
        """

        self.history = input

        # Calculate estimated tokens for rate limiting
        estimated_tokens = 0
        for item in input:
            estimated_tokens += count_tokens(item.text())

        # Check rate limit for this connector type with estimated tokens
        connector_type = self.config.get_connector_type(self.persona)
        rate_limiter = TokenRateLimiter()
        while not rate_limiter.check_rate_limit(connector_type, estimated_tokens):
            print(" !! Token rate limit exceeded, waiting 1 second before checking again")
            time.sleep(1)  # Wait 1 second before checking again
            
        # Create the chain using runnables
        chain = self.llm

        raw_content = ""
        full_content = ""
        
        total_tokens = 0

        for item in input:
            total_tokens += count_tokens(item.text())

        # Remove oldest messages if total tokens exceed max limit
        while total_tokens > self.max_tokens and len(input) > 0:
            # Remove oldest message
            print("pruning message: " + str(input[0]))
            removed_message = input.pop(0)
            # Recalculate total tokens
            total_tokens -= count_tokens(removed_message.text())
            
        # Track response tokens
        response_tokens = 0
        
        c = 0
        while c < 25:
            token_reader = TokenLimiter(999999999999)
            for item in input:
                token_reader.count(item.text())
            print(" +++ Input token size: " + str(token_reader.total_counted))
            
            try:
                response = chain.invoke(input)
                response.sent_at = time.time()
            except Exception as e:
                c += 1
                print(e)
                continue
            content = response.content
            ## if content is a list, join it into a string
            if isinstance(content, list):
                content = "\n".join(content)

            raw_content += str(content)
            response_tokens += count_tokens(content)
            for processor in self.processors:
                content = yield from processor.process_chunk(content)
                full_content += content
            
            yield ("content", content)
        
            input.append(response)

            if response.tool_calls:
                for tool_call in response.tool_calls:
                    print("tool_call: " + str(tool_call))
                    name = tool_call["name"]
                    formatted_args = [key + ": " + str(value) for key, value in tool_call["args"].items()]
                    formatted_args = ", ".join(formatted_args)
                    yield ("system", self.persona + " is using tool: " + name + " with args: " + formatted_args)
                    matching_tools = [tool for tool in self.tools if tool.name == name]
                    selected_tool = matching_tools[0] if matching_tools else None
                    if selected_tool is None:
                        print("Tool not found: " + name)
                        break
                    tool_result = asyncio.run(selected_tool.ainvoke(tool_call))
                    print("tool_result: " + str(tool_result))
                    tool_result.sent_at = time.time()
                    input.append(tool_result)
            else:
                break

        self.history = input       
        

        # Add the total tokens used to the rate limiter
        total_tokens_used = total_tokens + response_tokens
        rate_limiter.add_tokens(connector_type, total_tokens_used)
        