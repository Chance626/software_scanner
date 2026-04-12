import datetime
import json
from pathlib import Path
import networkx as nx

class ReportGenerator:
    def __init__(self, template_path="templates/report.html"):
        self.template_path = Path(template_path)

    def generate(self, graph, call_graph, root_node, project_name, output_path="report.html"):
        """Generate a JSON data file and a dynamic HTML viewer."""
        output_path = Path(output_path)
        json_path = output_path.with_suffix(".json")
        
        # 1. Prepare Data
        total_lines, code_count, total_files = self._get_stats(graph)
        scan_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Convert Graph to nested tree for JSON
        tree_data = self._graph_to_tree(graph, call_graph, root_node)
        functional_data = self._get_functional_view(graph, call_graph)
        
        def get_groups(node_id):
            """Extract directory and file groups from a node ID."""
            file_path = node_id.split("::")[0]
            path_obj = Path(file_path)
            groups = [{"id": ".", "name": project_name, "type": "directory"}]
            
            # Add directory groups
            current = Path(".")
            for part in path_obj.parts[:-1]:
                current = current / part
                groups.append({"id": str(current), "name": part, "type": "directory"})
            
            # Add file group
            groups.append({"id": file_path, "name": path_obj.name, "type": "file"})
            return groups

        report_data = {
            "project_name": project_name,
            "scan_date": scan_date,
            "stats": {
                "total_lines": total_lines,
                "code_count": code_count,
                "total_files": total_files
            },
            "tree": tree_data,
            "functional": functional_data,
            "call_graph": {
                "nodes": [
                    {
                        "id": n, 
                        "name": n.split("::")[-1], 
                        "type": graph.nodes[n].get("type", "unknown"),
                        "groups": get_groups(n)
                    } for n in call_graph.nodes()
                ],
                "links": [{"source": u, "target": v, "type": d.get("type", "call")} for u, v, d in call_graph.edges(data=True)]
            }
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

    def _graph_to_tree(self, graph, call_graph, node_id, depth=0):
        """Recursively convert networkx graph to a nested dictionary."""
        node_data = dict(graph.nodes[node_id])
        node_data["id"] = node_id  # Ensure ID is present
        children = list(graph.successors(node_id))
        
        # Add call information
        if node_id in call_graph:
            node_data["resolved_calls"] = list(call_graph.successors(node_id))
            node_data["callers"] = list(call_graph.predecessors(node_id))
            node_data["in_call_map"] = True
        else:
            node_data["resolved_calls"] = []
            node_data["callers"] = []
            node_data["in_call_map"] = False

        # Recursively build children
        child_trees = [self._graph_to_tree(graph, call_graph, child, depth + 1) for child in children]

        # Calculate directory stats
        if node_data.get("type") == "directory":
            total_files = 0
            total_lines = 0
            code_count = 0
            
            for child in child_trees:
                if child.get("type") == "file":
                    total_files += 1
                    total_lines += child.get("line_count", 0)
                    if child.get("file_type") == "code":
                        code_count += 1
                elif child.get("type") == "directory":
                    total_files += child.get("total_files", 0)
                    total_lines += child.get("total_lines", 0)
                    code_count += child.get("code_count", 0)
            
            node_data["total_files"] = total_files
            node_data["total_lines"] = total_lines
            node_data["code_count"] = code_count

        # Sort children: directories first, then files, then components
        child_trees.sort(key=lambda x: (
            x.get("type") != "directory",
            x.get("type") != "file",
            x.get("name")
        ))
        
        tree_node = {
            **node_data,
            "depth": depth,
            "children": child_trees
        }
        return tree_node

    def _get_stats(self, graph):
        """Calculate stats by iterating over graph nodes."""
        total_lines = sum(data.get("line_count", 0) for _, data in graph.nodes(data=True))
        code_count = sum(1 for _, data in graph.nodes(data=True) if data.get("file_type") == "code")
        total_files = sum(1 for _, data in graph.nodes(data=True) if data.get("type") == "file")
        return total_lines, code_count, total_files

    def _get_functional_view(self, graph, call_graph):
        """Group components by type (classes, functions) for a functional overview."""
        functional = {
            "classes": [],
            "functions": [],
            "symbol_map": {}
        }
        
        for node_id, data in graph.nodes(data=True):
            if data.get("type") == "class":
                # Create a copy and add the file context
                node_copy = dict(data)
                node_copy["file_path"] = node_id.split("::")[0]
                node_copy["id"] = node_id
                
                # Add call information
                if node_id in call_graph:
                    node_copy["resolved_calls"] = list(call_graph.successors(node_id))
                    node_copy["callers"] = list(call_graph.predecessors(node_id))
                else:
                    node_copy["resolved_calls"] = []
                    node_copy["callers"] = []

                functional["classes"].append(node_copy)
                
                name = data.get("name")
                if name:
                    if name not in functional["symbol_map"]:
                        functional["symbol_map"][name] = []
                    functional["symbol_map"][name].append(node_id)
                    
            elif data.get("type") == "function":
                # Only top-level functions or methods? 
                # Let's include all for now but mark their parent
                node_copy = dict(data)
                parts = node_id.split("::")
                node_copy["file_path"] = parts[0]
                node_copy["id"] = node_id
                
                # Add call information
                if node_id in call_graph:
                    node_copy["resolved_calls"] = list(call_graph.successors(node_id))
                    node_copy["callers"] = list(call_graph.predecessors(node_id))
                else:
                    node_copy["resolved_calls"] = []
                    node_copy["callers"] = []

                if len(parts) > 2:
                    node_copy["parent_component"] = parts[1]
                functional["functions"].append(node_copy)

                name = data.get("name")
                if name:
                    if name not in functional["symbol_map"]:
                        functional["symbol_map"][name] = []
                    functional["symbol_map"][name].append(node_id)
                
        # Sort by name
        functional["classes"].sort(key=lambda x: x["name"])
        functional["functions"].sort(key=lambda x: x["name"])
        
        return functional
