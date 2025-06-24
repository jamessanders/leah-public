from typing import List, Dict, Any
from leah.actions.IActions import IAction
import time

from leah.utils.PostOffice import PostOffice

class AgentAction(IAction):
    def __init__(self, config_manager, persona: str, query: str, chat_app: Any):
        self.config_manager = config_manager
        self.persona = persona
        self.query = query
        self.chat_app = chat_app
        self.threading = False

    def getTools(self) -> List[tuple]:
        return [
            (self.ask_agent,
             "ask_agent",
             "Ask an agent a question and get a response, these agents are experts in their own fields and can help you with your questions.  The agent is unaware of the conversation history, so you will need to provide any details that may have been disucssed previously.",
             {"query": "<the question to ask the agent>", "agent": "<the agent to query>"}),
            (self.ask_agent,
             "delegate_task_to_agent",
             "Delegate a task to an agent, these agents are experts in their own fields and can help you with your task.  The agent is unaware of the conversation history, so you will need to provide any details that may have been disucssed previously.",
             {"query": "<a query to initiate the task>", "agent": "<the agent to query>"})
        ]

    def check_inbox(self, arguments):
        wait_time = int(arguments.get("wait_time",1))
        yield ("system", f"{self.persona} is checking for new messages...waiting {wait_time} seconds")
        if wait_time > 5:
            wait_time = 5
        if not self.chat_app.is_watching():
            yield ("result", "You are not expecting any messages and none have been found.")
        else:
            sent_something = False
            for type,body,source in self.chat_app.watch(1):
                if type == "content":
                    sent_something = True
                    yield ("system", self.persona + ": Found a new message from " + source + " before the query...")
                    yield ("result", "System said: Appears to be a response from " + source + ":\n\n" + body + "\n\nNote that the user has not read the response message yet.")
                else:
                    yield (type, body)
            if not sent_something:
                yield ("result", "No new messages have arrived yet, check back later.")
                

    def _ask_agent(self, query: str, conversation_history: List[Dict[str, Any]], agent_chatapp: Any):
        time.sleep(0.1)
        conversation_history.append({"role": "user", "content": query})
        response = ""
        for type,message in agent_chatapp.stream(query):
            if type == "content":
                response += message
            else:
                yield (type, message)
        
        response = response.strip() or "...silence..."
        conversation_history.append({"role": "assistant", "content": response})
        yield ("system", "Agent said: " + response)
        yield ("result", "Here is the conversation history please use it to answer the users query:\n\n" + "\n\n".join([x["content"] for x in conversation_history]))
        
    def ask_agent(self, arguments: Dict[str, Any]):
                
        from leah.llm.ChatApp import ChatApp

        query = arguments.get("query", "")
        agent = arguments.get("agent", "expert")
        
        if agent.startswith("@"):
            agent = agent[1:]
        
        if not query:
            yield ("end", "Query is required")
            return
        
        agent_chatapp = ChatApp(self.config_manager, agent, conversation_id=self.persona + "_to_" + agent)

        yield ("system", f"{self.persona} asked agent {agent_chatapp.persona}: {query}")
        yield from self._ask_agent(query, [], agent_chatapp)

    def additional_notes(self) -> str:
        output = "The following is a description of the agents you can query: \n\n"
        for persona, description in self.config_manager.get_config().get_agent_descriptions().items():
            if persona != self.persona:
                output += f"    - {persona} (handle: @{persona}): {description}\n"
        return output + """
     
    Important information regarding agents: 
    
        - Agent actions are considerably more reliable than sending direct messages to agents.
        - Agents are not aware of any conversations you have had with the user or other agents so you must communicate all the details to them in detail.  
        - Do not assume agents have any knowledge of the user or other agents.  
        - You can call multiple agents and they will all work in parallel, this is encouraged.
        - Agents can run a variety of tools you may not be aware of, so be sure to ask one if you need to use a tool that is not listed in the tools you have available.

"""
    
    def context_template(self, query: str, context: str, source: str) -> str:
        return f"""
Here is the response from {source}:

{context}

Query: {query}
"""

    