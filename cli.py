import argparse
import os
from scanner.core import Scanner
from scanner.report import ReportGenerator

def scan():
    """Scan a directory and generate a visualization report."""
    parser = argparse.ArgumentParser(description="Scan a directory and generate a visualization report.")
    parser.add_argument('target', help='Target directory to scan.')
    parser.add_argument('--output', '-o', default='report.html', help='Output file path for the report.')
    parser.add_argument('--name', '-n', help='Project name for the report.')
    
    args = parser.parse_args()
    
    if not args.name:
        args.name = os.path.basename(os.path.abspath(args.target))

    print(f"Scanning {args.target}...")
    scanner = Scanner(args.target)
    results = scanner.scan()

    print(f"Generating report to {args.output}...")
    # Get the absolute path to the templates directory relative to this script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(base_dir, "templates", "report.html")

    generator = ReportGenerator(template_path=template_path)
    report_path = generator.generate(results, args.name, args.output)

    print(f"Scan complete! Report saved to: {report_path}")

if __name__ == '__main__':
    scan()
