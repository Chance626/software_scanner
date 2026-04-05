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
        results = scanner.scan()
        self.assertTrue(len(results) > 0)
        
        # Check if we find cli.py
        cli_found = any(r["name"] == "cli.py" for r in results)
        self.assertTrue(cli_found)

if __name__ == '__main__':
    unittest.main()
