"""Capture genuine browser screenshots of the actual source files for peer grading.

Screenshots are rendered from checked-out files without modifying their source code.
This viewer preserves original code text, highlights syntax, and shows file paths.
"""
from html import escape
from pathlib import Path

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import HtmlDjangoLexer, PythonLexer
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "screenshots"
OUT.mkdir(exist_ok=True)

SOURCES = [
    ("01-models", "onlinecourse/models.py", "class Question(models.Model):", "Models: Question, Choice, Submission"),
    ("02-admin-file", "onlinecourse/admin.py", None, "Django Admin configuration"),
    ("04-course-details", "onlinecourse/templates/onlinecourse/course_details_bootstrap.html", None, "Course details / Bootstrap template"),
    ("05-views", "onlinecourse/views.py", "@login_required\n@require_POST\n@transaction.atomic\ndef submit(", "Exam submission and result views"),
    ("06-urls", "onlinecourse/urls.py", None, "Django URL routes"),
]

formatter = HtmlFormatter(style="friendly", linenos="table", nowrap=False)
css = formatter.get_style_defs(".highlight")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=1)
    for filename, relative_path, start_marker, title in SOURCES:
        file_path = ROOT / relative_path
        full_text = file_path.read_text(encoding="utf-8")
        start = full_text.find(start_marker) if start_marker else 0
        if start == -1:
            raise RuntimeError(f"Missing section in {relative_path}: {start_marker!r}")
        lineno = full_text[:start].count("\n") + 1
        source = full_text[start:]
        lexer = HtmlDjangoLexer() if relative_path.endswith(".html") else PythonLexer()
        styled_code = highlight(source, lexer, HtmlFormatter(
            style="friendly", linenos="table", linenostart=lineno,
        ))
        html = """<!doctype html><html><head><meta charset="utf-8"><style>
        *{box-sizing:border-box}body{margin:0;background:#f4f6fa;color:#1e293b;
        font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
        .shell{margin:24px auto;width:calc(100% - 56px);max-width:1520px;
        background:white;border:1px solid #dce3ec;border-radius:14px;
        box-shadow:0 12px 40px #182b4d13;overflow:hidden}
        .top{padding:21px 28px 19px;background:#fff;border-bottom:1px solid #e4e9f0}
        .eyebrow{font-size:12px;color:#5070ad;letter-spacing:1.9px;font-weight:800;
        text-transform:uppercase;margin-bottom:8px}
        h1{font-size:26px;letter-spacing:-.5px;margin:0 0 12px}
        .path{font:14px Consolas,'DejaVu Sans Mono',monospace;color:#607187;
        padding:9px 12px;background:#f4f7fc;border-radius:7px;display:inline-block}
        .tab{padding:13px 28px;background:#eef2f8;color:#344766;
        border-bottom:1px solid #dce3ec;font-size:13px;font-weight:700}
        .code{padding:15px 8px 20px 14px;overflow:hidden}
        .highlight{background:white}
        .highlighttable{width:100%;border-spacing:0;border-collapse:collapse}
        .highlighttable td{vertical-align:top}
        .linenos{min-width:61px!important;text-align:right;padding:0 14px 0 0!important;
        border-right:1px solid #e9edf2;color:#a3b0c1!important;user-select:none}
        .codecell{width:100%;padding:0 0 0 17px!important}
        .highlight pre{font:15px/1.65 'DejaVu Sans Mono',Consolas,monospace;
        margin:0;white-space:pre-wrap;overflow-wrap:anywhere;tab-size:4}
        .codecell .highlight pre{color:#263548}
        """ + css + """</style></head><body><div class="shell">
        <header class="top"><div class="eyebrow">Online Course / Source file</div>
        <h1>""" + escape(title) + """</h1>
        <div class="path">""" + escape(relative_path) + """</div></header>
        <div class="tab">""" + escape(relative_path.rsplit("/",1)[-1]) + """</div>
        <div class="code">""" + styled_code + """</div></div></body></html>"""
        page.set_content(html, wait_until="load")
        page.screenshot(path=str(OUT / (filename + ".png")), full_page=True)
        print(f"Captured {filename}.png from {relative_path} (starting at line {lineno})")
    browser.close()
