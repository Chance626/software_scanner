# software_scanner

A tool to scan and visualize code components locally, ensuring privacy while providing deep insights into project architecture.

## Features
- **Privacy-First:** All scanning and report generation happens locally. No code is sent to external servers or AI.
- **Visual Reports:** Generates an interactive HTML report with a side-by-side Directory Tree and a D3-powered Call Map.
- **Multilingual Support:**
    - **Python:** Uses the `ast` module to extract classes, functions, variables, and type info.
    - **C/C++:** Uses `libclang` to parse `.c`, `.cc`, `.cpp`, `.h`, and `.hpp` files, including support for namespaces, structs, enums, and `extern "C"` blocks.
- **Intelligent Documentation:** Aggressive comment extraction captures documentation from formal docstrings and "gap" comments between code symbols, displayed in compact daffodil-yellow boxes.
- **Scalable Performance:** 
    - **Parallel Parsing:** Multi-core support for high-speed scanning of large repositories.
    - **Lazy Rendering:** UI remains responsive on massive projects (e.g., MuJoCo) by loading tree nodes and source code only on demand.
- **Interactive Map & Navigation:**
    - **Bidirectional Sync:** Clicking map regions or nodes navigates the directory tree; using **Highlight (🔦)** or **Focus (🎯)** buttons in the tree centers the map on the relevant symbols.
    - **Smart Regions:** Group nodes by file or directory with togglable shading to visualize the physical organization of logic.
    - **Per-Directory Stats:** Instantly see file counts and lines of code for any branch of the tree.

## Installation
Install the package and its core dependencies:
```bash
pip install .
```

### C/C++ Support (Optional)
To enable C/C++ parsing, you must have `libclang` installed on your system:
```bash
pip install libclang
# Ensure LLVM/Clang is installed on your OS (e.g., sudo apt install libclang-dev)
```

## Usage
Run the scanner using the `pyscan` command:
```bash
pyscan /path/to/project [options]
```

### Options:
- `-p, --parallel`: Number of workers (e.g., `-p 4`) or percentage of cores (e.g., `-p 0.5`). Default: 1 (serial).
- `-o, --output`: Specify the output path for the HTML report (default: `report.html`).
- `-n, --name`: Specify the project name for the report.

### Example:
```bash
# Scan a large project using half of your CPU cores
pyscan ../mujoco -p 0.5 -n "MuJoCo Analysis"
```

### Viewing the Report
The scanner generates an HTML viewer and a JSON data file. Due to browser security restrictions (CORS), you must use a local web server to view the report:

1. **Start a server** in the output directory:
   ```bash
   python3 -m http.server
   ```
2. **Open your browser** to `http://localhost:8000/report.html`.

## How it Works
1.  **Discovery:** Recursively walks the directory tree, calculating statistics and identifying code files.
2.  **Parsing:** (Optional Parallel) Extracted components, imports, and comments are mapped into a `networkx` graph.
3.  **Resolution:** Logic maps every function call and class inheritance to its definition across the entire project.
4.  **Reporting:** Data is serialized to JSON, and a responsive HTML/D3.js environment is generated for exploration.

Project data includes:
- **Symbols:** Classes, Structs, Functions, Variables, Enums, and Types.
- **Inheritance:** Visualization of class and struct hierarchies.
- **Source Code:** On-demand viewing of implementations for functions and variables.
- **Documentation:** Unified view of comments and docstrings.
