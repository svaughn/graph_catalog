#!/usr/bin/env python3

import sys
import json
import os
import re

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

def get_dot_filename(json_filename: str) -> str:
    """Convert JSON filename to DOT filename."""
    base_name = os.path.splitext(json_filename)[0]
    return f"{base_name}.dot"

def sanitize_id(text: str) -> str:
    """
    Sanitize text to create a valid DOT node ID.
    Replaces spaces and special characters with underscores.
    """
    # Remove quotes and special characters, replace spaces with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', text)
    # Remove consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Remove leading/trailing underscores
    return sanitized.strip('_')

def escape_label(text: str) -> str:
    """Escape special characters for DOT labels."""
    # Escape quotes and backslashes
    text = text.replace('\\', '\\\\').replace('"', '\\"')
    return text

def create_catalog_graph(data: dict, dot_filename: str):
    """Create a DOT graph from the catalog summary data."""
    
    lines = []
    
    # Start the digraph
    lines.append('digraph CatalogSummary {')
    lines.append('    // Graph attributes')
    lines.append('    rankdir=LR; // Left-to-Right layout')
    lines.append('    node [shape=box, style=filled];')
    lines.append('    edge [fontsize=10];')
    lines.append('')
    
    # Define node styles
    lines.append('    // Node styles')
    lines.append('    node [fillcolor=lightblue] // Default for Schools')
    lines.append('')
    
    schools = data.get('schools', [])
    
    # Track all nodes and edges to avoid duplicates
    nodes = set()
    edges = set()
    
    for school in schools:
        school_name = school.get('school_name', 'Unknown School')
        school_id = sanitize_id(f"school_{school_name}")
        
        # Add school node
        if school_id not in nodes:
            lines.append(f'    {school_id} [label="{escape_label(school_name)}", fillcolor=lightblue];')
            nodes.add(school_id)
        
        for program in school.get('programs', []):
            program_name = program.get('program_name', 'Unknown Program')
            program_id = sanitize_id(f"program_{school_name}_{program_name}")
            
            # Add program node
            if program_id not in nodes:
                lines.append(f'    {program_id} [label="{escape_label(program_name)}", fillcolor=lightgreen];')
                nodes.add(program_id)
            
            # Add edge from school to program
            edge = (school_id, program_id)
            if edge not in edges:
                lines.append(f'    {school_id} -> {program_id};')
                edges.add(edge)
            
            # Process all courses (requirement and program)
            all_program_courses = program.get('program_courses', [])
            requirement_courses = program.get('requirement_courses', [])
            
            # Create nodes for all courses first
            for course in all_program_courses + requirement_courses:
                course_id_text = course.get('course_id', 'Unknown')
                course_title = course.get('course_title', 'Unknown')
                course_id = sanitize_id(f"course_{course_id_text}")
                
                if course_id not in nodes:
                    lines.append(f'    {course_id} [label="{escape_label(course_id_text)}\\n{escape_label(course_title)}", fillcolor=lightyellow];')
                    nodes.add(course_id)

            # Add edges for requirement courses
            for req_course in requirement_courses:
                req_course_id = sanitize_id(f"course_{req_course.get('course_id')}")
                edge = (program_id, req_course_id, 'requires')
                if edge not in edges:
                    lines.append(f'    {program_id} -> {req_course_id} [label="Requirement", color=red, style=bold];')
                    edges.add(edge)

            # Add edges for prerequisites
            for course in all_program_courses:
                course_id = sanitize_id(f"course_{course.get('course_id')}")
                for prereq in course.get('prerequisites', []):
                    prereq_id = sanitize_id(f"course_{prereq.get('course_id')}")
                    edge = (prereq_id, course_id, 'prereq')
                    if edge not in edges:
                        lines.append(f'    {prereq_id} -> {course_id} [label="Prereq", color=orange, style=dashed];')
                        edges.add(edge)
            
            lines.append('')
    
    # Close the digraph
    lines.append('}')
    
    # Write to file
    try:
        with open(dot_filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print(f"✓ DOT graph created successfully: {dot_filename}")
        print(f"\n  Total nodes: {len(nodes)}")
        print(f"  Total edges: {len(edges)}")
        print(f"\nTo generate an image, you need Graphviz installed. Then run:")
        print(f"  dot -Tpng {dot_filename} -o {dot_filename.replace('.dot', '.png')}")
        print(f"  dot -Tsvg {dot_filename} -o {dot_filename.replace('.dot', '.svg')}")
    except Exception as e:
        print(f"❌ Error creating DOT file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Check for JSON filename argument
    if len(sys.argv) < 2:
        print("Usage: python create_summary_graph.py <json_summary_file>")
        print("\nExample:")
        print("  python create_summary_graph.py 2025-2026_undergraduate.json")
        sys.exit(1)
    
    json_filename = sys.argv[1]
    
    # Load JSON data
    catalog_data = load_json_summary(json_filename)
    
    # Generate DOT filename
    dot_filename = get_dot_filename(json_filename)
    
    print(f"Creating DOT graph: {dot_filename}")
    
    # Create the DOT graph
    create_catalog_graph(catalog_data, dot_filename)