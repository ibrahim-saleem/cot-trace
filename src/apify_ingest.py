"""
apify_ingest.py
Scrape sources with Apify Website Content Crawler and cache to disk.
Run this BEFORE the demo: python -m src.apify_ingest
"""
import json
import os
import time
from pathlib import Path
from apify_client import ApifyClient
from src.schemas import Document

SOURCES = [
    {"name": "Anthropic", "url": "https://www.anthropic.com/research", "max_pages": 8},
    {"name": "Anthropic", "url": "https://www.anthropic.com/research/reasoning-models-dont-say-think", "max_pages": 1},
    {"name": "Anthropic", "url": "https://www.anthropic.com/research/tracing-thoughts-language-model", "max_pages": 1},
    {"name": "OpenAI",    "url": "https://openai.com/news/research/",  "max_pages": 8},
    {"name": "DeepMind",  "url": "https://deepmind.google/blog/",      "max_pages": 8},
]

RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

CACHE_FILE = RAW_DIR / "documents.json"


def run_crawler(client: ApifyClient, source: dict) -> list[dict]:
    """Run one Apify Website Content Crawler actor call."""
    run = client.actor("apify/website-content-crawler").call(
        run_input={
            "startUrls": [{"url": source["url"]}],
            "maxCrawlPages": source["max_pages"],
            "crawlerType": "cheerio",           # fast, no JS needed for blogs
            "outputFormats": ["markdown"],
            "removeCookieWarnings": True,
        }
    )
    items = list(
        client.dataset(run["defaultDatasetId"]).iterate_items()
    )
    return items


def items_to_documents(items: list[dict], source_name: str) -> list[Document]:
    docs = []
    for i, item in enumerate(items):
        content = item.get("markdown") or item.get("text") or ""
        if len(content.strip()) < 100:          # skip near-empty pages
            continue
        docs.append(Document(
            doc_id=f"{source_name.lower()}_{i:03d}",
            source=source_name,
            title=item.get("title") or item.get("url", ""),
            url=item.get("url", ""),
            content=content[:6000],             # cap per doc to keep tokens sane
            published_at=item.get("publishedAt") or item.get("date") or "",
        ))
    return docs


def load_or_scrape(token: str, force: bool = False) -> list[Document]:
    """
    Return cached documents if they exist, otherwise scrape fresh.
    Pass force=True to re-scrape even if cache exists.
    """
    if CACHE_FILE.exists() and not force:
        raw = json.loads(CACHE_FILE.read_text())
        return [Document(**d) for d in raw]

    client = ApifyClient(token)
    all_docs: list[Document] = []

    for source in SOURCES:
        print(f"Scraping {source['name']}...")
        try:
            items = run_crawler(client, source)
            docs = items_to_documents(items, source["name"])
            all_docs.extend(docs)
            print(f"  → {len(docs)} documents")
        except Exception as e:
            print(f"  ✗ Failed: {e}")
        time.sleep(1)

    # persist to disk
    CACHE_FILE.write_text(
        json.dumps([d.__dict__ for d in all_docs], indent=2)
    )
    print(f"\nCached {len(all_docs)} documents to {CACHE_FILE}")
    return all_docs


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    token = os.environ["APIFY_TOKEN"]
    docs = load_or_scrape(token, force=True)
    print(f"Total documents: {len(docs)}")
