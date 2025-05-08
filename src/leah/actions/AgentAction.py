from typing import List, Dict, Any
from leah.llm.ChatApp import ChatApp
from leah.actions.IActions import IAction
import time

from leah.utils.PostOffice import PostOffice

class AgentAction(IAction):
    def __init__(self, config_manager, persona: str, query: str, chat_app: ChatApp):
        self.config_manager = config_manager
        self.persona = persona
        self.query = query
        self.chat_app = chat_app

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

    def _ask_agent(self, query: str, conversation_history: List[Dict[str, Any]], agent_chatapp: ChatApp):
        
        time.sleep(0.5)
        
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
        query = arguments.get("query", "")
        agent = arguments.get("agent", "expert")
        agent_chatapp = ChatApp(self.config_manager, agent, self.chat_app.conversation_id+"_agent_"+agent)
        if not query:
            yield ("end", "Query is required")
            return
        if "@" in agent:
            agent = agent.split("@")[0]

        return_inbox_id = self.persona+"_agent_"+agent+"_"+self.chat_app.conversation_id + "_" + str(time.time())

        yield ("system", f"{self.persona} asked agent {agent_chatapp.persona}: {query}")

        to_inbox_id = agent + "@agents"
        post_office = PostOffice.get_instance()
        if post_office.has_inbox(to_inbox_id):
            if post_office.has_inbox(return_inbox_id):
                yield ("system", "Agent " + agent + " is already running, waiting for it to finish...")
                yield ("inbox", return_inbox_id)
                return
            yield ("system", "Going into background")
            post_office.create_inbox(return_inbox_id)
            post_office.send_message(
                to_inbox_id=to_inbox_id,
                return_inbox_id=return_inbox_id,
                body=(query, agent_chatapp, "AgentAction.ask_agent with agent named '" + agent + "'")
            )
            yield ("inbox", return_inbox_id)
        else:
            yield from self._ask_agent(query, [], agent_chatapp)

    def additional_notes(self) -> str:
        output = "The following is a description of the agents you can query: \n\n"
        for persona, description in self.config_manager.get_config().get_agent_descriptions().items():
            if persona != self.persona:
                output += f"    - {persona}: {description}\n"
        return output + """
     
    Important information regarding agents: 
    
        - Agents are not aware of any conversations you have had with the user or other agents so you must communicate all the details to them in detail.  
        - Do not assume agents have any knowledge of the user or other agents.  
        - You can call multiple agents and they will all work in parallel, this is encouraged.

"""
    
    def context_template(self, query: str, context: str, source: str) -> str:
        return f"""
Here is the response from {source}:

{context}

Query: {query}
"""

    