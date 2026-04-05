import os
import ast
import copy
from pathlib import Path
import networkx as nx

class Parser:
    """Base class for language-specific parsers."""
    def parse(self, content):
        raise NotImplementedError("Subclasses must implement parse()")

class PythonParser(Parser):
    """Python parser using the built-in ast module."""
    def parse(self, content):
        try:
            tree = ast.parse(content)
            return self._parse_body(tree.body)
        except SyntaxError:
            return []

    def _parse_body(self, body):
        """Recursively parse a list of AST nodes."""
        components = []
        for node in body:
            if isinstance(node, ast.ClassDef):
                components.append({
                    "name": node.name,
                    "type": "class",
                    "short_name": node.name,
                    "docstring": ast.get_docstring(node),
                    "source": self._get_scrubbed_source(node),
                    "children": self._parse_body(node.body)
                })
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                components.append(self._parse_function(node))
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        components.append({
                            "name": target.id,
                            "type": "variable",
                            "docstring": None,
                            "source": ast.unparse(node)
                        })
        return components

    def _get_scrubbed_source(self, node):
        """Returns the source code of a node with docstrings and comments removed."""
        node_copy = copy.deepcopy(node)
        if hasattr(node_copy, 'body') and node_copy.body:
            # Check if the first statement is a docstring
            first = node_copy.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                if ast.get_docstring(node):
                    node_copy.body.pop(0)
                    if not node_copy.body:
                        node_copy.body.append(ast.Pass())
        return ast.unparse(node_copy)

    def _parse_function(self, node):
        """Helper to parse function arguments, returns, docstrings and nested children."""
        parsed_args = []
        for arg in node.args.args:
            arg_info = {"name": arg.arg, "explicit": False, "type": ""}
            if arg.annotation:
                try:
                    arg_info["type"] = ast.unparse(arg.annotation)
                    arg_info["explicit"] = True
                except Exception: pass
            parsed_args.append(arg_info)
        
        return_info = {"type": "None", "explicit": False}
        if node.returns:
            try:
                return_info["type"] = ast.unparse(node.returns)
                return_info["explicit"] = True
            except Exception: pass
        else:
            return_values = []
            for child in ast.walk(node):
                if isinstance(child, ast.Return) and child.value:
                    try:
                        val = ast.unparse(child.value)
                        if val not in return_values:
                            return_values.append(val)
                    except Exception: pass
            if return_values:
                return_info["type"] = " | ".join(return_values[:3])
                return_info["explicit"] = False

        return {
            "name": node.name,
            "type": "function",
            "short_name": node.name,
            "args": parsed_args,
            "returns": return_info,
            "docstring": ast.get_docstring(node),
            "source": self._get_scrubbed_source(node),
            "children": self._parse_body(node.body)
        }

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
                                   file_type=self._guess_type(extension))
                self.graph.add_edge(parent_node, rel_file_path)

                if extension in self.parsers:
                    components = self.parsers[extension].parse(content)
                    self._add_components(rel_file_path, components)

        return self.graph, "."

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
        code_exts = {".py", ".js", ".ts", ".c", ".cpp", ".go", ".rs", ".java", ".sh", ".bash"}
        config_exts = {".json", ".yaml", ".yml", ".toml", ".xml", ".ini", ".env"}
        doc_exts = {".md", ".txt", ".pdf", ".html", ".css"}
        if extension in code_exts: return "code"
        if extension in config_exts: return "config"
        if extension in doc_exts: return "doc"
        return "other"
