#!/usr/bin/env python3

import re
import sys
import time
import pickle
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SJF-Catalog-Extractor/2.5)"
}

COURSE_DICT_FILE = "course_dictionary.ser"

def normalize_url(u: str) -> str:
    """Normalize URL for reliable comparison (drop query/fragment, unify trailing slash)."""
    p = urlparse(u.strip())
    scheme = p.scheme.lower()
    netloc = p.netloc.lower()
    path = p.path or "/"
    if not path.endswith("/"):
        if "." not in path.split("/")[-1]:
            path = path + "/"
    return urlunparse((scheme, netloc, path, "", "", ""))

def get_year_root(page_url: str) -> str:
    """Extract the catalog year root."""
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
        time.sleep(0.5)
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
    """Extract links from sidebar ul elements."""
    html = fetch_html(page_url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    
    sidebar = soup.find("div", id="sidebar")
    if not sidebar:
        return []
    
    ul = sidebar.find("ul")
    if not ul:
        return []
    
    links = []
    for li in ul.find_all("li", recursive=False):
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
    """Find a link containing the specified substring."""
    html = fetch_html(page_url)
    if not html:
        return None

    try:
        soup = BeautifulSoup(html, "html.parser")
        
        for a in soup.find_all("a", href=True):
            link_text = a.get_text(strip=True)
            if link_text_substring.lower() in link_text.lower():
                return urljoin(page_url, a["href"])
        
        return None
    except Exception as e:
        print(f"      ⚠️  Error finding '{link_text_substring}' on {page_url}: {e}")
        return None

def remove_parenthetical(text: str) -> str:
    """Remove parenthetical phrases from text."""
    while '(' in text:
        text = re.sub(r'\([^()]*\)', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def save_course_dictionary(course_dict: dict, filename: str = COURSE_DICT_FILE):
    """Save the course dictionary to a file using pickle serialization."""
    try:
        with open(filename, 'wb') as f:
            pickle.dump(course_dict, f)
        print(f"✓ Course dictionary saved to {filename}")
    except Exception as e:
        print(f"⚠️  Error saving course dictionary: {e}")

def load_course_dictionary(filename: str = COURSE_DICT_FILE) -> dict:
    """Load the course dictionary from a file if it exists."""
    if os.path.exists(filename):
        try:
            with open(filename, 'rb') as f:
                course_dict = pickle.load(f)
            print(f"✓ Loaded course dictionary from {filename} ({len(course_dict)} courses)")
            return course_dict
        except Exception as e:
            print(f"⚠️  Error loading course dictionary: {e}")
            print("   Starting with empty dictionary...")
            return {}
    else:
        print(f"ℹ️  No existing course dictionary found at {filename}")
        return {}

def extract_course_titles(courses_url: str) -> list[dict]:
    """Extract course titles and prerequisites from courses page."""
    html = fetch_html(courses_url)
    if not html:
        return []
    
    try:
        soup = BeautifulSoup(html, "html.parser")
        course_data = []
        
        for h3 in soup.find_all("h3", class_="maryann_course_title"):
            title = h3.get_text(strip=True)
            if not title:
                continue
            
            cleaned_title = remove_parenthetical(title)
            if not cleaned_title:
                continue
            
            parts = cleaned_title.split(" ", 1)
            course_id = ""
            course_title = ""
            
            if len(parts) == 2:
                course_id = parts[0].strip()
                course_title = parts[1].strip()
            elif len(parts) == 1:
                course_id = parts[0].strip()
                course_title = ""
            
            prerequisites = None
            li_parent = h3.find_parent("li")
            if li_parent:
                prereq_span = li_parent.find("span", string=re.compile(r'Pre-requisites?', re.IGNORECASE))
                
                if prereq_span:
                    next_sibling = prereq_span.next_sibling
                    prereq_text = ""
                    
                    if next_sibling and isinstance(next_sibling, str):
                        prereq_text = next_sibling.strip()
                    elif prereq_span.parent:
                        parent_text = prereq_span.parent.get_text()
                        if "Pre-requisites" in parent_text or "Pre-requisite" in parent_text:
                            parts = re.split(r'Pre-requisites?:?\s*', parent_text, flags=re.IGNORECASE)
                            if len(parts) > 1:
                                prereq_text = parts[1].strip()
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
    """Discover candidate top-level School URLs."""
    html = fetch_html(page_url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")

    year_root = get_year_root(page_url)
    pattern = r"/(?:undergraduate"
    if include_grad:
        pattern += r"|graduate"
    pattern += r")/([^/]+)/?$"

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

    # Try to load existing course dictionary
    course_dictionary = load_course_dictionary()
    
    # If dictionary is empty, build it from scratch
    if not course_dictionary:
        print("Building course dictionary from catalog...\n")
        
        # Discover and filter school URLs
        YOUR_URLS = discover_candidate_school_urls(CATALOG_PAGE_WITH_SIDEBAR, include_grad=False)
        
        try:
            filtered = filter_urls_by_sidebar(CATALOG_PAGE_WITH_SIDEBAR, YOUR_URLS)
        except Exception as e:
            print(f"Error: {e}")
            raise

        print(f"Discovered {len(YOUR_URLS)} candidate school URLs; {len(filtered)} appear in sidebar\n")
        print("=" * 80)
        print("\n🔍 PHASE 1: Building course dictionary...\n")
        
        for school_url in filtered:
            sidebar_links = get_sidebar_ul_links(school_url)
            
            if not sidebar_links:
                continue
            
            for nav_link in sidebar_links:
                prog_req_link = find_link(nav_link['url'], "Program Requirements")
                
                if prog_req_link:
                    courses_link = find_link(nav_link['url'], "Courses")
                    if courses_link:
                        course_data = extract_course_titles(courses_link)
                        
                        for course in course_data:
                            course_dictionary[course["course_id"]] = course["course_title"]
        
        print(f"✓ Built course dictionary with {len(course_dictionary)} unique courses\n")
        
        # Save the course dictionary
        save_course_dictionary(course_dictionary)
    else:
        print("Course dictionary already exists and was loaded successfully.")
