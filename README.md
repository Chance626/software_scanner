# software_scanner

A tool to scan and visualize code components without having to run the code or allow AI to access your code.

## Features
- **Privacy-First:** All scanning and report generation happens locally.
- **Visual Reports:** Generates an interactive HTML report with a side-by-side Directory Tree and a D3-powered Call Map.
- **Bidirectional Call Tracking:** Automatically resolves function calls, variable usage, and class inheritance within the codebase.
- **Interactive Map:** A force-directed graph (static after initial positioning) that allows you to drag nodes, zoom, and visualize connections.
- **Deep Navigation:** 
    - **Focus (🎯):** Instantly highlight and center any component in the Call Map from the Directory Tree.
    - **Fading Logic:** Clicking a node in the Call Map highlights its direct dependencies (calls and callers) while fading unrelated nodes.
    - **Automatic Sync:** Clicking map nodes expands the Directory Tree to the relevant definition.
- **Robust Python Parsing:** Uses the `ast` module to extract classes, functions, variables, docstrings, and type information (explicit or inferred).
- **Error Visibility:** Flags files with syntax errors using a ⚠️ icon, ensuring you know when code couldn't be fully parsed.

## Installation
Install the package from the current directory:
```bash
pip install .
```

## Usage
After installation, you can run the scanner using the `pyscan` command:
```bash
pyscan /path/to/project
```

Options:
- `-o, --output`: Specify the output path for the HTML report (default: `report.html`).
- `-n, --name`: Specify the project name for the report.

### Viewing the Report
The scanner generates two files: an HTML viewer and a JSON data file. Due to browser security restrictions (CORS) when fetching local files, you must use a local web server to view the report:

1. **Start a server** in the output directory:
   ```bash
   python3 -m http.server
   ```
2. **Open your browser** to `http://localhost:8000/report.html`.

## How it Works
The scanner recursively traverses the target directory using `networkx` to build two internal graphs:
1.  **Project Structure Graph:** Represents the physical directory and file hierarchy.
2.  **Call Graph:** Represents the logical dependencies between code components (Function calls, Class inheritance, etc.).

For Python files, the scanner extracts:
- **Classes, Functions, and Variables** (including nested structures).
- **Inheritance:** Tracks base classes to visualize class hierarchies.
- **Docstrings and Source Code** (with comments and docstrings scrubbed from the code view).
- **Type Information:** Detects both explicit type hints and heuristic inferences.

All project data is stored in a structured JSON file, which the HTML viewer renders dynamically using Vanilla JavaScript and D3.js.
