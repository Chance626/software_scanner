import datetime
from pathlib import Path
import networkx as nx
import html

class ReportGenerator:
    def __init__(self, template_path="templates/report.html"):
        self.template_path = Path(template_path)

    def generate(self, graph, root_node, project_name, output_path="report.html"):
        """Generate the HTML report by traversing the networkx graph."""
        total_lines, code_count, total_files = self._get_stats(graph)
        scan_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(self.template_path, "r", encoding="utf-8") as f:
            template_content = f.read()

        # Render the recursive graph to HTML starting from root
        visited = set()
        tree_html = self._render_node(graph, root_node, visited)

        # Replacing simple variables
        html_content = template_content.replace("{{ project_name }}", project_name)
        html_content = html_content.replace("{{ scan_date }}", scan_date)
        html_content = html_content.replace("{{ total_lines }}", str(total_lines))
        html_content = html_content.replace("{{ code_count }}", str(code_count))
        html_content = html_content.replace("{{ total_files }}", str(total_files))
        html_content = html_content.replace("{{ tree_html }}", tree_html)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        return Path(output_path).resolve()

    def _render_node(self, graph, node_id, visited):
        """Recursively render a graph node to HTML."""
        if node_id in visited:
            return ""
        visited.add(node_id)
        
        node_data = graph.nodes[node_id]
        children = list(graph.successors(node_id))
        
        node_type = node_data.get("type")
        name = node_data.get("name")
        docstring = node_data.get("docstring")
        source = node_data.get("source")

        # Prepare metadata and tags
        meta_html = ""
        if node_type == "file":
            meta_html = f'<span class="file-meta">{node_data.get("line_count")} lines</span>'
        
        type_tag = ""
        if node_type in ["class", "function", "variable"]:
            type_tag = f'<span class="type-tag type-{node_type}">{node_type}</span>'
        elif node_type == "file":
            type_tag = f'<span class="type-tag type-{node_data.get("file_type")}">{node_data.get("file_type")}</span>'

        # Special formatting for functions
        display_name = name
        if node_type == "function":
            args_list = []
            for arg in node_data.get("args", []):
                indicator = "●" if arg.get("explicit") else "○"
                arg_text = arg["name"]
                if arg["type"]:
                    arg_text += f": {arg['type']}"
                args_list.append(f'<span class="arg" title="{"Explicit Type" if arg.get("explicit") else "Inferred/Untyped"}">{indicator} {arg_text}</span>')
            
            ret = node_data.get("returns", {})
            ret_indicator = "●" if ret.get("explicit") else "○"
            display_name = f'{node_data.get("short_name", name)}({", ".join(args_list)}) <span class="return-type" title="{"Explicit Return" if ret.get("explicit") else "Heuristic/None"}">→ {ret_indicator} {ret.get("type", "None")}</span>'

        # Content for expandable sections (source and docstring)
        extra_content = ""
        if docstring:
            extra_content += f'<div class="docstring"><strong>Docs:</strong><br>{html.escape(docstring).replace("\\n", "<br>")}</div>'
        if source:
            extra_content += f'<div class="source-code"><pre><code>{html.escape(source)}</code></pre></div>'

        if children or source or docstring:
            icons = {"directory": "📁", "file": "📄", "class": "📦", "function": "ƒ", "variable": "v"}
            icon = icons.get(node_type, "•")
            
            summary_class = "dir-summary" if node_type == "directory" else "file-summary"
            node_class = "dir-node" if node_type == "directory" else "file-node expandable"
            if node_type in ["class", "function", "variable"]:
                node_class = f"comp-node expandable {node_type}-node"
                summary_class = "comp-summary"
            
            children.sort(key=lambda x: (graph.nodes[x].get("type") != "directory", 
                                       graph.nodes[x].get("type") != "file",
                                       graph.nodes[x].get("name")))
            
            children_html = "".join(self._render_node(graph, child, visited) for child in children)
            
            if node_type == "directory":
                header_content = f'<span class="icon">{icon}</span> {display_name}'
            else:
                header_content = f'<span class="icon">{icon}</span> <span class="file-name">{display_name}</span> {type_tag} {meta_html}'

            return f"""
            <details class="{node_class}">
                <summary class="{summary_class}">
                    {header_content}
                </summary>
                <div class="dir-content">
                    {extra_content}
                    {children_html}
                </div>
            </details>
            """
        else:
            icons = {"file": "📄", "class": "📦", "function": "ƒ", "variable": "v"}
            icon = icons.get(node_type, "•")
            
            return f"""
            <div class="file-node">
                <span class="icon">{icon}</span>
                <span class="file-name">{display_name}</span>
                {type_tag}
                {meta_html}
            </div>
            """

    def _get_stats(self, graph):
        total_lines = sum(data.get("line_count", 0) for _, data in graph.nodes(data=True))
        code_count = sum(1 for _, data in graph.nodes(data=True) if data.get("file_type") == "code")
        total_files = sum(1 for _, data in graph.nodes(data=True) if data.get("type") == "file")
        return total_lines, code_count, total_files
