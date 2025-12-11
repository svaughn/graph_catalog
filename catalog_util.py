#!/usr/bin/env python3

import subprocess
from urllib.parse import urlparse
import requests
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
import re


HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SJF-Catalog-Extractor/2.5)"
}

def run_command(command_parts: list[str]) -> tuple[int, str, str]:
    """
    Run a command and capture its output.
    Returns (return_code, stdout, stderr).
    """
    try:
        print(f"  Running command: {' '.join(command_parts)}")
        result = subprocess.run(
            command_parts,
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        # Return a special code to indicate the command itself was not found
        return -1, "", f"Command not found: '{command_parts[0]}'. Is it installed and in your PATH?"
    except Exception as e:
        return 1, "", str(e)


def get_base_filename(catalog_url: str) -> str:
    """
    Extract the first two path elements from URL to create a base filename.
    Example: https://catalog.sjf.edu/2025-2026/undergraduate/ug-academic-programs/
    Returns: 2025-2026_undergraduate
    """
    parsed = urlparse(catalog_url)
    path_parts = [p for p in parsed.path.split('/') if p]
    
    if len(path_parts) >= 2:
        return f"{path_parts[0]}_{path_parts[1]}"
    elif len(path_parts) == 1:
        return f"{path_parts[0]}"
    else:
        return "catalog_summary"


def get_filename(catalog_url: str) -> str:
    """Get base filename from catalog URL."""
    return get_base_filename(catalog_url)


def get_json_filename(catalog_url: str) -> str:
    """Get JSON filename from catalog URL."""
    return get_filename(catalog_url) + ".json"


def get_ser_filename(catalog_url: str) -> str:
    """Get serialized dictionary filename from catalog URL."""
    return get_filename(catalog_url) + ".ser"


def fetch_html(url: str) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        time.sleep(0.5)
        return r.text
    except requests.RequestException as e:
        print(f"      ⚠️  Error fetching {url}: {e}")
        return None
    

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
    
def discover_candidate_school_urls(page_url: str) -> list[str]:
    """Discover candidate top-level School URLs."""
    html = fetch_html(page_url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")

    year_root = get_year_root(page_url)

    candidates = set()
    for a in soup.find_all("a", href=True):
        abs_url = urljoin(page_url, a["href"])
        if not abs_url.startswith(year_root):
            continue
        path = urlparse(abs_url).path
        candidates.add(normalize_url(abs_url))

    return sorted(candidates)


def filter_urls_by_sidebar(page_url: str, urls: list[str]) -> list[str]:
    sidebar_links = get_sidebar_links(page_url)
    return [u for u in urls if normalize_url(u) in sidebar_links]


def get_year_root(page_url: str) -> str:
    """Extract the catalog year root."""
    p = urlparse(page_url)
    parts = [seg for seg in p.path.split("/") if seg]
    if not parts:
        return f"{p.scheme}://{p.netloc}/"
    year = parts[0]
    return f"{p.scheme}://{p.netloc}/{year}/"

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

def get_sidebar_links(page_url: str, debug: bool = False) -> set[str]:
    html = fetch_html(page_url)
    if not html:
        return set()
    
    soup = BeautifulSoup(html, "html.parser")
    sidebar = soup.find("div", id="sidebar")
    
    if not sidebar:
        if debug:
            print("⚠️  No sidebar found!")
        return set()
    
    if debug:
        print(f"✓ Sidebar found, scanning for links...")
    
    links = set()
    for a in sidebar.find_all("a", href=True):
        link_text = a.get_text(strip=True)
        if debug:
            print(f"  Found link: '{link_text}'")
        
        if 'school' in link_text.lower():
            abs_url = urljoin(page_url, a["href"])
            links.add(normalize_url(abs_url))
            if debug:
                print(f"    ✓ Matched! Added: {abs_url}")
    
    return links

def remove_parenthetical(text: str) -> str:
    """Remove parenthetical phrases from text."""
    while '(' in text:
        text = re.sub(r'\([^()]*\)', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text