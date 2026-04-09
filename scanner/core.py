import os
from pathlib import Path
import networkx as nx
from .parsers.python import PythonParser

class Scanner:
    def __init__(self, target_dir):
        self.target_dir = Path(target_dir).resolve()
        self.graph = nx.DiGraph()
        self.parsers = {
            ".py": PythonParser()
        }
        self.ignore_dirs = {".git", "__pycache__", "venv", "bin", "lib", "lib64", "include"}

    def scan(self):
        """Recursively scan and build a networkx DiGraph of the project structure."""
        root_name = self.target_dir.name or str(self.target_dir)
        self.graph.add_node(".", type="directory", name=root_name, path=".")
        
        for root, dirs, files in os.walk(self.target_dir):
            # Filtering ignored directories
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

                line_count = 0
                content = ""
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as file_obj:
                        content = file_obj.read()
                        line_count = len(content.splitlines())
                except Exception:
                    pass

                self.graph.add_node(rel_file_path, 
                                   type="file", 
                                   name=f, 
                                   path=rel_file_path,
                                   extension=extension,
                                   line_count=line_count,
                                   file_type=self._guess_type(extension),
                                   source=content)
                self.graph.add_edge(parent_node, rel_file_path)

                if extension in self.parsers:
                    components, imports = self.parsers[extension].parse(content)
                    self._add_components(rel_file_path, components)
                    self.graph.nodes[rel_file_path]["imports"] = imports

        return self.graph, "."

    def _add_components(self, parent_node, components, prefix=""):
        """Recursively add components to the graph."""
        for comp in components:
            node_name = comp.get("short_name", comp["name"])
            comp_id = f"{parent_node}::{prefix}{node_name}"
            
            # Extract children to handle them separately
            children = comp.pop("children", [])
            
            self.graph.add_node(comp_id, **comp)
            self.graph.add_edge(parent_node, comp_id)
            
            if children:
                self._add_components(comp_id, children, prefix=f"{node_name}.")

    def _guess_type(self, extension):
        code_exts = {".py", ".js", ".ts", ".c", ".cpp", ".go", ".rs", ".java", ".sh", ".bash"}
        config_exts = {".json", ".yaml", ".yml", ".toml", ".xml", ".ini", ".env"}
        doc_exts = {".md", ".txt", ".pdf", ".html", ".css"}
        if extension in code_exts: return "code"
        if extension in config_exts: return "config"
        if extension in doc_exts: return "doc"
        return "other"
