import datetime
import json
from pathlib import Path
import networkx as nx

class ReportGenerator:
    def __init__(self, template_path="templates/report.html"):
        self.template_path = Path(template_path)

    def generate(self, graph, root_node, project_name, output_path="report.html"):
        """Generate a JSON data file and a dynamic HTML viewer."""
        output_path = Path(output_path)
        json_path = output_path.with_suffix(".json")
        
        # 1. Prepare Data
        total_lines, code_count, total_files = self._get_stats(graph)
        scan_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Convert Graph to nested tree for JSON
        tree_data = self._graph_to_tree(graph, root_node)
        
        report_data = {
            "project_name": project_name,
            "scan_date": scan_date,
            "stats": {
                "total_lines": total_lines,
                "code_count": code_count,
                "total_files": total_files
            },
            "tree": tree_data
        }

        # 2. Save JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

        # 3. Save HTML Viewer
        with open(self.template_path, "r", encoding="utf-8") as f:
            template_content = f.read()

        # We only need to replace the project name in the template for the title
        # and tell the HTML which JSON file to load
        html_content = template_content.replace("{{ project_name }}", project_name)
        html_content = html_content.replace("{{ json_filename }}", json_path.name)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        return output_path.resolve(), json_path.resolve()

    def _graph_to_tree(self, graph, node_id, depth=0):
        """Recursively convert networkx graph to a nested dictionary."""
        node_data = dict(graph.nodes[node_id])
        children = list(graph.successors(node_id))
        
        # Sort children: directories first, then files, then components
        children.sort(key=lambda x: (
            graph.nodes[x].get("type") != "directory",
            graph.nodes[x].get("type") != "file",
            graph.nodes[x].get("name")
        ))
        
        tree_node = {
            **node_data,
            "depth": depth,
            "children": [self._graph_to_tree(graph, child, depth + 1) for child in children]
        }
        return tree_node

    def _get_stats(self, graph):
        """Calculate stats by iterating over graph nodes."""
        total_lines = sum(data.get("line_count", 0) for _, data in graph.nodes(data=True))
        code_count = sum(1 for _, data in graph.nodes(data=True) if data.get("file_type") == "code")
        total_files = sum(1 for _, data in graph.nodes(data=True) if data.get("type") == "file")
        return total_lines, code_count, total_files
