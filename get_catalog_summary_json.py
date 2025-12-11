#!/usr/bin/env python3

import sys
import pickle
import os
import json
from urllib.parse import urlparse

from catalog_util import (
    get_json_filename,
    get_ser_filename,
    fetch_html,
    get_sidebar_ul_links,
    find_link,
    extract_course_titles,
    discover_candidate_school_urls,
    filter_urls_by_sidebar    
)

# Get the serialized filename based on the catalog URL
CATALOG_PAGE_WITH_SIDEBAR = sys.argv[1]
COURSE_DICT_FILE = get_ser_filename(CATALOG_PAGE_WITH_SIDEBAR)

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
            return {}
    else:
        print(f"❌ Course dictionary not found at {filename}")
        print(f"   Please run create_course_dictionary.py first to build the dictionary.")
        sys.exit(1)

def extract_school_name(school_url: str) -> str:
    """Extract the school name from the school's overview page."""
    from bs4 import BeautifulSoup
    
    html = fetch_html(school_url)
    if not html:
        return "Unknown School"
    
    try:
        soup = BeautifulSoup(html, "html.parser")
        
        # Try to find the page title or h1 heading
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)
        
        # Fallback to page title
        title = soup.find("title")
        if title:
            title_text = title.get_text(strip=True)
            # Remove common suffixes like " | St. John Fisher University"
            if "|" in title_text:
                return title_text.split("|")[0].strip()
            return title_text
        
        return "Unknown School"
    except Exception as e:
        print(f"      ⚠️  Error extracting school name from {school_url}: {e}")
        return "Unknown School"

def parse_prerequisite_courses(prereq_string: str, course_dict: dict) -> list[str]:
    """Parse prerequisite string and extract course IDs."""
    if not prereq_string:
        return []
    
    import re
    pattern = r'\b([A-Z]{3,4}[-\s]?\d{3}[A-Z]?)\b'
    matches = re.findall(pattern, prereq_string.upper())
    
    prereq_courses = []
    for match in matches:
        normalized = match.replace(' ', '').replace('-', '')
        
        for course_id in course_dict.keys():
            normalized_dict_id = course_id.replace(' ', '').replace('-', '').upper()
            if normalized == normalized_dict_id:
                prereq_courses.append(course_id)
                break
    
    return prereq_courses

def extract_course_ids_from_program_requirements(prog_req_url: str, course_dict: dict) -> list[str]:
    """Extract course IDs from Program Requirements page."""
    from bs4 import BeautifulSoup
    import re
    
    html = fetch_html(prog_req_url)
    if not html:
        return []
    
    try:
        soup = BeautifulSoup(html, "html.parser")
        page_text = soup.get_text()
        
        pattern = r'\b([A-Z]{3,4}[-\s]?\d{3}[A-Z]?)\b'
        matches = re.findall(pattern, page_text.upper())
        
        found_courses = []
        seen = set()
        
        for match in matches:
            normalized = match.replace(' ', '').replace('-', '')
            
            for course_id in course_dict.keys():
                normalized_dict_id = course_id.replace(' ', '').replace('-', '').upper()
                if normalized == normalized_dict_id and course_id not in seen:
                    found_courses.append(course_id)
                    seen.add(course_id)
                    break
        
        return found_courses
    except Exception as e:
        print(f"        ⚠️  Error extracting courses from {prog_req_url}: {e}")
        return []

def save_to_json(data: dict, filename: str):
    """Save the catalog summary data to a JSON file."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✓ Summary saved to {filename}")
    except Exception as e:
        print(f"⚠️  Error saving JSON file: {e}")

if __name__ == "__main__":
    # Accept URL from command line or use default
    if len(sys.argv) > 1:
        CATALOG_PAGE_WITH_SIDEBAR = sys.argv[1]
    else:
        CATALOG_PAGE_WITH_SIDEBAR = "https://catalog.sjf.edu/2025-2026/"
    
    print(f"Generating JSON summary for: {CATALOG_PAGE_WITH_SIDEBAR}\n")

    # Load course dictionary (required)
    course_dictionary = load_course_dictionary()
    
    # Discover and filter school URLs
    YOUR_URLS = discover_candidate_school_urls(CATALOG_PAGE_WITH_SIDEBAR)
    
    try:
        filtered = filter_urls_by_sidebar(CATALOG_PAGE_WITH_SIDEBAR, YOUR_URLS)
    except Exception as e:
        print(f"Error: {e}")
        raise

    print(f"Discovered {len(YOUR_URLS)} candidate school URLs; {len(filtered)} appear in sidebar\n")
    
    # Collect course data
    print("Collecting course data...\n")
    all_courses_data = []
    
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
                        all_courses_data.append({
                            "school_url": school_url,
                            "program_name": nav_link['text'],
                            "prog_req_link": prog_req_link,
                            "courses_link": courses_link,
                            **course
                        })
    
    # Build JSON structure
    print("Building JSON structure...\n")
    json_output = {
        "catalog_url": CATALOG_PAGE_WITH_SIDEBAR,
        "total_courses": len(all_courses_data),
        "schools": []
    }
    
    # Organize data by school and program for JSON
    schools_dict = {}
    
    for course_data in all_courses_data:
        school_url = course_data["school_url"]
        program_name = course_data["program_name"]
        
        # Initialize school if not exists
        if school_url not in schools_dict:
            school_name = extract_school_name(school_url)
            schools_dict[school_url] = {
                "school_name": school_name,
                "school_url": school_url,
                "programs": {}
            }
        
        # Initialize program if not exists
        if program_name not in schools_dict[school_url]["programs"]:
            prog_req_link = course_data.get('prog_req_link')
            
            # Get requirement courses
            requirement_courses = []
            if prog_req_link and prog_req_link != 'Not found':
                req_course_ids = extract_course_ids_from_program_requirements(
                    prog_req_link,
                    course_dictionary
                )
                requirement_courses = [
                    {
                        "course_id": cid,
                        "course_title": course_dictionary.get(cid, "Unknown")
                    }
                    for cid in req_course_ids
                ]
            
            schools_dict[school_url]["programs"][program_name] = {
                "program_name": program_name,
                "program_requirements_url": prog_req_link if prog_req_link else "Not available",
                "courses_url": course_data['courses_link'],
                "requirement_courses": requirement_courses,
                "program_courses": []
            }
        
        # Add course to program
        prereq_courses = parse_prerequisite_courses(
            course_data.get("prerequisites", ""),
            course_dictionary
        )
        
        course_entry = {
            "course_id": course_data["course_id"],
            "course_title": course_data["course_title"],
            "prerequisites": [
                {
                    "course_id": pid,
                    "course_title": course_dictionary.get(pid, "Unknown")
                }
                for pid in prereq_courses
            ] if prereq_courses else []
        }
        
        schools_dict[school_url]["programs"][program_name]["program_courses"].append(course_entry)
    
    # Convert schools_dict to list format for JSON
    for school_url, school_data in schools_dict.items():
        school_entry = {
            "school_name": school_data["school_name"],
            "school_url": school_data["school_url"],
            "programs": list(school_data["programs"].values())
        }
        json_output["schools"].append(school_entry)
    
    # Save to JSON file
    json_filename = get_json_filename(sys.argv[1])
    save_to_json(json_output, json_filename)
    
    print(f"\n✓ JSON generation complete!")
    print(f"  Total schools: {len(json_output['schools'])}")
    print(f"  Total courses: {json_output['total_courses']}")