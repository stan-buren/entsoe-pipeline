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
import re
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

def extract_latest_iceberg_urls(source_file: Path) -> list[str]:
    """Parses raw markdown dump of Iceberg URLs and returns unique docs/latest URLs.
    
    It extracts URLs matching Apache Iceberg documentation paths, strips anchor fragments
    to avoid duplicate scraping of the same page, and returns a unique, deduplicated list.
    """
    if not source_file.exists():
        print(f"Error: Source file {source_file} not found!")
        return []
        
    content = source_file.read_text(encoding="utf-8")
    
    # Match any valid http/https URLs pointing to iceberg.apache.org
    raw_urls = re.findall(r'(https://[a-zA-Z0-9_\-\.\/]+[a-zA-Z0-9_\-\/])', content)
    
    filtered_urls = []
    seen = set()
    
    for url in raw_urls:
        # Keep only the latest 1.11.0 documentation or spark-quickstart from iceberg.apache.org
        if ("docs/latest" in url or "spark-quickstart" in url) and "iceberg.apache.org" in url:
            # Strip anchor fragments (anything after #)
            clean_url = url.split("#")[0].rstrip("/")
            
            if clean_url not in seen:
                seen.add(clean_url)
                filtered_urls.append(clean_url)
                
    return filtered_urls

def parse_page_to_markdown(url: str, session: requests.Session) -> str:
    """Fetches an Iceberg documentation page and extracts its main article as Markdown.
    
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
    
    # Iceberg docs main content containers
    article = soup.find("div", id="content")
    if not article:
        article = soup.find("main")
    if not article:
        article = soup.find("article")
    if not article:
        article = soup.find("div", class_="content")
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
    artifacts_dir = script_dir / "artifacts"
    results_dir = script_dir / "results"
    
    source_urls_file = artifacts_dir / "iceberg_urls.txt"
    cleaned_urls_file = results_dir / "iceberg_latest_urls.txt"
    
    # Ensure results directory exists
    results_dir.mkdir(parents=True, exist_ok=True)
    
    print("Step 1: Extracting and cleaning Iceberg URLs...")
    urls = extract_latest_iceberg_urls(source_urls_file)
    print(f"Total unique latest Iceberg URLs found: {len(urls)}")
    
    if not urls:
        print("No URLs extracted. Please verify notebooks/.learning_scripts/artifacts/iceberg_urls.txt content. Exiting.")
        return
        
    # Write the cleaned list of URLs to results/iceberg_latest_urls.txt
    print(f"Writing cleaned URLs list to: {cleaned_urls_file}...")
    cleaned_urls_file.write_text('\n'.join(urls) + '\n', encoding='utf-8')
    
    # If in TEST_MODE, restrict processing to the first 20 URLs
    limit = 20 if TEST_MODE else None
    urls_to_process = urls[:limit] if limit else urls
    
    # Dynamic output naming based on TEST_MODE
    filename = "iceberg_latest_megadoc_test.md" if TEST_MODE else "iceberg_latest_megadoc.md"
    megadoc_file = results_dir / filename
    
    print(f"\nStep 2: Scrape & Parse pages (TEST_MODE = {TEST_MODE}, processing {len(urls_to_process)} URLs)...")
    
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
            for i, url in enumerate(urls_to_process)
        }
        
        for future in as_completed(future_to_index):
            i, url = future_to_index[future]
            basename = url.split("/")[-1] if url.split("/")[-1] else "index"
            try:
                markdown = future.result()
                parsed_pages[i] = markdown
                
                # Progressive logger every 10 pages parsed
                if len(parsed_pages) % 5 == 0 or len(parsed_pages) == len(urls_to_process):
                    print(f"Progress: [{len(parsed_pages)}/{len(urls_to_process)}] pages parsed successfully.")
            except Exception as e:
                parsed_pages[i] = f"### [Error in parser thread]({url})\n\nException occurred: {e}\n"
                print(f"Thread failed for {basename}: {e}")
                
    elapsed_time = time.time() - start_time
    print(f"Finished scraping in {elapsed_time:.2f} seconds!")
    
    # Write to compiled megadoc in original order
    print(f"Writing compiled megadoc to: {megadoc_file}...")
    with open(megadoc_file, "w", encoding="utf-8") as f:
        title_prefix = "TEST " if TEST_MODE else ""
        f.write(f"# Apache Iceberg Latest (1.11.0) Documentation Megadoc ({title_prefix}First {len(urls_to_process)} Pages)\n\n")
        f.write("This document is a compiled archive of the latest Apache Iceberg stable documentation.\n\n")
        f.write("## Table of Contents\n\n")
        for i, url in enumerate(urls_to_process):
            basename = url.split("/")[-1] if url.split("/")[-1] else "index"
            f.write(f"{i+1}. [{basename}](#{basename.replace('.', '').replace('#', '').lower()})\n")
        f.write("\n---\n\n")
        
        for i in range(len(urls_to_process)):
            url = urls_to_process[i]
            basename = url.split("/")[-1] if url.split("/")[-1] else "index"
            markdown = parsed_pages.get(i, "")
            
            f.write(f"# {basename}\n\n")
            f.write(f"**Source URL:** {url}  \n\n")
            f.write(markdown)
            f.write("\n\n---\n\n")
            
    print(f"Done! Megadoc compiled successfully at: {megadoc_file}")

if __name__ == "__main__":
    main()
