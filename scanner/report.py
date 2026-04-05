import datetime
from pathlib import Path

class ReportGenerator:
    def __init__(self, template_path="templates/report.html"):
        self.template_path = Path(template_path)

    def generate(self, results, project_name, output_path="report.html"):
        """Generate the HTML report from the scan results."""
        total_lines = sum(r["line_count"] for r in results)
        code_count = sum(1 for r in results if r["type"] == "code")
        scan_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(self.template_path, "r", encoding="utf-8") as f:
            template_content = f.read()

        # Simple replacement for Jinja2 tags
        # We'll use a more robust way to handle the loop later if needed
        # For now, let's just use string formatting for simple tags
        
        # Replacing simple variables
        html_content = template_content.replace("{{ project_name }}", project_name)
        html_content = html_content.replace("{{ scan_date }}", scan_date)
        html_content = html_content.replace("{{ total_lines }}", str(total_lines))
        html_content = html_content.replace("{{ code_count }}", str(code_count))
        html_content = html_content.replace("{{ results|length }}", str(len(results)))

        # Replacing the loop
        loop_start_tag = "{% for component in results %}"
        loop_end_tag = "{% endfor %}"
        
        start_idx = html_content.find(loop_start_tag)
        end_idx = html_content.find(loop_end_tag) + len(loop_end_tag)
        
        if start_idx != -1 and end_idx != -1:
            loop_template = html_content[start_idx + len(loop_start_tag) : html_content.find(loop_end_tag)]
            rows_html = ""
            for r in results:
                row = loop_template.replace("{{ component.path }}", r["path"])
                row = row.replace("{{ component.type }}", r["type"])
                row = row.replace("{{ component.line_count }}", str(r["line_count"]))
                rows_html += row
            
            html_content = html_content[:start_idx] + rows_html + html_content[end_idx:]

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        return Path(output_path).resolve()
