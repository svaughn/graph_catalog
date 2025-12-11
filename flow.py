#!/usr/bin/env python3

import subprocess
import sys
from urllib.parse import urlparse

def run_command(script_name: str, catalog_url: str) -> tuple[int, str, str]:
    """
    Run a Python script with the catalog URL as an argument.
    Returns (return_code, stdout, stderr).
    """
    try:
        result = subprocess.run(
            ["python3", script_name, catalog_url],
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)
    
def get_filename(catalog_url: str) -> str:
    """
    Extract the first two path elements from URL and create JSON filename.
    Example: https://catalog.sjf.edu/2025-2026/undergraduate/ug-academic-programs/
    Returns: 2025-2026_undergraduate.json
    """
    parsed = urlparse(catalog_url)
    path_parts = [p for p in parsed.path.split('/') if p]
    
    if len(path_parts) >= 2:
        return f"{path_parts[0]}_{path_parts[1]}"
    elif len(path_parts) == 1:
        return f"{path_parts[0]}"
    else:
        return "catalog_summary"

def get_json_filename(catalog_url: str) -> str:
    
    return get_filename(catalog_url) +".json"

def main():
    # Check for catalog URL argument
    if len(sys.argv) < 2:
        print("Usage: python flow.py <catalog_url>")
        print("\nExample:")
        print("  python flow.py https://catalog.sjf.edu/2025-2026/undergraduate/ug-academic-programs/")
        sys.exit(1)

    catalog_url = sys.argv[1]
    json_filename = get_json_filename(catalog_url)
    
    print("=" * 80)
    print("CATALOG ANALYSIS WORKFLOW")
    print("=" * 80)
    print(f"\nCatalog URL: {catalog_url}")
    print(f"JSON Output: {json_filename}\n")
    
    # Step 1: Create/load course dictionary
    print("=" * 80)
    print("STEP 1: Creating/Loading Course Dictionary")
    print("=" * 80)
    
    returncode, stdout, stderr = run_command("create_course_dictionary.py", catalog_url)
    
    # Print output from create_course_dictionary.py
    if stdout:
        print(stdout)
    
    if returncode != 0:
        print("\n❌ ERROR: create_course_dictionary.py failed")
        if stderr:
            print("\nError details:")
            print(stderr)
        sys.exit(1)
    
    print("✓ Course dictionary ready\n")
    
    # Step 2: Generate JSON summary
    print("=" * 80)
    print("STEP 2: Generating JSON Summary")
    print("=" * 80)
    
    returncode, stdout, stderr = run_command("get_catalog_summary_json.py", catalog_url)
    
    # Print output from get_catalog_summary_json.py
    if stdout:
        print(stdout)
    
    if returncode != 0:
        print("\n❌ ERROR: get_catalog_summary_json.py failed")
        if stderr:
            print("\nError details:")
            print(stderr)
        sys.exit(1)
    
    print(f"✓ JSON summary generated: {json_filename}\n")
    
    # Step 3: Print summary from JSON
    print("=" * 80)
    print("STEP 3: Printing Catalog Summary")
    print("=" * 80)
    
    returncode, stdout, stderr = run_command("print_catalog_summary.py", json_filename)
    
    # Print output from print_catalog_summary.py
    if stdout:
        print(stdout)
    
    if returncode != 0:
        print("\n❌ ERROR: print_catalog_summary.py failed")
        if stderr:
            print("\nError details:")
            print(stderr)
        sys.exit(1)

    # Step 4: Generate PDF (optional)
    print("=" * 80)
    print("STEP 4: Generating PDF Summary")
    print("=" * 80)

    returncode, stdout, stderr = run_command("create_catalog_summary_pdf.py", json_filename)

    if stdout:
        print(stdout)

    if returncode != 0:
        print("\n⚠️  Warning: PDF generation failed")
        if stderr:
            print(stderr)
    else:
        pdf_filename = json_filename.replace('.json', '.pdf')
        print(f"✓ PDF summary generated: {pdf_filename}\n")
    
    print("\n" + "=" * 80)
    print("✓ WORKFLOW COMPLETED SUCCESSFULLY")
    print("=" * 80)
    print(f"\nGenerated files:")
    print(f"  • " + get_filename(catalog_url) + ".ser")
    print(f"  • {json_filename}")

if __name__ == "__main__":
    main()