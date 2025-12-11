#!/usr/bin/env python3

import subprocess
import sys
from urllib.parse import urlparse

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

# refactor these two funtions out eventually
def get_filename(catalog_url: str) -> str:

    return get_base_filename(catalog_url)

def get_json_filename(catalog_url: str) -> str:
    
    return get_filename(catalog_url) +".json"

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

def main():
    # Check for catalog URL argument
    if len(sys.argv) < 2:
        print("Usage: python flow.py <catalog_url>")
        print("\nExample:")
        print("  python flow.py https://catalog.sjf.edu/2025-2026/undergraduate/ug-academic-programs/")
        sys.exit(1)

    catalog_url = sys.argv[1]
    base_filename = get_base_filename(catalog_url)
    json_filename = f"{base_filename}.json"
    pdf_filename = f"{base_filename}.pdf"
    dot_filename = f"{base_filename}.dot"
    svg_filename = f"{base_filename}.svg"
    dependencies_pdf_filename = f"{base_filename}_dependencies.pdf" # New filename
    
    print("=" * 80)
    print("CATALOG ANALYSIS WORKFLOW")
    print("=" * 80)
    print(f"\nCatalog URL: {catalog_url}")
    print(f"JSON Output: {json_filename}")
    print(f"PDF Output:  {pdf_filename}")
    print(f"DOT Output:  {dot_filename}")
    print(f"SVG Output:  {svg_filename}")
    print(f"Deps PDF:    {dependencies_pdf_filename}\n") # New output listed
    
    # Step 1: Create/load course dictionary
    print("=" * 80)
    print("STEP 1: Creating/Loading Course Dictionary")
    print("=" * 80)
    returncode, stdout, stderr = run_command(["python3", "create_course_dictionary.py", catalog_url])
    if stdout: print(stdout)
    if returncode != 0:
        print(f"\n❌ ERROR: create_course_dictionary.py failed.\n{stderr}")
        sys.exit(1)
    print("✓ Course dictionary ready\n")
    
    # Step 2: Generate JSON summary
    print("=" * 80)
    print("STEP 2: Generating JSON Summary")
    print("=" * 80)
    returncode, stdout, stderr = run_command(["python3", "get_catalog_summary_json.py", catalog_url])
    if stdout: print(stdout)
    if returncode != 0:
        print(f"\n❌ ERROR: get_catalog_summary_json.py failed.\n{stderr}")
        sys.exit(1)
    print(f"✓ JSON summary generated: {json_filename}\n")
    
    # Step 3: Print summary from JSON
    print("=" * 80)
    print("STEP 3: Printing Catalog Summary")
    print("=" * 80)
    returncode, stdout, stderr = run_command(["python3", "print_catalog_summary.py", json_filename])
    if stdout: print(stdout)
    if returncode != 0:
        print(f"\n❌ ERROR: print_catalog_summary.py failed.\n{stderr}")
        sys.exit(1)
    print("✓ Text summary printed successfully.\n")

    # Step 4: Generate PDF
    print("=" * 80)
    print("STEP 4: Generating PDF Summary")
    print("=" * 80)
    returncode, stdout, stderr = run_command(["python3", "create_catalog_summary_pdf.py", json_filename])
    if stdout: print(stdout)
    if returncode != 0:
        print(f"\n⚠️  Warning: PDF generation failed.\n{stderr}")
    else:
        print(f"✓ PDF summary generated: {pdf_filename}\n")

    # Step 5: Generate DOT graph from JSON
    print("=" * 80)
    print("STEP 5: Generating DOT Graph")
    print("=" * 80)
    returncode, stdout, stderr = run_command(["python3", "create_summary_graph.py", json_filename])
    if stdout: print(stdout)
    if returncode != 0:
        print(f"\n❌ ERROR: create_summary_graph.py failed.\n{stderr}")
        sys.exit(1)
    print(f"✓ DOT graph generated: {dot_filename}\n")

    # Step 6: Generate SVG from DOT
    print("=" * 80)
    print("STEP 6: Generating SVG from DOT")
    print("=" * 80)
    returncode, stdout, stderr = run_command(["dot", "-Tsvg", dot_filename, "-o", svg_filename])
    if stdout: print(stdout)
    if returncode == -1:
        print(f"\n⚠️  WARNING: Graphviz 'dot' command not found. Skipping SVG generation.")
        print("   To install it, run: 'sudo apt-get install graphviz' or 'brew install graphviz'")
    elif returncode != 0:
        print(f"\n⚠️  WARNING: SVG generation failed.\n{stderr}")
    else:
        print(f"✓ SVG graph generated: {svg_filename}\n")

    # Step 7: Generate Course Dependency PDF (NEW STEP)
    print("=" * 80)
    print("STEP 7: Generating Course Dependency PDF")
    print("=" * 80)
    returncode, stdout, stderr = run_command(["python3", "get_dependencies_pdf.py", json_filename])
    if stdout: print(stdout)
    if returncode != 0:
        print(f"\n⚠️  Warning: Dependency PDF generation failed.\n{stderr}")
    else:
        print(f"✓ Dependency PDF generated: {dependencies_pdf_filename}\n")

    print("\n" + "=" * 80)
    print("✓ WORKFLOW COMPLETED")
    print("=" * 80)
    print(f"\nGenerated files:")
    print(f"  • course_dictionary.ser")
    print(f"  • {json_filename}")
    print(f"  • {pdf_filename} (if successful)")
    print(f"  • {dot_filename}")
    print(f"  • {svg_filename} (if Graphviz is installed and successful)")
    print(f"  • {dependencies_pdf_filename} (if successful)") # New file listed

if __name__ == "__main__":
    main()