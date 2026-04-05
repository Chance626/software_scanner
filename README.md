# software_scanner

A tool to scan and visualize code components without having to run the code or allow AI to access your code.

## Features
- **Privacy-First:** All scanning and report generation happens locally.
- **Visual Reports:** Generates an interactive HTML report to visualize project structure and metrics.
- **Language Agnostic:** Supports common code, configuration, and documentation file types.

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
The scanner recursively traverses the target directory using `networkx` to build a directed graph of the project structure. For Python files, it employs the `ast` module to extract:
- **Classes, Functions, and Variables** (including nested structures).
- **Docstrings and Source Code** (with comments and docstrings scrubbed from the code view).
- **Type Information** (detecting both explicit type hints and heuristic inferences).

All project data is stored in a structured JSON file, which the HTML viewer renders dynamically using Vanilla JavaScript.
