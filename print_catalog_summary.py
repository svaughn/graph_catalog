#!/usr/bin/env python3

import sys
import json
import os

def load_json_summary(filename: str) -> dict:
    """Load the catalog summary from a JSON file."""
    if not os.path.exists(filename):
        print(f"❌ JSON file not found: {filename}")
        print(f"   Please run get_catalog_summary_json.py first to generate the JSON file.")
        sys.exit(1)
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✓ Loaded catalog summary from {filename}")
        return data
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading JSON file: {e}")
        sys.exit(1)

def print_catalog_summary(data: dict):
    """Print the catalog summary in the same format as summarize_catalog.py"""
    
    print(f"\nAnalyzing: {data.get('catalog_url', 'Unknown')}\n")
    print(f"Total courses in catalog: {data.get('total_courses', 0)}\n")
    print("=" * 80)
    
    print("\n🔍 Program Courses and prerequisite relationships...\n")
    print("=" * 80)
    
    schools = data.get('schools', [])
    
    for school in schools:
        school_name = school.get('school_name', 'Unknown School')
        school_url = school.get('school_url', 'Unknown URL')
        
        print(f"\n📚 School: {school_name}")
        print(f"    Overview: {school_url}")
        print("-" * 80)
        
        programs = school.get('programs', [])
        
        for program in programs:
            program_name = program.get('program_name', 'Unknown Program')
            prog_req_url = program.get('program_requirements_url', 'Not available')
            courses_url = program.get('courses_url', 'Not available')
            requirement_courses = program.get('requirement_courses', [])
            program_courses = program.get('program_courses', [])
            
            print(f"\n  📄 Program: {program_name}")
            
            # Display requirement courses
            if requirement_courses:
                print(f"\n      📋 Requirement Courses ({len(requirement_courses)}): {prog_req_url}")
                for req_course in requirement_courses:
                    course_id = req_course.get('course_id', 'Unknown')
                    course_title = req_course.get('course_title', 'Unknown')
                    print(f'        • "{course_id}": "{course_title}"')
            elif prog_req_url != 'Not available':
                print(f"\n      📋 Requirement Courses: None found ({prog_req_url})")
            else:
                print(f"\n      📋 Requirement Courses: Not available")
            
            print(f"\n      Courses URL: {courses_url}")
            print(f"\n      📚 Program Courses:")
            print()
            
            # Display program courses
            for course in program_courses:
                course_id = course.get('course_id', 'Unknown')
                course_title = course.get('course_title', 'Unknown')
                prerequisites = course.get('prerequisites', [])
                
                print(f'        • "{course_id}", "{course_title}"')
                
                # Display prerequisites if any
                if prerequisites:
                    print(f"          Prerequisites:")
                    for prereq in prerequisites:
                        prereq_id = prereq.get('course_id', 'Unknown')
                        prereq_title = prereq.get('course_title', 'Unknown')
                        print(f'            - "{prereq_id}": "{prereq_title}"')
                
                print()

if __name__ == "__main__":
    # Check for JSON filename argument
    if len(sys.argv) < 2:
        print("Usage: python print_catalog_summary.py <json_summary_file>")
        print("\nExample:")
        print("  python print_catalog_summary.py 2025-2026_summary.json")
        sys.exit(1)
    
    json_filename = sys.argv[1]
    
    # Load JSON data
    catalog_data = load_json_summary(json_filename)
    
    # Print the summary
    print_catalog_summary(catalog_data)