#!/usr/bin/env python3

import sys
import json
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_LEFT

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

def get_pdf_filename(json_filename: str) -> str:
    """Convert JSON filename to PDF filename."""
    base_name = os.path.splitext(json_filename)[0]
    return f"{base_name}.pdf"

def create_catalog_pdf(data: dict, pdf_filename: str):
    """Create a PDF from the catalog summary data."""
    
    # Create the PDF document
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor='black',
        spaceAfter=12,
        alignment=TA_LEFT
    )
    
    heading1_style = ParagraphStyle(
        'CustomHeading1',
        parent=styles['Heading2'],
        fontSize=14,
        textColor='black',
        spaceAfter=10,
        spaceBefore=10,
        alignment=TA_LEFT
    )
    
    heading2_style = ParagraphStyle(
        'CustomHeading2',
        parent=styles['Heading3'],
        fontSize=12,
        textColor='black',
        spaceAfter=8,
        spaceBefore=8,
        leftIndent=20,
        alignment=TA_LEFT
    )
    
    heading3_style = ParagraphStyle(
        'CustomHeading3',
        parent=styles['Heading4'],
        fontSize=11,
        textColor='black',
        spaceAfter=6,
        leftIndent=40,
        alignment=TA_LEFT
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        textColor='black',
        leftIndent=60,
        spaceAfter=4,
        alignment=TA_LEFT
    )
    
    indent_style = ParagraphStyle(
        'CustomIndent',
        parent=styles['Normal'],
        fontSize=9,
        textColor='black',
        leftIndent=80,
        spaceAfter=2,
        alignment=TA_LEFT
    )
    
    # Title
    catalog_url = data.get('catalog_url', 'Unknown')
    total_courses = data.get('total_courses', 0)
    
    elements.append(Paragraph(f"Catalog Analysis", title_style))
    elements.append(Paragraph(f"URL: {catalog_url}", body_style))
    elements.append(Paragraph(f"Total courses: {total_courses}", body_style))
    elements.append(Spacer(1, 0.2*inch))
    
    elements.append(Paragraph("Program Courses and Prerequisite Relationships", title_style))
    elements.append(Spacer(1, 0.1*inch))
    
    schools = data.get('schools', [])
    
    for school_idx, school in enumerate(schools):
        school_name = school.get('school_name', 'Unknown School')
        school_url = school.get('school_url', 'Unknown URL')
        
        # School header
        elements.append(Paragraph(f"School: {school_name}", heading1_style))
        elements.append(Paragraph(f"Overview: {school_url}", body_style))
        elements.append(Spacer(1, 0.1*inch))
        
        programs = school.get('programs', [])
        
        for program_idx, program in enumerate(programs):
            program_name = program.get('program_name', 'Unknown Program')
            prog_req_url = program.get('program_requirements_url', 'Not available')
            courses_url = program.get('courses_url', 'Not available')
            requirement_courses = program.get('requirement_courses', [])
            program_courses = program.get('program_courses', [])
            
            # Program header
            elements.append(Paragraph(f"Program: {program_name}", heading2_style))
            
            # Requirement courses
            if requirement_courses:
                elements.append(Paragraph(
                    f"Requirement Courses ({len(requirement_courses)}): {prog_req_url}",
                    heading3_style
                ))
                for req_course in requirement_courses:
                    course_id = req_course.get('course_id', 'Unknown')
                    course_title = req_course.get('course_title', 'Unknown')
                    elements.append(Paragraph(
                        f'• "{course_id}": "{course_title}"',
                        body_style
                    ))
            elif prog_req_url != 'Not available':
                elements.append(Paragraph(
                    f"Requirement Courses: None found ({prog_req_url})",
                    heading3_style
                ))
            else:
                elements.append(Paragraph(
                    "Requirement Courses: Not available",
                    heading3_style
                ))
            
            elements.append(Spacer(1, 0.05*inch))
            elements.append(Paragraph(f"Courses URL: {courses_url}", heading3_style))
            elements.append(Paragraph("Program Courses:", heading3_style))
            elements.append(Spacer(1, 0.05*inch))
            
            # Program courses
            for course in program_courses:
                course_id = course.get('course_id', 'Unknown')
                course_title = course.get('course_title', 'Unknown')
                prerequisites = course.get('prerequisites', [])
                
                elements.append(Paragraph(
                    f'• "{course_id}", "{course_title}"',
                    body_style
                ))
                
                # Prerequisites
                if prerequisites:
                    elements.append(Paragraph("Prerequisites:", indent_style))
                    for prereq in prerequisites:
                        prereq_id = prereq.get('course_id', 'Unknown')
                        prereq_title = prereq.get('course_title', 'Unknown')
                        elements.append(Paragraph(
                            f'- "{prereq_id}": "{prereq_title}"',
                            indent_style
                        ))
            
            elements.append(Spacer(1, 0.1*inch))
        
        # Add page break between schools (except for the last one)
        if school_idx < len(schools) - 1:
            elements.append(PageBreak())
    
    # Build the PDF
    try:
        doc.build(elements)
        print(f"✓ PDF created successfully: {pdf_filename}")
    except Exception as e:
        print(f"❌ Error creating PDF: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Check for JSON filename argument
    if len(sys.argv) < 2:
        print("Usage: python create_catalog_summary_pdf.py <json_summary_file>")
        print("\nExample:")
        print("  python create_catalog_summary_pdf.py 2025-2026_undergraduate.json")
        sys.exit(1)
    
    json_filename = sys.argv[1]
    
    # Load JSON data
    catalog_data = load_json_summary(json_filename)
    
    # Generate PDF filename
    pdf_filename = get_pdf_filename(json_filename)
    
    print(f"Creating PDF: {pdf_filename}")
    
    # Create the PDF
    create_catalog_pdf(catalog_data, pdf_filename)