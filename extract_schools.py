#!/usr/bin/env python3

import re
import sys
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SJF-Catalog-Extractor/1.5)"
}

def normalize_url(u: str) -> str:
    """Normalize URL for reliable comparison (drop query/fragment, unify trailing slash)."""
    p = urlparse(u.strip())
    scheme = p.scheme.lower()
    netloc = p.netloc.lower()
    path = p.path or "/"
    # Ensure single trailing slash for directory-like paths
    if not path.endswith("/"):
        if "." not in path.split("/")[-1]:  # likely not a file
            path = path + "/"
    return urlunparse((scheme, netloc, path, "", "", ""))

def get_year_root(page_url: str) -> str:
    """
    Extract the catalog year root, e.g. https://catalog.sjf.edu/2025-2026/
    from a URL like https://catalog.sjf.edu/2025-2026/undergraduate/ug-academic-programs/
    """
    p = urlparse(page_url)
    parts = [seg for seg in p.path.split("/") if seg]
    if not parts:
        return f"{p.scheme}://{p.netloc}/"
    year = parts[0]
    return f"{p.scheme}://{p.netloc}/{year}/"

def fetch_html(url: str) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        time.sleep(0.5)  # Be polite to the server
        return r.text
    except requests.RequestException as e:
        print(f"      ⚠️  Error fetching {url}: {e}")
        return None

def get_sidebar_links(page_url: str) -> set[str]:
    """Fetch page_url, parse sidebar navigation, and return absolute normalized hrefs found there."""
    html = fetch_html(page_url)
    if not html:
        return set()
    soup = BeautifulSoup(html, "html.parser")
    
    # Try multiple possible sidebar selectors
    sidebar = (
        soup.find("div", id="sidebar") or
        soup.find("nav", id="sidebar") or
        soup.find("aside", id="sidebar") or
        soup.find("div", class_="sidebar") or
        soup.find("nav", class_="sidebar") or
        soup.find("div", {"role": "navigation"})
    )
    
    if not sidebar:
        return set()
    
    links = set()
    for a in sidebar.find_all("a", href=True):
        abs_url = urljoin(page_url, a["href"])
        links.add(normalize_url(abs_url))
    
    return links

def get_sidebar_ul_links(page_url: str) -> list[dict]:
    """
    Fetch the page, find div#sidebar, then find the ul within it,
    and extract all links from li elements within that ul.
    Returns a list of dicts with 'text' and 'url' keys.
    """
    html = fetch_html(page_url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    
    # Find div with id="sidebar"
    sidebar = soup.find("div", id="sidebar")
    
    if not sidebar:
        print(f"  ⚠️  No div#sidebar found on {page_url}")
        return []
    
    # Find ul within the sidebar
    ul = sidebar.find("ul")
    
    if not ul:
        print(f"  ⚠️  No <ul> found within div#sidebar on {page_url}")
        return []
    
    # Extract links from li elements
    links = []
    for li in ul.find_all("li", recursive=False):  # Direct children only
        a = li.find("a", href=True)
        if a:
            link_text = a.get_text(strip=True)
            abs_url = urljoin(page_url, a["href"])
            links.append({
                "text": link_text,
                "url": normalize_url(abs_url)
            })
    
    return links

def find_link(page_url: str, link_text_substring: str) -> str | None:
    """
    Fetch the page and search for a link with text containing the specified substring.
    Returns the absolute URL if found, None otherwise.
    """
    html = fetch_html(page_url)
    if not html:
        return None

    try:
        soup = BeautifulSoup(html, "html.parser")
        
        # Search for links containing the specified text (case-insensitive)
        for a in soup.find_all("a", href=True):
            link_text = a.get_text(strip=True)
            if link_text_substring.lower() in link_text.lower():
                return urljoin(page_url, a["href"])
        
        return None
    except Exception as e:
        print(f"      ⚠️  Error finding '{link_text_substring}' on {page_url}: {e}")
        return None

def extract_course_titles(courses_url: str) -> list[str]:
    """
    Fetch the courses page and extract all h3 elements with class="maryann_course_title".
    Returns a list of course title strings.
    """
    html = fetch_html(courses_url)
    if not html:
        return []
    
    try:
        soup = BeautifulSoup(html, "html.parser")
        
        # Find all h3 elements with class="maryann_course_title"
        course_titles = []
        for h3 in soup.find_all("h3", class_="maryann_course_title"):
            title = h3.get_text(strip=True)
            if title:
                course_titles.append(title)
        
        return course_titles
    except Exception as e:
        print(f"        ⚠️  Error extracting course titles from {courses_url}: {e}")
        return []

def discover_candidate_school_urls(page_url: str, include_grad: bool = False) -> list[str]:
    """
    Discover candidate top-level School URLs from the entire page (not just sidebar).
    We look for links like:
      /{year}/undergraduate/<slug>/        (and optionally /graduate/<slug>/)
    and ignore deeper paths (program pages).
    """
    html = fetch_html(page_url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")

    year_root = get_year_root(page_url)
    pattern = r"/(?:undergraduate"
    if include_grad:
        pattern += r"|graduate"
    pattern += r")/([^/]+)/?$"  # top-level slug, optional trailing slash

    candidates = set()
    for a in soup.find_all("a", href=True):
        abs_url = urljoin(page_url, a["href"])
        if not abs_url.startswith(year_root):
            continue
        path = urlparse(abs_url).path
        if re.search(pattern, path):
            candidates.add(normalize_url(abs_url))

    return sorted(candidates)

def filter_urls_by_sidebar(page_url: str, urls: list[str]) -> list[str]:
    sidebar_links = get_sidebar_links(page_url)
    return [u for u in urls if normalize_url(u) in sidebar_links]

if __name__ == "__main__":
    # Accept URL from command line or use default
    if len(sys.argv) > 1:
        CATALOG_PAGE_WITH_SIDEBAR = sys.argv[1]
    else:
        CATALOG_PAGE_WITH_SIDEBAR = "https://catalog.sjf.edu/2025-2026/"
    
    print(f"Analyzing: {CATALOG_PAGE_WITH_SIDEBAR}\n")

    # 1) Build YOUR_URLS dynamically from the same page
    YOUR_URLS = discover_candidate_school_urls(CATALOG_PAGE_WITH_SIDEBAR, include_grad=False)

    # 2) Filter to only those present in sidebar
    try:
        filtered = filter_urls_by_sidebar(CATALOG_PAGE_WITH_SIDEBAR, YOUR_URLS)
    except Exception as e:
        print(f"Error: {e}")
        raise

    print(f"Discovered {len(YOUR_URLS)} candidate school URLs; {len(filtered)} appear in sidebar\n")
    print("=" * 80)
    
    # 3) For each filtered URL, fetch the page and extract sidebar ul links
    for school_url in filtered:
        print(f"\n📚 School: {school_url}")
        print("-" * 80)
        
        sidebar_links = get_sidebar_ul_links(school_url)
        
        if not sidebar_links:
            print("  No links found in sidebar <ul>")
            continue
        
        print(f"  Found {len(sidebar_links)} navigation links in sidebar\n")
        
        # 4) For each sidebar link, fetch the page and find "Program Requirements" and "Courses" links
        for nav_link in sidebar_links:
            print(f"  📄 {nav_link['text']}: {nav_link['url']}")
            
            # Fetch this page and look for "Program Requirements" link
            prog_req_link = find_link(nav_link['url'], "Program Requirements")
            
            if prog_req_link:
                print(f"      ✓ Program Requirements: {prog_req_link}")

                # Find "Courses" link on the same page
                courses_link = find_link(nav_link['url'], "Courses")
                if courses_link:
                    print(f"      ✓ Courses: {courses_link}")
                    
                    # 5) Visit the Courses page and extract course titles
                    course_titles = extract_course_titles(courses_link)
                    
                    if course_titles:
                        print(f"        📚 Found {len(course_titles)} courses:")
                        for title in course_titles:
                            print(f"          • {title}")
                    else:
                        print(f"        ⚠️  No course titles found on courses page")
                else:
                    print(f"      ✗ No 'Courses' link found")

            else:
                print(f"      ✗ No 'Program Requirements' link found")
            
            print()
