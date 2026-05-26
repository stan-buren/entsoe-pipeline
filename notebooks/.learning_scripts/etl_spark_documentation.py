# Copyright 2026 Stanislav Burundukov
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup
import html2text

# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================
TEST_MODE = False  # Set to True for testing (20 URLs), False for Production (All URLs)
# =============================================================================

def load_urls(urls_file: Path, limit: int | None = None) -> list[str]:
    """Loads URLs from the text file with an optional limit.

    Args:
        urls_file (Path): The path to the file containing the URLs.
        limit (int, optional): The maximum number of URLs to load. Defaults to None.

    Returns:
        list[str]: A list of URL strings.
    """
    if not urls_file.exists():
        print(f"Error: URL file not found at {urls_file}")
        return []
    with open(urls_file, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]
    if limit is not None:
        return urls[:limit]
    return urls

def parse_page_to_markdown(url: str, session: requests.Session) -> str:
    """Fetches a documentation page and extracts its main article as Markdown.

    Args:
        url (str): The URL of the documentation page.
        session (requests.Session): The requests Session object.

    Returns:
        str: Clean Markdown content or error message.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = session.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return f"### [Error Loading Page]({url})\n\nFailed to fetch content: {e}\n"

    # Parse raw bytes payload with explicit UTF-8 to resolve encoding mismatches
    soup = BeautifulSoup(response.content, "html.parser", from_encoding="utf-8")

    article = soup.find("article", class_="bd-article", role="main")
    if not article:
        article = soup.find("article", class_="bd-article")
    if not article:
        article = soup.find("main", id="main-content")
    if not article:
        article = soup.find("div", class_="section")

    if not article:
        article = soup.body if soup.body else soup

    # Pre-clean the HTML to strip non-breaking spaces before markdown conversion
    html_str = str(article)
    html_str = html_str.replace('\xa0', ' ').replace('&nbsp;', ' ')

    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True
    h.body_width = 0  # Keep code lines and tabular content from wrapping
    h.ignore_emphasis = False

    markdown_content = h.handle(html_str)

    # Strip residual Windows-1252 to UTF-8 decoding symbols
    markdown_content = markdown_content.replace('Â', '')
    markdown_content = markdown_content.replace('â€™', "'").replace('âs', "'s").replace('â', "'")

    return markdown_content

def main():
    script_dir = Path(__file__).parent
    urls_file = script_dir / "results" / "spark_sql_urls.txt"

    # Dynamic output naming based on TEST_MODE
    filename = "spark_sql_megadoc_test.md" if TEST_MODE else "spark_sql_megadoc.md"
    megadoc_file = script_dir / "results" / filename

    limit = 20 if TEST_MODE else None
    print(f"Starting PySpark SQL Documentation parser (TEST_MODE = {TEST_MODE})...")
    urls = load_urls(urls_file, limit=limit)
    print(f"Loaded {len(urls)} URLs to process in parallel.")

    if not urls:
        print("No URLs to process. Exiting.")
        return

    megadoc_file.parent.mkdir(parents=True, exist_ok=True)

    # Instantiate session with custom connection pool limits
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    parsed_pages = {}

    start_time = time.time()

    print(f"Spawning concurrent fetch threads (max workers: 10)...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_index = {
            executor.submit(parse_page_to_markdown, url, session): (i, url)
            for i, url in enumerate(urls)
        }

        for future in as_completed(future_to_index):
            i, url = future_to_index[future]
            basename = url.split("/")[-1].replace(".html", "")
            try:
                markdown = future.result()
                parsed_pages[i] = markdown

                # Progressive logger every 10 pages parsed (very helpful for production runs)
                if len(parsed_pages) % 10 == 0 or len(parsed_pages) == len(urls):
                    print(f"Progress: [{len(parsed_pages)}/{len(urls)}] pages parsed successfully.")
            except Exception as e:
                parsed_pages[i] = f"### [Error in parser thread]({url})\n\nException occurred: {e}\n"
                print(f"Thread failed for {basename}: {e}")

    elapsed_time = time.time() - start_time
    print(f"Finished scraping in {elapsed_time:.2f} seconds!")

    # Write to compiled megadoc in original order
    print(f"Writing compiled megadoc to: {megadoc_file}...")
    with open(megadoc_file, "w", encoding="utf-8") as f:
        title_prefix = "TEST " if TEST_MODE else ""
        f.write(f"# PySpark SQL Documentation Megadoc ({title_prefix}First {len(urls)} Pages)\n\n")
        f.write("This document is a compiled archive of PySpark SQL documentation pages.\n\n")
        f.write("## Table of Contents\n\n")
        for i, url in enumerate(urls):
            basename = url.split("/")[-1].replace(".html", "")
            f.write(f"{i+1}. [{basename}](#{basename.replace('.', '').lower()})\n")
        f.write("\n---\n\n")

        for i in range(len(urls)):
            url = urls[i]
            basename = url.split("/")[-1].replace(".html", "")
            markdown = parsed_pages.get(i, "")

            f.write(f"# {basename}\n\n")
            f.write(f"**Source URL:** {url}  \n\n")
            f.write(markdown)
            f.write("\n\n---\n\n")

    print(f"Done! Megadoc compiled successfully at: {megadoc_file}")

if __name__ == "__main__":
    main()
