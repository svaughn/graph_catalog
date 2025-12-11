#!/usr/bin/env python3

import re
import sys
import pickle
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
from catalog_util import (
    get_ser_filename,
    get_sidebar_ul_links,
    find_link,
    extract_course_titles,
    discover_candidate_school_urls,
    filter_urls_by_sidebar,
)

def save_course_dictionary(course_dict: dict, filename: str):
    """Save the course dictionary to a file using pickle serialization."""
    try:
        with open(filename, 'wb') as f:
            pickle.dump(course_dict, f)
        print(f"✓ Course dictionary saved to {filename}")
    except Exception as e:
        print(f"⚠️  Error saving course dictionary: {e}")


def load_course_dictionary(filename: str) -> dict:
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
    

if __name__ == "__main__":
    # Accept URL from command line or use default
    if len(sys.argv) > 1:
        CATALOG_PAGE_WITH_SIDEBAR = sys.argv[1]
    else:
        CATALOG_PAGE_WITH_SIDEBAR = "https://catalog.sjf.edu/2025-2026/"
    
    print(f"Analyzing: {CATALOG_PAGE_WITH_SIDEBAR}\n")

    # Get the serialized filename based on the catalog URL
    COURSE_DICT_FILE = get_ser_filename(CATALOG_PAGE_WITH_SIDEBAR)

    # Try to load existing course dictionary
    course_dictionary = load_course_dictionary(COURSE_DICT_FILE)
    
    # If dictionary is empty, build it from scratch
    if not course_dictionary:
        print("Building course dictionary from catalog...\n")
        
        # Discover and filter school URLs
        YOUR_URLS = discover_candidate_school_urls(CATALOG_PAGE_WITH_SIDEBAR)
        
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
        save_course_dictionary(course_dictionary, COURSE_DICT_FILE)
    else:
        print("Course dictionary already exists and was loaded successfully.")

        