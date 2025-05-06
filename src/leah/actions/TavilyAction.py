from datetime import datetime
from typing import List, Dict, Any, Generator, Tuple, Union
from .IActions import IAction
from langchain_community.utilities.tavily_search import TavilySearchAPIWrapper
from leah.llm.ChatApp import ChatApp

class TavilyAction(IAction):
    def __init__(self, config_manager, persona: str, query: str, chat_app: ChatApp):
        self.config_manager = config_manager
        self.persona = persona
        self.query = query
        self.chat_app = chat_app
        self.tavily_api_key = self.config_manager.get_config().get_keys()["tavily"]
        self.search = TavilySearchAPIWrapper(tavily_api_key=self.tavily_api_key)

    def process_query(self) -> Dict[str, Any]:
        return {
            "response": f"TavilyAction processed query: {self.query} with persona: {self.persona}",
            "success": True
        }

    def additional_notes(self) -> str:
        return " - You can perform web searches using Tavily's AI-powered search engine to get relevant and up-to-date information.  Prefer this tool over searching google or other search engines."

    def getTools(self) -> List[tuple]:
        return [
            (self.web_search,
             "web_search",
             "Performs a web search using Tavily API to get relevant and up-to-date information",
             {"query": "<the search query to look up>"})
        ]

    def context_template(self, message: str, context: str, source: str) -> str:
        now = datetime.now()
        today = now.strftime("%B %d, %Y")
        template = f"""
Here is some context for the query:
{context}

Source: {source} (Last updated {today})
"""
        return template.strip()

    def web_search(self, arguments: Dict[str, Any]) -> Generator[Tuple[str, str], None, None]:
        try:
            query = arguments['query']
            yield ("system", f"Searching Tavily for: {query}")
            
            # Perform the search
            results = self.search.results(
                query=query,
                max_results=5,  # Limiting to top 5 results for conciseness
                search_depth="advanced"
            )
            
            # Format the results
            formatted_results = "Search Results:\n\n"
            
            # Format individual search results
            for idx, result in enumerate(results, 1):
                title = result.get('title', 'No title')
                url = result.get('url', 'No URL')
                content = result.get('content', 'No content')
                
                formatted_results += f"{idx}. {title}\n"
                formatted_results += f"   URL: {url}\n"
                formatted_results += f"   Summary: {content}\n\n"
            
            yield ("result", self.context_template(self.query, formatted_results, "Tavily Search Results"))
            
        except Exception as e:
            yield ("result", self.context_template(self.query, f"Error performing Tavily search: {str(e)}", "Error")) 