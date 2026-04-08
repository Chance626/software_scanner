import unittest
from pathlib import Path
from scanner.core import Scanner

class TestScanner(unittest.TestCase):
    def test_guess_type(self):
        scanner = Scanner(".")
        self.assertEqual(scanner._guess_type(".py"), "code")
        self.assertEqual(scanner._guess_type(".json"), "config")
        self.assertEqual(scanner._guess_type(".md"), "doc")
        self.assertEqual(scanner._guess_type(".unknown"), "other")

    def test_scan_self(self):
        # Scan the current directory
        scanner = Scanner(".")
        graph, root = scanner.scan()
        
        # Check if we find cli.py in the graph nodes
        cli_found = any(data.get("name") == "cli.py" for _, data in graph.nodes(data=True))
        self.assertTrue(cli_found)

if __name__ == '__main__':
    unittest.main()
