"""
Web search tool for agents
"""
import os
import httpx
from typing import Dict, Any, List, Optional
from .base import Tool, tool_registry
import logging

logger = logging.getLogger("ai_survival.tools.web_search")


class WebSearchTool(Tool):
    """Web search using Brave Search API, SerpAPI, or DuckDuckGo"""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            name="web_search",
            description="Search the web for information",
            cost=0.001,
        )
        self.brave_api_key = api_key or os.getenv("BRAVE_SEARCH_API_KEY")
        self.serpapi_key = os.getenv("SERPAPI_KEY")
        self.use_brave = bool(self.brave_api_key)
        self.use_serpapi = bool(self.serpapi_key)

    async def execute(self, query: str, count: int = 5, **kwargs) -> Dict[str, Any]:
        """Execute web search with fallback chain"""
        # Try Brave Search first
        if self.use_brave:
            result = await self._brave_search(query, count)
            if result.get("status") == "success" and result.get("results"):
                return result
            logger.warning("Brave search returned no results, trying SerpAPI")

        # Try SerpAPI
        if self.use_serpapi:
            result = await self._serpapi_search(query, count)
            if result.get("status") == "success" and result.get("results"):
                return result
            logger.warning("SerpAPI returned no results, trying DuckDuckGo")

        # Fallback to DuckDuckGo
        return await self._duckduckgo_search(query, count)

    async def _brave_search(self, query: str, count: int) -> Dict[str, Any]:
        """Search using Brave Search API"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    headers={"X-Subscription-Token": self.brave_api_key},
                    params={"q": query, "count": count},
                )
                response.raise_for_status()
                data = response.json()

                results = []
                for result in data.get("web", {}).get("results", [])[:count]:
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "snippet": result.get("description", ""),
                    })

                return {
                    "status": "success",
                    "query": query,
                    "results": results,
                    "source": "brave",
                }
        except Exception as e:
            logger.error(f"Brave search failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def _serpapi_search(self, query: str, count: int) -> Dict[str, Any]:
        """Search using SerpAPI (Google search)"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://serpapi.com/search",
                    params={
                        "q": query,
                        "api_key": self.serpapi_key,
                        "num": count,
                        "engine": "google",
                    },
                )
                response.raise_for_status()
                data = response.json()

                results = []
                for result in data.get("organic_results", [])[:count]:
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("link", ""),
                        "snippet": result.get("snippet", ""),
                    })

                return {
                    "status": "success",
                    "query": query,
                    "results": results,
                    "source": "serpapi",
                }
        except Exception as e:
            logger.error(f"SerpAPI search failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def _duckduckgo_search(self, query: str, count: int) -> Dict[str, Any]:
        """Fallback search using DuckDuckGo HTML (lite version)"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            # Use lite.duckduckgo.com which is simpler and more reliable
            async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True) as client:
                response = await client.get(
                    "https://lite.duckduckgo.com/lite/",
                    params={"q": query},
                )
                response.raise_for_status()

                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, "html.parser")

                results = []
                # Lite DDG uses table rows with links
                for link in soup.select("table tr td a")[:count]:
                    title = link.get_text(strip=True)
                    href = link.get("href", "")
                    if title and href:
                        results.append({
                            "title": title[:100],
                            "url": href,
                            "snippet": "",
                        })

                # If no results from lite, try html version
                if not results:
                    response2 = await client.get(
                        "https://html.duckduckgo.com/html/",
                        params={"q": query},
                    )
                    response2.raise_for_status()
                    soup2 = BeautifulSoup(response2.text, "html.parser")

                    # Try multiple selector patterns for different DDG HTML versions
                    selectors_to_try = [
                        (".result .result__a", ".result__snippet"),
                        (".result a.result__snippet", None),
                        (".results .result a", ".result__snippet"),
                        (".web-result .result__snippet", None),
                        ("a.result__url", None),
                        (".result__title a", None),
                    ]

                    for title_selector, snippet_selector in selectors_to_try:
                        elements = soup2.select(title_selector)
                        for el in elements[:count]:
                            title = el.get_text(strip=True)
                            href = el.get("href", "")

                            snippet = ""
                            if snippet_selector:
                                snippet_el = el.find_parent().select_one(snippet_selector)
                                if snippet_el:
                                    snippet = snippet_el.get_text(strip=True)

                            if title or href:
                                results.append({
                                    "title": title[:100],
                                    "url": href,
                                    "snippet": snippet[:200],
                                })

                        if results:
                            break

                return {
                    "status": "success",
                    "query": query,
                    "results": results,
                    "source": "duckduckgo",
                }
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            # Return empty results but success status so pipeline continues
            return {
                "status": "success",
                "query": query,
                "results": [],
                "source": "duckduckgo",
                "note": f"Search failed: {str(e)[:100]}",
            }


class WebFetchTool(Tool):
    """Fetch and extract content from a URL"""

    def __init__(self):
        super().__init__(
            name="web_fetch",
            description="Fetch and extract content from a web page",
            cost=0.0005,
        )

    async def execute(self, url: str, **kwargs) -> Dict[str, Any]:
        """Fetch web page content"""
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()

                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, "html.parser")

                # Remove script and style elements
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()

                text = soup.get_text(separator="\n", strip=True)
                title = soup.title.string if soup.title else ""

                return {
                    "status": "success",
                    "url": url,
                    "title": title,
                    "content": text[:10000],  # Limit content size
                }
        except Exception as e:
            logger.error(f"Web fetch failed: {e}")
            return {"status": "failed", "error": str(e)}


# Register tools
tool_registry.register(WebSearchTool())
tool_registry.register(WebFetchTool())