from datetime import datetime
from typing import List, Dict, Any, Generator, Tuple, Union
from langchain_community.utilities.tavily_search import TavilySearchAPIWrapper
from leah.config.LocalConfigManager import LocalConfigManager
from leah.utils.CacheManager import CacheManager
import hashlib
from langchain_core.tools import tool



def context_template(message: str, context: str, source: str) -> str:
    now = datetime.now()
    today = now.strftime("%B %d, %Y")
    template = f"""
I have searched the web and found the following information:

{context}

from the Source: {source} which was last updated {today}

----
"""
    return template.strip()

@tool
def web_search(query: str) -> Generator[Tuple[str, str], None, None]:
    """
    Searches the web for the given query using Tavily API
    """
    config_manager = LocalConfigManager("default")
    tavily_api_key = config_manager.get_config().get_keys()["tavily"]
    search = TavilySearchAPIWrapper(tavily_api_key=tavily_api_key)
    # Initialize cache manager with 4 hours (14400 seconds) default expiration
    cache_manager = CacheManager(default_expiration=14400)

    try:
        print(f"Searching Tavily for: {query}")
        
        # Create a cache key from the query
        cache_key = f"tavily_search_{hashlib.md5(query.encode()).hexdigest()}"
        
        # Try to get results from cache first
        cached_results = cache_manager.get(cache_key)
        if cached_results is not None:
            print("Retrieved results from cache")
            formatted_results = cached_results
        else:
            # Perform the search if not in cache
            results = search.results(
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
            
            # Cache the formatted results
            cache_manager.set(cache_key, formatted_results)
        
        return context_template(query, formatted_results, "Tavily Search Results")
        
    except Exception as e:
        return context_template(query, f"Error performing Tavily search: {str(e)}", "Error") 