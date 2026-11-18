# backend/tools/report_generator_tool.py
"""
Report Generator Tool (BEAST)
- Accepts a report spec (title, author, sections [{heading, text, tables, images}], metadata)
- Can generate HTML, PDF (if dependencies installed), and PPTX slides.
- Returns paths to generated files.
"""

import os
import tempfile
import json
from pathlib import Path
from typing import Dict, Any, List

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape, Template
    _HAVE_JINJA = True
except Exception:
    _HAVE_JINJA = False

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    _HAVE_PPTX = True
except Exception:
    _HAVE_PPTX = False

try:
    # Try WeasyPrint if available for HTML->PDF (renders CSS)
    from weasyprint import HTML
    _HAVE_WEASY = True
except Exception:
    _HAVE_WEASY = False

# fallback simple HTML template (if jinja2 not available)
_SIMPLE_HTML = """
<html>
<head>
  <meta charset="utf-8">
  <title>{{title}}</title>
  <!-- Mermaid JS for diagrams -->
  <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
  <script>
    mermaid.initialize({ startOnLoad: true, theme: 'neutral' });
    document.addEventListener("DOMContentLoaded", function() {
      // Find all code blocks with language-mermaid and render them
      document.querySelectorAll('pre.mermaid, code.language-mermaid, div.mermaid').forEach(el => {
        el.classList.add('mermaid');
      });
    });
  </script>
</head>
<body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; line-height: 1.6; color: #333; max-width: 900px; mx-auto;">
<h1 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">{{title}}</h1>
<p style="color: #7f8c8d; font-style: italic;"><em>{{author}}</em></p>
{% for s in sections %}
  <h2 style="color: #2980b9; margin-top: 30px;">{{s.heading}}</h2>
  <div style="font-size: 16px;">{{s.text | safe}}</div>
  {% if s.tables %}
    {% for t in s.tables %}
      <h4 style="color: #34495e;">Table: {{t.title}}</h4>
      <pre style="background: #f8f9fa; padding: 15px; border-radius: 5px;">{{t.preview}}</pre>
    {% endfor %}
  {% endif %}
  {% if s.images %}
    {% for img in s.images %}
      <img src="{{img}}" style="max-width:100%; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin: 20px 0;" />
    {% endfor %}
  {% endif %}
{% endfor %}
</body>
</html>
"""

OUT_DIR = os.getenv("REPORTS_DIR", "reports")
Path(OUT_DIR).mkdir(parents=True, exist_ok=True)

def _sanitize_mermaid(text: str) -> str:
    """Sanitize Mermaid diagrams to prevent common syntax errors."""
    import re
    
    def fix_mermaid_block(match):
        content = match.group(1)
        lines = content.strip().split('\n')
        fixed_lines = []
        
        for line in lines:
            # Fix common issues
            line = line.strip()
            
            # Skip empty lines
            if not line:
                fixed_lines.append(line)
                continue
            
            # Fix node labels with special characters (wrap in quotes)
            # Pattern: A[Some (text) here] -> A["Some (text) here"]
            line = re.sub(r'\[([^\]"]*[()&<>][^\]"]*)\]', r'["\1"]', line)
            
            # Fix arrow syntax: --> should be -->
            line = re.sub(r'-+>', '-->', line)
            
            # Ensure sequenceDiagram participants are declared
            # (Can't fully fix this without more context)
            
            fixed_lines.append(line)
        
        return f'<div class="mermaid">\n{chr(10).join(fixed_lines)}\n</div>'
    
    # Find and fix mermaid blocks
    # Match ```mermaid ... ``` blocks
    text = re.sub(r'```mermaid\s*(.*?)```', fix_mermaid_block, text, flags=re.DOTALL)
    
    # Match <div class="mermaid">...</div> blocks
    text = re.sub(r'<div class="mermaid">\s*(.*?)</div>', fix_mermaid_block, text, flags=re.DOTALL)
    
    return text

def _render_html(spec: Dict[str,Any]) -> str:
    title = spec.get("title", "Aetherix Report")
    author = spec.get("author", "")
    sections = spec.get("sections", [])
    
    # Normalize sections (handle LLM naming variations)
    norm_sections = []
    for s in sections:
        heading = s.get("heading") or s.get("title") or s.get("header") or ""
        text = s.get("text") or s.get("content") or s.get("body") or s.get("description") or ""
        
        # Sanitize Mermaid diagrams to fix common syntax errors
        text = _sanitize_mermaid(text)
        
        norm_sections.append({
            "heading": heading, 
            "text": text,
            "tables": s.get("tables", []),
            "images": s.get("images", [])
        })
    sections = norm_sections

    if _HAVE_JINJA:
        env = Environment(loader=FileSystemLoader("."), autoescape=select_autoescape(["html","xml"]))
        tmpl = env.from_string(_SIMPLE_HTML)
        html = tmpl.render(title=title, author=author, sections=sections)
    else:
        # naive replace
        from string import Template as _T
        t = _T(_SIMPLE_HTML)
        # crude substitution: convert sections to HTML
        secs = []
        for s in sections:
            # Flexible key extraction
            heading = s.get("heading") or s.get("title") or s.get("header") or ""
            text = s.get("text") or s.get("content") or s.get("body") or s.get("description") or ""
            
            secs.append(f"<h2>{heading}</h2><div>{text}</div>")
        
        # fallback: simpler
        html = f"<html><body><h1>{title}</h1><p><em>{author}</em></p>{''.join(secs)}</body></html>"
    return html

def generate_html_report(spec: Dict[str,Any], out_basename: str = None) -> str:
    out_basename = out_basename or spec.get("title","report").replace(" ","_")
    html = _render_html(spec)
    out_path = os.path.join(OUT_DIR, f"{out_basename}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path

def generate_pdf_report(spec: Dict[str,Any], out_basename: str = None) -> str:
    html_path = generate_html_report(spec, out_basename=out_basename)
    out_basename = out_basename or spec.get("title","report").replace(" ","_")
    pdf_path = os.path.join(OUT_DIR, f"{out_basename}.pdf")
    # Try Playwright for PDF (supports JS/Mermaid)
    try:
        from concurrent.futures import ThreadPoolExecutor
        from playwright.sync_api import sync_playwright
        
        def _run_playwright_pdf():
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(f"file:///{os.path.abspath(html_path).replace(os.sep, '/')}")
                page.wait_for_timeout(2000) 
                page.pdf(path=pdf_path, format="A4", print_background=True, margin={"top": "1cm", "right": "1cm", "bottom": "1cm", "left": "1cm"})
                browser.close()
        
        # Run in separate thread to avoid asyncio conflict
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(_run_playwright_pdf).result()
            
        return pdf_path
    
    except Exception as e:
        print(f"Playwright PDF failed: {e}")
        # Fallback to WeasyPrint or just HTML
        if _HAVE_WEASY:
            try:
                HTML(html_path).write_pdf(pdf_path)
                return pdf_path
            except Exception:
                return html_path
        else:
            return html_path

def generate_pptx_report(spec: Dict[str,Any], out_basename: str = None) -> str:
    if not _HAVE_PPTX:
        return generate_html_report(spec, out_basename=out_basename)
    out_basename = out_basename or spec.get("title","report").replace(" ","_")
    prs = Presentation()
    # Title slide
    slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1] if len(slide.placeholders) > 1 else None
    title.text = spec.get("title","Aetherix Report")
    if subtitle:
        subtitle.text = spec.get("author","")
    # Content slides
    for s in spec.get("sections", []):
        sl = prs.slides.add_slide(prs.slide_layouts[1] if len(prs.slide_layouts)>1 else prs.slide_layouts[5])
        sh = sl.shapes.title
        sh.text = s.get("heading","")
        body = sl.shapes.placeholders[1] if len(sl.shapes.placeholders)>1 else None
        if body:
            tf = body.text_frame
            # add text paragraphs safely
            for line in (s.get("text","") or "").split("\n")[:20]:
                p = tf.add_paragraph()
                p.text = line[:1000]
                p.level = 0
    out_path = os.path.join(OUT_DIR, f"{out_basename}.pptx")
    prs.save(out_path)
    return out_path

# Public wrapper
def generate_report(spec: Dict[str,Any], formats: List[str] = None, out_basename: str = None) -> Dict[str,str]:
    """
    spec: {title, author, sections: [{heading, text, tables:[{title, preview}], images:[path,...]}]}
    formats: list of 'html','pdf','pptx'
    returns dict of format->path
    """
    formats = formats or ["html"]
    results = {}
    if "html" in formats:
        results["html"] = generate_html_report(spec, out_basename)
    if "pdf" in formats:
        results["pdf"] = generate_pdf_report(spec, out_basename)
    if "pptx" in formats:
        results["pptx"] = generate_pptx_report(spec, out_basename)
    return results

# Example quick-run API for agents
def create_and_save_report(title: str, sections: List[Dict[str,str]], formats: List[str]=["html","pdf"]) -> Dict[str,str]:
    spec = {"title": title, "author": "", "sections": sections}
    return generate_report(spec, formats=formats, out_basename=title.replace(" ","_"))
