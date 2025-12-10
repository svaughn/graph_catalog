#!/usr/bin/env python3

import sys
import pickle
import os

# Import common functions from create_course_dictionary
from create_course_dictionary import (
    COURSE_DICT_FILE,
    normalize_url,
    fetch_html,
    get_sidebar_links,
    get_sidebar_ul_links,
    find_link,
    remove_parenthetical,
    extract_course_titles,
    discover_candidate_school_urls,
    filter_urls_by_sidebar
)

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

if __name__ == "__main__":
    # Accept URL from command line or use default
    if len(sys.argv) > 1:
        CATALOG_PAGE_WITH_SIDEBAR = sys.argv[1]
    else:
        CATALOG_PAGE_WITH_SIDEBAR = "https://catalog.sjf.edu/2025-2026/"
    
    print(f"Analyzing: {CATALOG_PAGE_WITH_SIDEBAR}\n")

    # Load course dictionary (required)
    course_dictionary = load_course_dictionary()
    
    # Discover and filter school URLs
    YOUR_URLS = discover_candidate_school_urls(CATALOG_PAGE_WITH_SIDEBAR, include_grad=False)
    
    try:
        filtered = filter_urls_by_sidebar(CATALOG_PAGE_WITH_SIDEBAR, YOUR_URLS)
    except Exception as e:
        print(f"Error: {e}")
        raise

    print(f"Discovered {len(YOUR_URLS)} candidate school URLs; {len(filtered)} appear in sidebar\n")
    print("=" * 80)
    
    # Collect course data for display
    print("\nCollecting course data for analysis...\n")
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
    
    print("=" * 80)
    
    # PHASE 2: Display Program Courses with prerequisite relationships
    print("\n🔍 PHASE 2: Program Courses and prerequisite relationships...\n")
    print("=" * 80)

    current_school = None
    current_program = None
    
    for course_data in all_courses_data:
        # Print school header if changed
        if current_school != course_data["school_url"]:
            current_school = course_data["school_url"]
            print(f"\n📚 School: {current_school}")
            print("-" * 80)
        
        # Print program header if changed
        if current_program != course_data["program_name"]:
            current_program = course_data["program_name"]
            print(f"\n  📄 Program: {current_program}")
            print(f"      Program Requirements URL: {course_data.get('prog_req_link', 'Not found')}")

            # Extract and display Requirement Courses from Program Requirements page
            prog_req_link = course_data.get('prog_req_link')
            if prog_req_link and prog_req_link != 'Not found':
                required_courses = extract_course_ids_from_program_requirements(
                    prog_req_link,
                    course_dictionary
                )
        
                if required_courses:
                    print(f"\n      📋 Requirement Courses ({len(required_courses)}):")
                    for course_id in required_courses:
                        course_title = course_dictionary.get(course_id, "Unknown")
                        print(f'        • "{course_id}": "{course_title}"')

            print(f"\n      Courses URL: {course_data['courses_link']}")
            print(f"\n      📚 Program Courses:")
            print()
        
        # Display course information
        print(f'        • "{course_data["course_id"]}", "{course_data["course_title"]}"')
        
        # Parse and display prerequisite courses (only if found in dictionary)
        if course_data["prerequisites"]:
            prereq_courses = parse_prerequisite_courses(
                course_data["prerequisites"], 
                course_dictionary
            )
            
            # Only display prerequisites if we found valid courses in the dictionary
            if prereq_courses:
                print(f"          Prerequisites:") 
                for prereq_id in prereq_courses:
                    prereq_title = course_dictionary.get(prereq_id, "Unknown")
                    print(f'            - "{prereq_id}": "{prereq_title}"') 
        
        print()
