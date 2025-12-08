import logging
from typing import Optional, List

from firecrawl import FirecrawlApp
from open_webui.retrieval.web.main import SearchResult, get_filtered_results
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_firecrawl(
    firecrawl_url: str,
    firecrawl_api_key: str,
    query: str,
    count: int,
    filter_list: Optional[List[str]] = None,
) -> List[SearchResult]:
    try:
        # Initialize official Firecrawl SDK client
        firecrawl = FirecrawlApp(api_key=firecrawl_api_key, api_url=firecrawl_url)

        # Run search
        response = firecrawl.search(
            query=query,
            limit=count,
            ignore_invalid_urls=True,
            timeout=count * 3,          # safe timeout scaling
        )

        results = response.web or []   # Ensure list if None

        # Optional filtering
        if filter_list:
            results = get_filtered_results(results, filter_list)

        # Normalize to SearchResult objects
        processed = [
            SearchResult(
                link=result.url,
                title=result.title,
                snippet=result.description,
            )
            for result in results[:count]
        ]

        log.info(f"Firecrawl search results: {processed}")
        return processed

    except Exception as e:
        log.error(f"Error in Firecrawl search: {e}")
        return []
