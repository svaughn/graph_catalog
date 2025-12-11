#!/usr/bin/env python3

import sys
import json
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

def load_json_summary(filename: str) -> dict:
    """Load the catalog summary from a JSON file."""
    if not os.path.exists(filename):
        print(f"❌ JSON file not found: {filename}")
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

def get_pdf_filename(json_filename: str) -> str:
    """Create a descriptive PDF filename from the JSON filename."""
    base_name = os.path.splitext(json_filename)[0]
    return f"{base_name}_dependencies.pdf"

def build_dependency_maps(data: dict) -> tuple[dict, dict, dict]:
    """
    Analyzes catalog data to map out course dependencies.
    Returns three dictionaries:
    1. all_courses: Maps course_id to course_title.
    2. required_by: Maps course_id to a list of programs that require it.
    3. prereq_for: Maps course_id to a list of courses that use it as a prerequisite.
    """
    all_courses = {}
    required_by = {}
    prereq_for = {}

    for school in data.get('schools', []):
        for program in school.get('programs', []):
            program_name = program.get('program_name', 'Unknown Program')

            # Map program requirements
            for req_course in program.get('requirement_courses', []):
                course_id = req_course.get('course_id')
                if course_id:
                    all_courses[course_id] = req_course.get('course_title', 'Unknown Title')
                    required_by.setdefault(course_id, set()).add(program_name)

            # Map prerequisites
            for course in program.get('program_courses', []):
                course_id = course.get('course_id')
                if course_id:
                    all_courses[course_id] = course.get('course_title', 'Unknown Title')
                    for prereq in course.get('prerequisites', []):
                        prereq_id = prereq.get('course_id')
                        if prereq_id:
                            # The key is the prerequisite, the value is the course that depends on it
                            prereq_for.setdefault(prereq_id, set()).add(course_id)
    
    return all_courses, required_by, prereq_for

def create_dependencies_pdf(all_courses: dict, required_by: dict, prereq_for: dict, pdf_filename: str):
    """Generates a PDF listing all courses and their dependencies."""
    doc = SimpleDocTemplate(pdf_filename, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    
    # Custom styles for better readability
    course_header_style = ParagraphStyle('CourseHeader', parent=styles['h2'], spaceBefore=12, spaceAfter=6)
    dependency_header_style = ParagraphStyle('DependencyHeader', parent=styles['h3'], leftIndent=18, spaceAfter=2)
    list_item_style = ParagraphStyle('ListItem', parent=styles['Normal'], leftIndent=36)
    
    story = [Paragraph("Course Dependency Analysis", styles['h1'])]
    
    # Sort courses alphabetically by ID
    sorted_course_ids = sorted(all_courses.keys())
    
    for course_id in sorted_course_ids:
        course_title = all_courses[course_id]
        story.append(Paragraph(f"{course_id}: {course_title}", course_header_style))
        
        # List programs that require this course
        if course_id in required_by:
            story.append(Paragraph("Required By Programs:", dependency_header_style))
            for program_name in sorted(list(required_by[course_id])):
                story.append(Paragraph(f"• {program_name}", list_item_style))
        
        # List courses that use this as a prerequisite
        if course_id in prereq_for:
            story.append(Paragraph("Prerequisite For:", dependency_header_style))
            for dependent_course_id in sorted(list(prereq_for[course_id])):
                dependent_title = all_courses.get(dependent_course_id, "Unknown Title")
                story.append(Paragraph(f"• {dependent_course_id}: {dependent_title}", list_item_style))
        
        # Add a small spacer if no dependencies were found for this course
        if course_id not in required_by and course_id not in prereq_for:
            story.append(Paragraph("<i>No dependencies found in other programs or courses.</i>", list_item_style))

    try:
        doc.build(story)
        print(f"✓ PDF created successfully: {pdf_filename}")
    except Exception as e:
        print(f"❌ Error creating PDF: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python get_dependencies_pdf.py <json_summary_file>")
        print("\nExample:")
        print("  python get_dependencies_pdf.py 2025-2026_undergraduate.json")
        sys.exit(1)
    
    json_filename = sys.argv[1]
    
    # Load and process the data
    catalog_data = load_json_summary(json_filename)
    all_courses, required_by, prereq_for = build_dependency_maps(catalog_data)
    
    # Generate the PDF
    pdf_filename = get_pdf_filename(json_filename)
    print(f"Creating dependency PDF: {pdf_filename}")
    create_dependencies_pdf(all_courses, required_by, prereq_for, pdf_filename)
    