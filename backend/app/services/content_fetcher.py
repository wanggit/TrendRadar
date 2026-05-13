"""
Content Fetcher - Extract full article content from URLs.

Uses trafilatura for robust content extraction with fallback strategies.
"""

import logging
import re
import requests
from dataclasses import dataclass

import trafilatura

# Suppress trafilatura's verbose warnings
logging.getLogger("trafilatura").setLevel(logging.ERROR)
logging.getLogger("courlan").setLevel(logging.ERROR)
logging.getLogger("htmldate").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


@dataclass
class ContentResult:
    title: str = ""
    content: str = ""
    success: bool = False
    error: str = ""


def fetch_content(url: str, timeout: int = 15) -> ContentResult:
    """
    Fetch and extract the main content from a URL.

    Strategy:
    1. trafilatura (best for news articles)
    2. Fallback: extract from <meta> tags if trafilatura fails

    Args:
        url: The article URL
        timeout: Request timeout in seconds

    Returns:
        ContentResult with title, content, and success status
    """
    if not url:
        return ContentResult(error="Empty URL")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding  # Force correct encoding

        html = resp.text
        if not html or len(html) < 100:
            return ContentResult(error="Page content too short")

        # Primary: trafilatura extraction
        content = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=False,
            include_links=False,
            output_format="txt",
        )

        if content and len(content.strip()) > 30:
            # Also try to get title from trafilatura
            metadata = trafilatura.extract_metadata(html)
            title = metadata.title if metadata and metadata.title else ""

            return ContentResult(
                title=title,
                content=content.strip(),
                success=True,
            )

        # Fallback: try to get content from meta description
        meta_desc = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html, re.I)
        if not meta_desc:
            meta_desc = re.search(r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']description["\']', html, re.I)

        if meta_desc:
            desc = meta_desc.group(1).strip()
            if len(desc) > 20:
                return ContentResult(
                    content=desc,
                    success=True,
                )

        logger.debug(f"No content extracted from {url[:80]}... (html_len={len(html)})")
        return ContentResult(error="No meaningful content extracted")

    except requests.RequestException as e:
        logger.debug(f"Failed to fetch {url[:80]}...: {e}")
        return ContentResult(error=f"Request failed: {type(e).__name__}")
    except Exception as e:
        logger.debug(f"Content extraction failed for {url[:80]}...: {e}")
        return ContentResult(error=f"Extraction failed: {type(e).__name__}")


def fetch_contents_batch(urls: list[str], timeout: int = 15, max_concurrent: int = 3) -> list[ContentResult]:
    """
    Fetch content from multiple URLs sequentially with rate limiting.

    Args:
        urls: List of article URLs
        timeout: Request timeout per URL
        max_concurrent: Not used (sequential to avoid rate limits)

    Returns:
        List of ContentResult in same order as urls
    """
    import time
    results = []
    for url in urls:
        result = fetch_content(url, timeout)
        results.append(result)
        # Rate limit: small delay between requests
        time.sleep(0.3)
    return results
