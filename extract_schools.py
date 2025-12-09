#!/usr/bin/env python3

import re
import sys
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SJF-Catalog-Extractor/1.8)"
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

def remove_parenthetical(text: str) -> str:
    """
    Remove parenthetical phrases from text.
    Handles nested parentheses and cleans up extra whitespace.
    """
    # Remove all parenthetical content (including nested parentheses)
    while '(' in text:
        text = re.sub(r'\([^()]*\)', '', text)
    
    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def extract_course_titles(courses_url: str) -> list[dict]:
    """
    Fetch the courses page and extract all h3 elements with class="maryann_course_title".
    Parses each title into course_id and course_title.
    Also extracts prerequisites if available.
    Removes parenthetical phrases before parsing.
    Returns a list of dictionaries, each with 'course_id', 'course_title', and 'prerequisites' keys.
    """
    html = fetch_html(courses_url)
    if not html:
        return []
    
    try:
        soup = BeautifulSoup(html, "html.parser")
        
        # Find all li elements that contain course information
        course_data = []
        
        # Find all h3 elements with class="maryann_course_title"
        for h3 in soup.find_all("h3", class_="maryann_course_title"):
            title = h3.get_text(strip=True)
            if not title:
                continue
            
            # Remove parenthetical phrases first
            cleaned_title = remove_parenthetical(title)
            
            if not cleaned_title:
                continue
            
            # Split into course_id (first token) and course_title (rest)
            parts = cleaned_title.split(" ", 1)
            course_id = ""
            course_title = ""
            
            if len(parts) == 2:
                course_id = parts[0].strip()
                course_title = parts[1].strip()
            elif len(parts) == 1:
                course_id = parts[0].strip()
                course_title = ""
            
            # Find prerequisites - look for span containing "Pre-requisites" in the same li
            prerequisites = None
            
            # Navigate up to the parent li element
            li_parent = h3.find_parent("li")
            if li_parent:
                # Look for span containing "Pre-requisites" text
                prereq_span = li_parent.find("span", string=re.compile(r'Pre-requisites?', re.IGNORECASE))
                
                if prereq_span:
                    # Get the next sibling text after the span
                    # This could be direct text or in another element
                    next_sibling = prereq_span.next_sibling
                    
                    # Try to extract text from various possible structures
                    prereq_text = ""
                    
                    # Check if next sibling is text
                    if next_sibling and isinstance(next_sibling, str):
                        prereq_text = next_sibling.strip()
                    # Check if it's in a following element
                    elif prereq_span.parent:
                        # Get all text after the span within the parent
                        parent_text = prereq_span.parent.get_text()
                        # Split on "Pre-requisites" and take what comes after
                        if "Pre-requisites" in parent_text or "Pre-requisite" in parent_text:
                            parts = re.split(r'Pre-requisites?:?\s*', parent_text, flags=re.IGNORECASE)
                            if len(parts) > 1:
                                prereq_text = parts[1].strip()
                                # Clean up - take only until next major section or newline
                                prereq_text = prereq_text.split('\n')[0].strip()
                    
                    if prereq_text:
                        prerequisites = prereq_text
            
            course_data.append({
                "course_id": course_id,
                "course_title": course_title,
                "prerequisites": prerequisites
            })
        
        return course_data
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
                    
                    # 5) Visit the Courses page and extract course data
                    course_data = extract_course_titles(courses_link)
                    
                    if course_data:
                        print(f"        📚 Found {len(course_data)} courses:")
                        for course in course_data:
                            output = f'          • "{course["course_id"]}", "{course["course_title"]}"'
                            if course["prerequisites"]:
                                output += f', "{course["prerequisites"]}"'
                            print(output)
                    else:
                        print(f"        ⚠️  No course titles found on courses page")
                else:
                    print(f"      ✗ No 'Courses' link found")

            else:
                print(f"      ✗ No 'Program Requirements' link found")
            
            print()
