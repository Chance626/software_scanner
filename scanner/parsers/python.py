import ast
import copy
from .base import Parser

class PythonParser(Parser):
    """Python parser using the built-in ast module."""
    def parse(self, content):
        try:
            tree = ast.parse(content)
            # Global variables are usually desired, so we start with True
            components = self._parse_body(tree.body, include_variables=True)
            imports = self._parse_imports(tree.body)
            return components, imports
        except SyntaxError:
            return [], []

    def _parse_imports(self, body):
        """Extract imports from the AST."""
        imports = []
        for node in body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module if node.module else ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}" if module else alias.name)
        return imports

    def _parse_body(self, body, include_variables=True):
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
                    # Class variables should be included
                    "children": self._parse_body(node.body, include_variables=True)
                })
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                components.append(self._parse_function(node))
            elif isinstance(node, ast.Assign) and include_variables:
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
            # Variables defined within functions are now excluded
            "children": self._parse_body(node.body, include_variables=False)
        }
