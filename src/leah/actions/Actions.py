from typing import List, Dict, Any
from leah.actions import AgentAction, LinkAction, LogAction, NotesAction, TimeAction, ImageGen, FileReadAction, FileWriteAction, ProcessAction, TavilyAction, EmailAction, MessageAction, WaitAction, ChannelAction, TaskAction
import json

class Actions:
    """
    A class to handle actions based on user queries and conversation history.
    
    This class processes user queries and manages actions based on the conversation
    context, persona settings, and local configuration.
    """
    
    def __init__(self, config_manager, persona: str, query: str, chat_app: Any):
        """
        Initialize the Actions class with the required parameters.
        
        Args:
            config_manager: An instance of LocalConfigManager for managing user configuration
            persona (str): The persona to use for processing the query
            query (str): The user's query to process
            chat_app (ChatApp): The chat app to use for processing the query
        """
        self.config_manager = config_manager
        self.persona = persona
        self.query = query
        self.chat_app = chat_app
        
        # Initialize managers from config_manager
        self.notes_manager = config_manager.get_notes_manager()
        self.log_manager = config_manager.get_log_manager()
        
        available_actions = [
            LinkAction.LinkAction(config_manager, persona, query, self.chat_app),
            ImageGen.ImageGen(config_manager, persona, query, self.chat_app),
            FileReadAction.FileReadAction(config_manager, persona, query, self.chat_app),
            FileWriteAction.FileWriteAction(config_manager, persona, query, self.chat_app),
            ProcessAction.ProcessAction(config_manager, persona, query, self.chat_app),
            TavilyAction.TavilyAction(config_manager, persona, query, self.chat_app),
            WaitAction.WaitAction(config_manager, persona, query, self.chat_app)
        ]
        persona_tools = config_manager.get_config().get_tools(persona)
        self.actions = [action for action in available_actions if action.__class__.__name__ in persona_tools]
        
        # Some default actions that are always available
        self.actions.append(ChannelAction.ChannelAction(config_manager, persona, query, self.chat_app))
        self.actions.append(MessageAction.MessageAction(config_manager, persona, query, self.chat_app))
        self.actions.append(WaitAction.WaitAction(config_manager, persona, query, self.chat_app))
        self.actions.append(TaskAction.TaskAction(config_manager, persona, query, self.chat_app))
        self.actions.append(NotesAction.NotesAction(config_manager, persona, query, self.chat_app))
        # self.actions.append(AgentAction.AgentAction(config_manager, persona, query, self.chat_app))

    def run_tool(self, tool_name: str, arguments: List[str]) -> str:
        tool_sp = tool_name.split(".")
        tool_name = tool_sp[0]
        tool_method = tool_sp[1]
        for action in self.actions:
            if action.__class__.__name__ == tool_name:
                tools = action.getTools()
                for tool in tools:
                    if tool[1] == tool_method:
                        yield from tool[0](arguments)
                        return
        yield ("end", "Tool not found") 

    def get_actions_prompt(self) -> str:
          
        prompt = """
## Please follow these instructions:

    - Request a tool in the format of json: `{"tool": "ActionName.tool_name", "arguments": "arguments_json"}`
    - Wrap the tool request in tool_code type markdown code block.  An example is:
                ```tool_code
                {"tool": "ActionName.tool_name", "arguments": "arguments_json"}
                ```
    - both tool and arguments are required parameters
    - The tool request should be in plain text without any formatting.
    - arguments_json should be in the format of {"argument_name": "argument_value"}
    - Tool names should be in the format of ActionName.ToolName
    - You can use multiple tools in a single response.
    - Do not ask the user to provide the tool name, just respond with the tool.
    - Do not use tags like <|python_start|>
    - Just use tools without telling the user that you will perform a task.
    - Tool usage can be mixed with conversation text.
    - Do not call the same tool with the same arguments more than once in a conversation.
    - Never use attempt to use a tool other than the ones provided to you below.
    - Use as many tools as you need to answer the user's query.
    - Don't just say you will use a tool, do it.

## Tools: 
"""
        for action in self.actions:
            actionName = action.__class__.__name__
            tools = action.getTools()
            for tool in tools:
                actionDescription = tool[2]
                actionArgs = json.dumps(tool[3])
                prompt += f"""
### Tool Name: {actionName}.{tool[1]}
  
  - Description: {actionDescription}
  
  - Arguments: {actionArgs}

"""
            if action.additional_notes():
                prompt += f"""
  ### Additional Notes for these tools: {action.additional_notes()}
"""
        return prompt