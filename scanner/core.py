import os
from pathlib import Path
import networkx as nx
from concurrent.futures import ProcessPoolExecutor
from .parsers.python import PythonParser
from .parsers.cpp import CppParser

def parse_file_task(file_path, extension):
    """Worker task to parse a single file."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
        parser = None
        if extension == ".py":
            parser = PythonParser()
        elif extension in [".cpp", ".cc", ".c", ".h", ".hpp"]:
            parser = CppParser()
            
        if parser:
            if isinstance(parser, CppParser):
                components, imports, file_doc = parser.parse(content, extension=extension)
            else:
                components, imports, file_doc = parser.parse(content)
            return {
                "rel_file_path": str(file_path), # We'll need to resolve this back to relative
                "components": components,
                "imports": imports,
                "file_doc": file_doc,
                "content": content,
                "line_count": len(content.splitlines())
            }
    except Exception as e:
        print(f"  [Warning] Error parsing {file_path}: {e}")
    return None

class Scanner:
    def __init__(self, target_dir):
        self.target_dir = Path(target_dir).resolve()
        self.graph = nx.DiGraph()
        self.call_graph = nx.DiGraph()
        self.parsers = {
            ".py": PythonParser(),
            ".cpp": CppParser(),
            ".cc": CppParser(),
            ".hpp": CppParser(),
            ".c": CppParser(),
            ".h": CppParser()
        }
        self.ignore_dirs = {".git", "__pycache__", "venv", "bin", "lib", "lib64"}

    def scan(self, num_workers=1):
        """Recursively scan and build a networkx DiGraph of the project structure."""
        import time
        self.timings = {}
        
        start_discovery = time.time()
        root_name = self.target_dir.name or str(self.target_dir)
        self.graph.add_node(".", type="directory", name=root_name, path=".")
        
        files_to_process = []
        
        for root, dirs, files in os.walk(self.target_dir):
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]

            rel_root = Path(root).relative_to(self.target_dir)
            parent_node = str(rel_root)

            for d in dirs:
                dir_path = str(rel_root / d)
                self.graph.add_node(dir_path, type="directory", name=d, path=dir_path)
                self.graph.add_edge(parent_node, dir_path)

            for f in files:
                file_path = Path(root) / f
                rel_file_path = str(rel_root / f)
                extension = file_path.suffix.lower()
                
                self.graph.add_node(rel_file_path, 
                                   type="file", 
                                   name=f, 
                                   path=rel_file_path,
                                   extension=extension,
                                   file_type=self._guess_type(extension))
                self.graph.add_edge(parent_node, rel_file_path)

                if extension in self.parsers:
                    files_to_process.append((file_path, rel_file_path, extension))
                else:
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as file_obj:
                            lines = file_obj.readlines()
                            self.graph.nodes[rel_file_path]["line_count"] = len(lines)
                    except Exception: pass
        
        self.timings["discovery"] = time.time() - start_discovery
        
        start_parsing = time.time()
        if num_workers > 1 and len(files_to_process) > 1:
            with ProcessPoolExecutor(max_workers=num_workers) as executor:
                futures = [executor.submit(parse_file_task, f[0], f[2]) for f in files_to_process]
                for i, future in enumerate(futures):
                    result = future.result()
                    if result:
                        rel_path = files_to_process[i][1]
                        self._apply_parse_result(rel_path, result)
        else:
            for file_path, rel_file_path, extension in files_to_process:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    
                    parser = self.parsers[extension]
                    if isinstance(parser, CppParser):
                        components, imports, file_doc = parser.parse(content, extension=extension)
                    else:
                        components, imports, file_doc = parser.parse(content)
                    result = {
                        "components": components,
                        "imports": imports,
                        "file_doc": file_doc,
                        "content": content,
                        "line_count": len(content.splitlines())
                    }
                    self._apply_parse_result(rel_file_path, result)
                except Exception as e:
                    print(f"  [Warning] Error parsing {rel_file_path}: {e}")
        
        self.timings["parsing"] = time.time() - start_parsing

        start_resolution = time.time()
        self._resolve_calls()
        self.timings["resolution"] = time.time() - start_resolution
        
        return self.graph, self.call_graph, "."

    def _apply_parse_result(self, rel_path, result):
        """Update graph with results from a file parse."""
        self.graph.nodes[rel_path].update({
            "source": result["content"],
            "line_count": result["line_count"],
            "imports": result["imports"]
        })
        if result["file_doc"]:
            self.graph.nodes[rel_path]["docstring"] = result["file_doc"]
            
        self._add_components(rel_path, result["components"])

    def _resolve_calls(self):
        """Build the call graph by resolving symbol names to node IDs."""
        symbol_map = {}
        for node_id, data in self.graph.nodes(data=True):
            if data.get("type") in ["class", "function", "variable"]:
                name = data.get("name")
                if name:
                    if name not in symbol_map: symbol_map[name] = []
                    symbol_map[name].append(node_id)
        
        for node_id, data in self.graph.nodes(data=True):
            calls = data.get("calls", [])
            for call_name in calls:
                if call_name in symbol_map:
                    for target_id in symbol_map[call_name]:
                        self.call_graph.add_edge(node_id, target_id, type="call")
            
            if data.get("type") == "class":
                bases = data.get("bases", [])
                for base_name in bases:
                    if base_name in symbol_map:
                        for target_id in symbol_map[base_name]:
                            self.call_graph.add_edge(node_id, target_id, type="inheritance")

    def _add_components(self, parent_node, components, prefix=""):
        """Recursively add components to the graph."""
        for comp in components:
            node_name = comp.get("short_name", comp["name"])
            comp_id = f"{parent_node}::{prefix}{node_name}"
            children = comp.pop("children", [])
            self.graph.add_node(comp_id, **comp)
            self.graph.add_edge(parent_node, comp_id)
            if children:
                self._add_components(comp_id, children, prefix=f"{node_name}.")

    def _guess_type(self, extension):
        code_exts = {".py", ".js", ".ts", ".c", ".cpp", ".cc", ".h", ".hpp", ".go", ".rs", ".java", ".sh", ".bash"}
        config_exts = {".json", ".yaml", ".yml", ".toml", ".xml", ".ini", ".env"}
        doc_exts = {".md", ".txt", ".pdf", ".html", ".css"}
        if extension in code_exts: return "code"
        if extension in config_exts: return "config"
        if extension in doc_exts: return "doc"
        return "other"
