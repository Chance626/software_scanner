import os
import sys
import json
import datetime
from pathlib import Path
import networkx as nx

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from scanner.core import Scanner

try:
    from sentence_transformers import SentenceTransformer
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

class AICheckpointGenerator:
    def __init__(self, target_dir, model_name='all-MiniLM-L6-v2'):
        self.target_dir = Path(target_dir).resolve()
        self.scanner = Scanner(self.target_dir)
        self.model = SentenceTransformer(model_name) if HAS_TRANSFORMERS else None
        
    def generate_summary(self, node_data):
        """Simple heuristic for generating a summary."""
        name = node_data.get("name", "Unknown")
        type_ = node_data.get("type", "unknown")
        docstring = node_data.get("docstring")
        
        if docstring:
            # Take the first line or first 100 characters of the docstring
            return docstring.split("\n")[0].strip() or docstring[:100].strip()
        
        if type_ == "file":
            return f"Source file: {name}"
        if type_ == "directory":
            return f"Directory: {name}"
        if type_ == "class":
            return f"Class: {name}"
        if type_ == "function":
            return f"Function: {name}"
        
        return f"{type_.capitalize()}: {name}"

    def run(self, output_path="ai_checkpoint.json"):
        print(f"Scanning {self.target_dir}...")
        graph, root_node = self.scanner.scan()
        
        # Add summaries to all nodes first
        for node_id, data in graph.nodes(data=True):
            data["summary"] = self.generate_summary(data)

        checkpoint_data = {
            "project_name": self.target_dir.name,
            "scan_date": datetime.datetime.now().isoformat(),
            "file_tree": self._build_tree(graph, root_node),
            "symbols": self._extract_symbols(graph),
            "dependencies": self._extract_dependencies(graph),
            "embeddings": {}
        }
        
        if HAS_TRANSFORMERS:
            print("Generating embeddings...")
            texts_to_embed = []
            keys = []
            
            # Embed summaries and names
            for node_id, data in graph.nodes(data=True):
                # Combine name and summary for a richer embedding
                text = f"{data.get('name')}: {data.get('summary')}"
                texts_to_embed.append(text)
                keys.append(node_id)
            
            embeddings = self.model.encode(texts_to_embed)
            checkpoint_data["embeddings"] = {k: v.tolist() for k, v in zip(keys, embeddings)}
        else:
            print("Warning: sentence-transformers not available. Embeddings will be empty.")
            # Still generate summaries without embeddings
            for node_id, data in graph.nodes(data=True):
                data["summary"] = self.generate_summary(data)
        
        # Save to file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, indent=2)
            
        print(f"AI Checkpoint saved to {output_path}")

    def _build_tree(self, graph, node_id):
        """Build a tree structure for JSON export."""
        data = dict(graph.nodes[node_id])
        # Summary is added in run()
        tree_node = {
            "id": node_id,
            "name": data.get("name"),
            "type": data.get("type"),
            "summary": data.get("summary", ""),
            "children": [self._build_tree(graph, child) for child in graph.successors(node_id)]
        }
        return tree_node

    def _extract_symbols(self, graph):
        """Extract all functions and classes into a flat list."""
        symbols = []
        for node_id, data in graph.nodes(data=True):
            if data.get("type") in ["class", "function"]:
                symbol = dict(data)
                symbol["id"] = node_id
                symbol["file_path"] = node_id.split("::")[0]
                symbols.append(symbol)
        return symbols

    def _extract_dependencies(self, graph):
        """Build a call graph or dependency map."""
        deps = {
            "imports": {},
            "call_graph": [] # Simple placeholder for now
        }
        for node_id, data in graph.nodes(data=True):
            if data.get("type") == "file" and "imports" in data:
                deps["imports"][node_id] = data["imports"]
        return deps

if __name__ == "__main__":
    generator = AICheckpointGenerator(".")
    generator.run()
