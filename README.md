# software_scanner

A tool to scan and visualize code components without having to run the code or allow AI to access your code.

## Features
- **Privacy-First:** All scanning and report generation happens locally.
- **Visual Reports:** Generates an interactive HTML report to visualize project structure and metrics.
- **Language Agnostic:** Supports common code, configuration, and documentation file types.

## Installation
```bash
pip install -r requirements.txt
```

## Usage
Scan a directory and generate a report:
```bash
python cli.py /path/to/project
```

Options:
- `-o, --output`: Specify the output path for the HTML report (default: `report.html`).
- `-n, --name`: Specify the project name for the report.

## How it Works
The scanner recursively traverses the target directory, identifies file types based on extensions, and calculates basic metrics (like line counts). It then uses Jinja2 to generate a static HTML report with a modern UI.
