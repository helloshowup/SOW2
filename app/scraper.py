import structlog
from typing import List
from dataclasses import dataclass
from Google Search import search # This uses the Google Search tool

log = structlog.get_logger(__name__)

@dataclass
class ScrapedContent:
    """Represents content scraped from a single source."""
    content: str
    source_url: str
    search_query: str


def search_and_scrape(queries: List[str]) -> List[ScrapedContent]:
    """
    Performs a Google search for each query and scrapes content from the results.
    """
    log.info("Entering search_and_scrape function", queries=queries) # ADDED LOG
    all_scraped_content: List[ScrapedContent] = []
    
    if not queries:
        log.warning("No search queries provided to search_and_scrape function.") # MODIFIED LOG
        return []

    for query in queries:
        try:
            log.info("Performing Google search", query=query) # ORIGINAL LOG
            search_results = search(queries=[query])
            log.info("Google Search results received", query=query, raw_results=search_results) # ADDED LOG: Shows raw search tool output
            
            if not search_results or not search_results[0].results:
                log.info("No search results found for query from Google Search tool.", query=query) # MODIFIED LOG
                continue
            
            for result in search_results[0].results:
                if result.snippet:
                    all_scraped_content.append(
                        ScrapedContent(
                            content=result.snippet,
                            source_url=result.url,
                            search_query=query
                        )
                    )
                else: # ADDED ELSE BLOCK
                    log.info("Search result has no snippet, skipping.", url=result.url, query=query)

        except Exception as e:
            log.error("Error during Google search or scraping.", query=query, error=str(e)) # MODIFIED LOG
    
    log.info("Exiting search_and_scrape function.", total_scraped_items=len(all_scraped_content)) # ADDED LOG
    return all_scraped_content