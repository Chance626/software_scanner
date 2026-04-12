import argparse
import os
from scanner.core import Scanner
from scanner.report import ReportGenerator

def main():
    """Scan a directory and generate a visualization report."""
    parser = argparse.ArgumentParser(description="Scan a directory and generate a visualization report.")
    parser.add_argument('target', help='Target directory to scan.')
    parser.add_argument('--output', '-o', default='report.html', help='Output file path for the report.')
    parser.add_argument('--name', '-n', help='Project name for the report.')
    parser.add_argument('--parallel', '-p', type=str, default='1', 
                        help='Number of workers (int) or percentage of cores (float 0-1). Default: 1 (serial).')
    
    args = parser.parse_args()
    
    # Parse parallel argument
    import os
    num_workers = 1
    try:
        if '.' in args.parallel:
            val = float(args.parallel)
            if 0 < val <= 1:
                num_workers = max(1, round(val * os.cpu_count()))
            else:
                num_workers = int(val)
        else:
            num_workers = int(args.parallel)
    except ValueError:
        print(f"Invalid parallel value: {args.parallel}. Defaulting to serial.")
        num_workers = 1

    if not args.name:
        args.name = os.path.basename(os.path.abspath(args.target))

    print(f"Scanning {args.target} (parallelism: {num_workers})...")
    scanner = Scanner(args.target)
    graph, call_graph, root_node = scanner.scan(num_workers=num_workers)

    print(f"Scan complete!")
    print(f"  Discovery:  {scanner.timings['discovery']:.2f}s")
    print(f"  Parsing:    {scanner.timings['parsing']:.2f}s")
    print(f"  Resolution: {scanner.timings['resolution']:.2f}s")
    
    import time
    start_report = time.time()
    print(f"\nGenerating report to {args.output}...")
    
    # Get the absolute path to the templates directory relative to this script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(base_dir, "templates", "report.html")

    generator = ReportGenerator(template_path=template_path)
    report_path, data_path = generator.generate(graph, call_graph, root_node, args.name, args.output)
    
    report_time = time.time() - start_report
    print(f"  Report Gen: {report_time:.2f}s")
    
    print(f"\nFiles ready!")
    print(f"  Report: {report_path}")
    print(f"  Data:   {data_path}")
    print("\nNote: To view the report, you may need to run a local server to avoid CORS issues.")
    print(f"      Example: cd {os.path.dirname(report_path)} && python3 -m http.server")

if __name__ == '__main__':
    main()
