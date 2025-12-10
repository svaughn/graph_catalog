#!/usr/bin/env python3

import subprocess
import sys

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

def main():
    # Check for catalog URL argument
    if len(sys.argv) < 2:
        print("Usage: python flow.py <catalog_url>")
        print("\nExample:")
        print("  python flow.py https://catalog.sjf.edu/2025-2026/")
        sys.exit(1)

    catalog_url = sys.argv[1]
    
    print("=" * 80)
    print("CATALOG ANALYSIS WORKFLOW")
    print("=" * 80)
    print(f"\nCatalog URL: {catalog_url}\n")
    
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
    
    # Step 2: Summarize catalog
    print("=" * 80)
    print("STEP 2: Summarizing Catalog")
    print("=" * 80)
    
    returncode, stdout, stderr = run_command("summarize_catalog.py", catalog_url)
    
    # Print output from summarize_catalog.py
    if stdout:
        print(stdout)
    
    if returncode != 0:
        print("\n❌ ERROR: summarize_catalog.py failed")
        if stderr:
            print("\nError details:")
            print(stderr)
        sys.exit(1)
    
    print("\n" + "=" * 80)
    print("✓ WORKFLOW COMPLETED SUCCESSFULLY")
    print("=" * 80)

if __name__ == "__main__":
    main()
