from datetime import datetime
from typing import List, Dict, Any
from .IActions import IAction

class LogAction(IAction):
    def __init__(self, config_manager, persona: str, query: str, chat_app: Any):
        self.config_manager = config_manager
        self.persona = persona
        self.query = query
        self.chat_app = chat_app

    def getTools(self) -> List[tuple]:
        return [
            (self.logIndex, "log_index", "Logs a list of index terms related to the query and the response for later referece with search_conversation_logs.", {"terms": "<comma separated list of index terms>"}),
            (self.searchConversationLogs, "search_conversation_logs", "Searches past conversation logs for search terms related to the query and the response. Use this tool to find information from past conversations. Provide multiple terms to search for to expand the search. Terms should be a comma seperate list of general terms (usually one word terms).", {"terms": "<comma separated list of search terms>"}),
            (self.getPastConversations, "get_past_conversations", "Searches past conversation logs over a period of days. Use this tool to find information from past conversations. It takes a single argument for the number of days to worth of conversation to gather. Only use this tool if you cannot answer the query using the searchConversationLogs tool.", {"days": "<number of days to gather>"})
        ]
    
    def context_template(self, message: str, context: str) -> str:
        return f"""
Here is some context for the query:

{context}

Source: logs of past conversations 

Here is the query:

{message}

Answer the query using the context provided above.
"""

    def logIndex(self, arguments: Dict[str, Any]):
        logManager = self.config_manager.get_log_manager()
        terms = arguments.get("terms", "").split(",")
        yield ("system", "Logging terms: " + arguments.get("terms", ""))
        for term in terms:
            logManager.log_index_item(term, "[USER] " + self.query.replace("\n", "\\n"))
            logManager.log_index_item(term, "[ASSISTANT] " + self.chat_app.history[-1].text().replace("\n", "\\n"))
        yield ("end", "")

    def searchIndex(self, terms):
        logManager = self.config_manager.get_log_manager()
        results = []
        total_tokens = 0
        for term in terms:
            # Get results and reverse them
            term_results = list(logManager.search_log_item(term))[::-1]
            for result in term_results:
                # Approximate token count (rough estimate: 4 chars = 1 token)
                result_tokens = len(result) // 4
                if total_tokens + result_tokens > 2000:
                    break
                results.append(result)
                total_tokens += result_tokens
        return results

    def searchConversationLogs(self, arguments: Dict[str, Any]):
        yield ("system", "Searching logs for " + arguments["terms"])
        terms = arguments["terms"].split(",")
        results = self.searchIndex(terms)
        if not results:
            yield ("result", self.context_template(self.query, "No results found in logs, do not search logs for this query."))
        else:
            yield ("result", self.context_template(self.query, "\n".join(results)))

    def getPastConversations(self, arguments: Dict[str, Any]):
        yield ("system", "Getting logs for the past " + str(arguments["days"]) + " days")
        logManager = self.config_manager.get_log_manager()
        days = int(arguments["days"])
        results = logManager.get_logs_for_days(days)
        yield ("result", self.context_template(self.query, results))


    def additional_notes(self) -> str:
        logManager = self.config_manager.get_log_manager()
        indexes = logManager.get_largest_index_logs(50)
        indexes_str = ",".join(indexes)
        out = f"""Always search past conversation logs if you cannot answer the query. The indexes are: {indexes_str}"""
        if indexes:
            out += "These are some of the most common search terms that you can use but you are not required to use them: " + indexes_str
        return out

    

