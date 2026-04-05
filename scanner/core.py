import os
from pathlib import Path

class Scanner:
    def __init__(self, target_dir):
        self.target_dir = Path(target_dir).resolve()

    def scan(self):
        """Recursively scan the target directory and collect component data."""
        results = []
        for root, dirs, files in os.walk(self.target_dir):
            # Ignore .git and other common ignored directories
            if ".git" in dirs:
                dirs.remove(".git")
            if "__pycache__" in dirs:
                dirs.remove("__pycache__")

            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(self.target_dir)
                extension = file_path.suffix.lower()

                # Basic file info
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                        line_count = len(lines)
                except Exception:
                    line_count = 0

                results.append({
                    "name": file,
                    "path": str(relative_path),
                    "extension": extension,
                    "line_count": line_count,
                    "type": self._guess_type(extension)
                })
        return results

    def _guess_type(self, extension):
        """Guess the component type based on the file extension."""
        code_exts = {".py", ".js", ".ts", ".c", ".cpp", ".go", ".rs", ".java", ".sh", ".bash"}
        config_exts = {".json", ".yaml", ".yml", ".toml", ".xml", ".ini", ".env"}
        doc_exts = {".md", ".txt", ".pdf", ".html", ".css"}

        if extension in code_exts:
            return "code"
        if extension in config_exts:
            return "config"
        if extension in doc_exts:
            return "doc"
        return "other"
