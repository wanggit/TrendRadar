"""
Scrapling Content Fetcher - Uses Scrapling framework for robust content extraction.

Scrapling provides:
- DynamicFetcher: Full browser automation via Playwright for JS-rendered pages
- Fetcher: Fast HTTP requests with TLS fingerprint impersonation
- Adaptive parser: Smart element tracking that survives website changes
"""

import logging
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ScraplingResult:
    title: str = ""
    content: str = ""
    success: bool = False
    error: str = ""
    fetcher_type: str = ""  # "dynamic" or "static"


class ScraplingFetcher:
    """
    Unified content fetcher using Scrapling framework.

    Strategy:
    1. Try DynamicFetcher (full browser) for JS-rendered pages
    2. Fallback to Fetcher (HTTP) for simple pages
    3. Skip known search/redirect URLs that can't yield content
    """

    # URLs that are search pages or redirects, not article pages
    SKIP_PATTERNS = [
        "s.weibo.com/weibo?q=",
        "baidu.com/s?wd=",
        "baidu.com/link?url=",
        "google.com/search?q=",
        "so.com/s?q=",
        "sogou.com/web?query=",
        "search.bilibili.com",
    ]

    # Maximum content length to store
    MAX_CONTENT_LENGTH = 10000

    # Timeout for dynamic fetcher (milliseconds)
    DYNAMIC_TIMEOUT = 15000

    # Timeout for static fetcher (seconds)
    STATIC_TIMEOUT = 10

    @classmethod
    def should_skip(cls, url: str) -> bool:
        """Check if URL is a search/redirect page that can't yield article content."""
        if not url:
            return True
        url_lower = url.lower()
        return any(pattern in url_lower for pattern in cls.SKIP_PATTERNS)

    @classmethod
    def fetch(cls, url: str, use_dynamic: bool = True) -> ScraplingResult:
        """
        Fetch content from URL using Scrapling.

        Args:
            url: The article URL
            use_dynamic: Try DynamicFetcher first (browser), fallback to Fetcher

        Returns:
            ScraplingResult with title, content, and success status
        """
        if not url:
            return ScraplingResult(error="Empty URL")

        if cls.should_skip(url):
            return ScraplingResult(error="Search/redirect URL, skipped")

        # Determine fetch strategy based on URL
        url_lower = url.lower()
        
        # Sites with strong anti-scraping (zhihu) - try dynamic with special config
        if 'zhihu.com' in url_lower:
            return cls._fetch_zhihu(url)
        
        # JS-heavy sites (douyin, tieba) - use dynamic with longer timeout
        if any(p in url_lower for p in ['douyin.com', 'tieba.baidu.com']):
            return cls._fetch_js_heavy(url)
        
        # Normal sites - try dynamic first, fallback to static
        if use_dynamic:
            result = cls._fetch_dynamic(url)
            if result.success:
                return result

        return cls._fetch_static(url)

    @classmethod
    def _fetch_zhihu(cls, url: str) -> ScraplingResult:
        """Fetch from Zhihu with special anti-scraping handling."""
        # Zhihu has very strong anti-scraping, skip for now
        return ScraplingResult(error="Zhihu anti-scraping (403)", fetcher_type="dynamic")

    @classmethod
    def _fetch_js_heavy(cls, url: str) -> ScraplingResult:
        """Fetch from JS-heavy sites with shorter timeout."""
        try:
            from scrapling.fetchers import DynamicFetcher
            
            page = DynamicFetcher.fetch(
                url,
                headless=True,
                timeout=10000,  # Shorter timeout (10s)
                disable_resources=True,  # Disable unnecessary resources
                block_ads=True,
                network_idle=False,  # Don't wait for network idle
            )
            
            if page.status != 200:
                return ScraplingResult(error=f"HTTP {page.status}", fetcher_type="dynamic")
            
            content = cls._extract_content(page)
            if content and len(content) > 30:
                title = ""
                title_elem = page.css("h1")
                if title_elem:
                    title = title_elem[0].get_all_text().strip()
                
                return ScraplingResult(
                    title=title,
                    content=content[:cls.MAX_CONTENT_LENGTH],
                    success=True,
                    fetcher_type="dynamic",
                )
            
            return ScraplingResult(error="No content extracted", fetcher_type="dynamic")
            
        except Exception as e:
            logger.debug(f"JS-heavy fetch failed: {e}")
            return ScraplingResult(error=f"JS-heavy fetch failed: {type(e).__name__}", fetcher_type="dynamic")

    @classmethod
    def _fetch_dynamic(cls, url: str) -> ScraplingResult:
        """Fetch using DynamicFetcher (Playwright browser)."""
        try:
            from scrapling.fetchers import DynamicFetcher

            page = DynamicFetcher.fetch(
                url,
                headless=True,
                timeout=cls.DYNAMIC_TIMEOUT,
                disable_resources=True,  # Speed boost
                block_ads=True,  # Block ads for cleaner content
            )

            if page.status != 200:
                return ScraplingResult(
                    error=f"HTTP {page.status}",
                    fetcher_type="dynamic",
                )

            content = cls._extract_content(page)
            if content and len(content) > 30:
                # Try to get title
                title = ""
                title_elem = page.css("h1")
                if title_elem:
                    title = title_elem[0].get_all_text().strip()

                return ScraplingResult(
                    title=title,
                    content=content[:cls.MAX_CONTENT_LENGTH],
                    success=True,
                    fetcher_type="dynamic",
                )

            return ScraplingResult(
                error="No meaningful content extracted",
                fetcher_type="dynamic",
            )

        except ImportError:
            return ScraplingResult(error="Scrapling not installed")
        except Exception as e:
            logger.debug(f"Dynamic fetch failed for {url[:80]}...: {e}")
            return ScraplingResult(
                error=f"Dynamic fetch failed: {type(e).__name__}",
                fetcher_type="dynamic",
            )

    @classmethod
    def _fetch_static(cls, url: str) -> ScraplingResult:
        """Fetch using Fetcher (HTTP with TLS fingerprint)."""
        try:
            from scrapling.fetchers import Fetcher

            page = Fetcher.get(url, timeout=cls.STATIC_TIMEOUT)

            if page.status != 200:
                return ScraplingResult(
                    error=f"HTTP {page.status}",
                    fetcher_type="static",
                )

            content = cls._extract_content(page)
            if content and len(content) > 30:
                title = ""
                title_elem = page.css("h1")
                if title_elem:
                    title = title_elem[0].get_all_text().strip()

                return ScraplingResult(
                    title=title,
                    content=content[:cls.MAX_CONTENT_LENGTH],
                    success=True,
                    fetcher_type="static",
                )

            return ScraplingResult(
                error="No meaningful content extracted",
                fetcher_type="static",
            )

        except ImportError:
            return ScraplingResult(error="Scrapling not installed")
        except Exception as e:
            logger.debug(f"Static fetch failed for {url[:80]}...: {e}")
            return ScraplingResult(
                error=f"Static fetch failed: {type(e).__name__}",
                fetcher_type="static",
            )

    @classmethod
    def _extract_content(cls, page) -> str:
        """
        Extract main content from a Scrapling page object.

        Uses multiple strategies:
        1. Article/main content selectors
        2. Body text with noise removal
        """
        content = ""

        # Strategy 1: Try article-specific selectors
        article_selectors = [
            "article",
            ".article-content",
            ".post-content",
            ".entry-content",
            ".content",
            "#content",
            ".RichContent-inner",  # Zhihu
            ".detail-content",  # Some news sites
            ".newsflash-item",  # 36kr
            ".topic_content",  # V2EX
            ".main-content",
            ".article-body",
            ".story-content",
        ]

        for selector in article_selectors:
            try:
                elem = page.css(selector)
                if elem:
                    text = elem[0].get_all_text().strip()
                    if len(text) > 50:
                        content = text
                        break
            except Exception:
                continue

        # Strategy 2: Try to get the first large text block
        if not content or len(content) < 50:
            try:
                # Get all paragraphs and join them
                paragraphs = page.css("p")
                if paragraphs:
                    texts = [p.get_all_text().strip() for p in paragraphs]
                    # Filter out short paragraphs
                    texts = [t for t in texts if len(t) > 20]
                    if texts:
                        content = "\n".join(texts)
            except Exception:
                pass

        # Strategy 3: Fallback to body text
        if not content or len(content) < 50:
            try:
                text = page.get_all_text().strip()
                # Remove excessive whitespace
                import re
                text = re.sub(r'\s+', ' ', text)
                if len(text) > 50:
                    content = text
            except Exception:
                pass

        return content

    @classmethod
    def fetch_batch(cls, urls: list[str], use_dynamic: bool = True) -> list[ScraplingResult]:
        """
        Fetch content from multiple URLs sequentially.

        Args:
            urls: List of article URLs
            use_dynamic: Use DynamicFetcher for each URL

        Returns:
            List of ScraplingResult in same order as urls
        """
        results = []
        for url in urls:
            result = cls.fetch(url, use_dynamic=use_dynamic)
            results.append(result)
            # Rate limit between requests
            time.sleep(0.5)
        return results

    @classmethod
    def search_and_fetch(cls, query: str, max_results: int = 1) -> list[ScraplingResult]:
        """
        Search for articles using a query (e.g., news title) and fetch content.

        Uses Bing search to find relevant articles, then fetches content from
        the top results.

        Args:
            query: Search query (typically news title)
            max_results: Maximum number of articles to fetch

        Returns:
            List of ScraplingResult for found articles
        """
        import requests
        import urllib.parse
        import base64
        from bs4 import BeautifulSoup

        results = []
        search_url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}&count={max_results}"

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            # Shorter timeout for search
            resp = requests.get(search_url, headers=headers, timeout=5)
            if resp.status_code != 200:
                return results

            soup = BeautifulSoup(resp.text, 'html.parser')
            links = []
            
            # Bing uses h2 > a for result titles
            for a in soup.select('li.b_algo h2 a'):
                href = a.get('href', '')
                if href:
                    # Bing redirect URLs contain the final URL in the 'u' parameter (base64)
                    if 'bing.com/ck/a' in href and 'u=a1' in href:
                        try:
                            # Extract the base64 part after 'u=a1'
                            parts = href.split('u=a1')
                            if len(parts) > 1:
                                b64_part = parts[1].split('&')[0]
                                # Add padding if needed
                                padding = 4 - len(b64_part) % 4
                                if padding != 4:
                                    b64_part += '=' * padding
                                decoded = base64.b64decode(b64_part).decode('utf-8')
                                if decoded and len(decoded) > 10:
                                    href = decoded
                        except Exception:
                            continue
                    
                    if href.startswith('http') and len(href) > 10:
                        links.append(href)

            # Deduplicate and limit
            seen = set()
            unique_links = []
            for link in links:
                if link not in seen:
                    seen.add(link)
                    unique_links.append(link)
                if len(unique_links) >= max_results:
                    break

            # Fetch content from each link (use static fetcher for speed)
            for link in unique_links[:max_results]:
                result = cls.fetch(link, use_dynamic=False)
                if result.success:
                    results.append(result)

        except Exception:
            # Silently fail for search
            pass

        return results
