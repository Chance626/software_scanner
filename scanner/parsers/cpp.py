import clang.cindex
import os
from .base import Parser

# Configure libclang to use the system library if possible
try:
    if not clang.cindex.Config.loaded:
        pass
except Exception:
    pass

class CppParser(Parser):
    """C/C++ parser with aggressive comment extraction, namespace, and linkage support."""

    def __init__(self):
        self.index = clang.cindex.Index.create()

    def parse(self, content, extension=".cpp"):
        """Parse C++ content and capture documentation in gaps."""
        filename = f"src{extension}"
        unsaved_files = [(filename, content)]
        
        # Heuristic: treat .h as C++ header by default since many projects use it that way
        args = ['-std=c++17']
        if extension in [".h", ".hpp"]:
            args.extend(['-x', 'c++-header'])
        elif extension == ".c":
            args = ['-std=c11']
        
        try:
            tu = self.index.parse(
                filename, 
                args=args, 
                unsaved_files=unsaved_files,
                options=clang.cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
            )
            
            if not tu:
                return [], [], None

            # If it failed, try C mode for .h files
            if extension == ".h" and any(d.severity >= clang.cindex.Diagnostic.Fatal for d in tu.diagnostics):
                tu = self.index.parse(
                    filename, 
                    args=['-std=c11', '-x', 'c-header'], 
                    unsaved_files=unsaved_files,
                    options=clang.cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
                )

            # Identify children belonging to the main file
            children = []
            for child in tu.cursor.get_children():
                if self._is_in_main_file(child, filename):
                    children.append(child)
            children.sort(key=lambda x: x.location.offset)

            # File doc: everything before the first symbol
            first_offset = children[0].location.offset if children else len(content)
            file_doc = self._extract_comments_in_range(tu, 0, first_offset)

            components = self._parse_cursors(children, tu, content, filename)
            imports = self._extract_inclusions(tu)
            
            return components, imports, file_doc
        except Exception as e:
            # Most likely 'Error parsing translation unit' which is a broad error from libclang
            # We'll just return empty and let the scanner continue
            return [], [], None

    def _is_in_main_file(self, cursor, filename):
        """Check if a cursor is located in the main dummy file."""
        if not cursor.location.file:
            return False
        return os.path.basename(cursor.location.file.name) == filename

    def _extract_comments_in_range(self, tu, start_offset, end_offset):
        """Extract all comments found between two offsets in the translation unit."""
        extracted = []
        try:
            tokens = tu.get_tokens(extent=tu.cursor.extent)
            for token in tokens:
                if token.kind == clang.cindex.TokenKind.COMMENT:
                    if start_offset <= token.extent.start.offset < end_offset:
                        cleaned = self._clean_comment(token.spelling)
                        if cleaned:
                            extracted.append(cleaned)
                    elif token.extent.start.offset >= end_offset:
                        break
        except Exception:
            pass
        return "\n".join(extracted) if extracted else None

    def _parse_cursors(self, cursors, tu, full_content, filename, include_variables=True):
        """Recursively traverse the AST and capture documentation in gaps."""
        components = []
        
        for i, child in enumerate(cursors):
            kind = child.kind
            name = child.spelling
            
            next_start = cursors[i+1].location.offset if i + 1 < len(cursors) else len(full_content)
            gap_doc = self._extract_comments_in_range(tu, child.extent.end.offset, next_start)
            formal_doc = self._clean_comment(child.raw_comment)
            merged_doc = self._merge_docs(formal_doc, gap_doc)

            comp = None
            
            if kind in [clang.cindex.CursorKind.NAMESPACE, clang.cindex.CursorKind.LINKAGE_SPEC, clang.cindex.CursorKind.UNEXPOSED_DECL]:
                child_cursors = sorted(
                    [c for c in child.get_children() if self._is_in_main_file(c, filename)],
                    key=lambda x: x.location.offset
                )
                components.extend(self._parse_cursors(child_cursors, tu, full_content, filename, include_variables))
                continue

            if not name and kind not in [clang.cindex.CursorKind.VAR_DECL, clang.cindex.CursorKind.FIELD_DECL]:
                continue

            if kind == clang.cindex.CursorKind.CLASS_DECL or kind == clang.cindex.CursorKind.STRUCT_DECL:
                child_cursors = sorted(
                    [c for c in child.get_children() if self._is_in_main_file(c, filename)],
                    key=lambda x: x.location.offset
                )
                type_name = "class" if kind == clang.cindex.CursorKind.CLASS_DECL else "struct"
                comp = {
                    "name": name,
                    "type": type_name,
                    "short_name": name,
                    "bases": self._get_base_classes(child),
                    "docstring": merged_doc,
                    "source": self._get_source(child, full_content),
                    "calls": self._extract_calls(child),
                    "children": self._parse_cursors(child_cursors, tu, full_content, filename, include_variables=True)
                }
                
            elif kind == clang.cindex.CursorKind.FUNCTION_DECL or kind == clang.cindex.CursorKind.CXX_METHOD:
                comp = {
                    "name": name,
                    "type": "function",
                    "short_name": name,
                    "args": self._get_function_args(child),
                    "returns": {"type": child.result_type.spelling, "explicit": True},
                    "docstring": merged_doc,
                    "source": self._get_source(child, full_content),
                    "calls": self._extract_calls(child),
                    "children": []
                }

            elif kind in [clang.cindex.CursorKind.TYPEDEF_DECL, clang.cindex.CursorKind.TYPE_ALIAS_DECL]:
                comp = {
                    "name": name,
                    "type": "type",
                    "short_name": name,
                    "docstring": merged_doc,
                    "source": self._get_source(child, full_content)
                }

            elif include_variables and (kind in [clang.cindex.CursorKind.VAR_DECL, clang.cindex.CursorKind.FIELD_DECL, clang.cindex.CursorKind.ENUM_DECL]):
                comp = {
                    "name": name or "unnamed",
                    "type": "variable",
                    "short_name": name or "unnamed",
                    "docstring": merged_doc,
                    "source": self._get_source(child, full_content)
                }
            
            if comp:
                components.append(comp)
                
        return components

    def _merge_docs(self, doc1, doc2):
        doc = ""
        if doc1 and doc2: doc = f"{doc1}\n{doc2}"
        elif doc1: doc = doc1
        elif doc2: doc = doc2
        
        if not doc: return None
        import re
        return re.sub(r'\n+', '\n', doc).strip()

    def _get_base_classes(self, cursor):
        bases = []
        try:
            for child in cursor.get_children():
                if child.kind == clang.cindex.CursorKind.CXX_BASE_SPECIFIER:
                    bases.append(child.type.spelling)
        except Exception: pass
        return bases

    def _get_function_args(self, cursor):
        args = []
        try:
            for child in cursor.get_children():
                if child.kind == clang.cindex.CursorKind.PARM_DECL:
                    args.append({"name": child.spelling, "type": child.type.spelling, "explicit": True})
        except Exception: pass
        return args

    def _extract_calls(self, cursor):
        calls = []
        try:
            for node in cursor.walk_preorder():
                if node == cursor: continue
                if node.kind == clang.cindex.CursorKind.CALL_EXPR:
                    name = node.spelling
                    if name and name not in calls: calls.append(name)
        except Exception: pass
        return calls

    def _clean_comment(self, comment):
        if not comment: return None
        lines = comment.splitlines()
        cleaned = []
        for line in lines:
            line = line.strip().lstrip('/*').lstrip('*/').lstrip('///').lstrip('//').strip()
            if line: cleaned.append(line)
        return "\n".join(cleaned) if cleaned else None

    def _extract_inclusions(self, tu):
        imports = []
        try:
            for inc in tu.get_includes():
                name = os.path.basename(inc.include.name)
                if name not in imports: imports.append(name)
        except Exception: pass
        return imports

    def _get_source(self, cursor, full_content):
        try:
            extent = cursor.extent
            return full_content[extent.start.offset:extent.end.offset]
        except Exception: return ""
