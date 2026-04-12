import ast
import copy
import re
from .base import Parser

class PythonParser(Parser):
    """Python parser with aggressive comment extraction."""
    def parse(self, content):
        try:
            tree = ast.parse(content)
            lines = content.splitlines()
            
            # Sort top-level nodes by line number
            nodes = sorted([n for n in tree.body if hasattr(n, 'lineno')], key=lambda x: x.lineno)
            
            # File-level documentation: everything from start to first symbol
            first_lineno = nodes[0].lineno if nodes else len(lines) + 1
            file_doc = self._extract_comments_in_range(1, first_lineno - 1, lines)
            # Add formal docstring if present
            formal_file_doc = ast.get_docstring(tree)
            if formal_file_doc:
                file_doc = (file_doc + "\n\n" + formal_file_doc) if file_doc else formal_file_doc

            components = self._parse_nodes(nodes, lines, include_variables=True)
            imports = self._parse_imports(tree.body)
            
            return components, imports, file_doc
        except SyntaxError as e:
            print(f"  [Warning] Syntax error in file: {e}")
            return [], [], None

    def _extract_comments_in_range(self, start_line, end_line, lines):
        """Extract all comments found between start_line and end_line (1-based)."""
        extracted = []
        # Clamp ranges
        start = max(0, start_line - 1)
        end = min(len(lines), end_line)
        
        for i in range(start, end):
            line = lines[i].strip()
            if line.startswith('#'):
                extracted.append(line.lstrip('#').strip())
            # We skip non-comment lines but keep searching until the end_line
        
        return "\n".join(extracted) if extracted else None

    def _parse_nodes(self, nodes, lines, include_variables=True):
        """Parse a list of nodes and capture trailing comments."""
        components = []
        for i, node in enumerate(nodes):
            comp = None
            
            # Determine the end of this node's documentation scope
            # It ends either at the start of the next node or the end of the parent's body
            next_node_start = nodes[i+1].lineno if i + 1 < len(nodes) else len(lines) + 1
            
            if isinstance(node, ast.ClassDef):
                # Class body children
                child_nodes = sorted([n for n in node.body if hasattr(n, 'lineno')], key=lambda x: x.lineno)
                docstring = ast.get_docstring(node)
                # Trailing comments for class: from end of its body until next sibling
                trailing = self._extract_comments_in_range(node.end_lineno + 1, next_node_start - 1, lines)
                
                comp = {
                    "name": node.name,
                    "type": "class",
                    "short_name": node.name,
                    "bases": [ast.unparse(b) for b in node.bases],
                    "docstring": self._merge_docs(docstring, trailing),
                    "source": self._get_scrubbed_source(node),
                    "calls": self._extract_calls(node.body),
                    "children": self._parse_nodes(child_nodes, lines, include_variables=True)
                }
                
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                docstring = ast.get_docstring(node)
                trailing = self._extract_comments_in_range(node.end_lineno + 1, next_node_start - 1, lines)
                
                child_nodes = sorted([n for n in node.body if hasattr(n, 'lineno')], key=lambda x: x.lineno)
                
                comp = {
                    "name": node.name,
                    "type": "function",
                    "short_name": node.name,
                    "args": self._get_args(node),
                    "returns": self._get_returns(node),
                    "docstring": self._merge_docs(docstring, trailing),
                    "source": self._get_scrubbed_source(node),
                    "calls": self._extract_calls(node.body),
                    "children": self._parse_nodes(child_nodes, lines, include_variables=False)
                }
                
            elif isinstance(node, ast.Assign) and include_variables:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        trailing = self._extract_comments_in_range(node.end_lineno + 1, next_node_start - 1, lines)
                        comp = {
                            "name": target.id,
                            "type": "variable",
                            "docstring": trailing,
                            "source": ast.unparse(node)
                        }
                        break # Just take the first target for simplicity
            
            if comp:
                components.append(comp)
                
        return components

    def _merge_docs(self, doc1, doc2):
        doc = ""
        if doc1 and doc2: doc = f"{doc1}\n{doc2}"
        elif doc1: doc = doc1
        elif doc2: doc = doc2
        
        if not doc: return None
        # Remove all blank lines (collapse multiple newlines into one)
        return re.sub(r'\n+', '\n', doc).strip()

    def _get_args(self, node):
        args = []
        for arg in node.args.args:
            arg_info = {"name": arg.arg, "explicit": False, "type": ""}
            if arg.annotation:
                try: arg_info["type"] = ast.unparse(arg.annotation); arg_info["explicit"] = True
                except Exception: pass
            args.append(arg_info)
        return args

    def _get_returns(self, node):
        ret = {"type": "None", "explicit": False}
        if node.returns:
            try: ret["type"] = ast.unparse(node.returns); ret["explicit"] = True
            except Exception: pass
        return ret

    def _parse_imports(self, body):
        imports = []
        for node in body:
            if isinstance(node, ast.Import):
                for alias in node.names: imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module if node.module else ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}" if module else alias.name)
        return imports

    def _extract_calls(self, body):
        calls = []
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)): continue
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    try:
                        name = ast.unparse(child.func)
                        if name not in calls: calls.append(name)
                    except Exception: pass
        return calls

    def _get_scrubbed_source(self, node):
        node_copy = copy.deepcopy(node)
        if hasattr(node_copy, 'body') and node_copy.body:
            first = node_copy.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                if ast.get_docstring(node):
                    node_copy.body.pop(0)
                    if not node_copy.body: node_copy.body.append(ast.Pass())
        return ast.unparse(node_copy)
