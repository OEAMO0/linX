from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
import json
import re


SOURCE_DIR = Path(r"D:\chrome_downloads")
OUTPUT_DIR = Path(__file__).resolve().parent
INDEX_FILE = OUTPUT_DIR / "index.html"
APP_JS_FILE = OUTPUT_DIR / "app.js"
URL_RE = re.compile(r"https?://[^\s|]+")


@dataclass(frozen=True)
class PageSpec:
    slug: str
    requirements: Path
    sources: Path


PAGE_SPECS = [
    PageSpec(
        "part1",
        SOURCE_DIR / "part1-kernel-from-scratch.md",
        SOURCE_DIR / "sources-part1-kernel-from-scratch.md",
    ),
    PageSpec(
        "part2",
        SOURCE_DIR / "part2-kernel-modification.md",
        SOURCE_DIR / "sources-part2-kernel-modification.md",
    ),
    PageSpec(
        "part3",
        SOURCE_DIR / "part3-distro-from-scratch.md",
        SOURCE_DIR / "sources-part3-distro-from-scratch.md",
    ),
    PageSpec(
        "part4",
        SOURCE_DIR / "part4-derivative-distro.md",
        SOURCE_DIR / "sources-part4-derivative-distro.md",
    ),
]


def read_markdown(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing source file: {path}")
    return path.read_text(encoding="utf-8").strip()


def render_inline(text: str) -> str:
    parts: list[str] = []
    start = 0

    for match in URL_RE.finditer(text):
        parts.append(escape(text[start:match.start()]))
        url = match.group(0)
        safe_url = escape(url, quote=True)
        parts.append(
            f'<a href="{safe_url}" target="_blank" rel="noreferrer">{safe_url}</a>'
        )
        start = match.end()

    parts.append(escape(text[start:]))
    return "".join(parts)


def split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def render_table(lines: list[str]) -> str:
    header = split_table_row(lines[0])
    rows = [split_table_row(line) for line in lines[2:]]
    thead = "".join(f"<th>{render_inline(cell)}</th>" for cell in header)
    body = []

    for row in rows:
        cells = "".join(f"<td>{render_inline(cell)}</td>" for cell in row)
        body.append(f"<tr>{cells}</tr>")

    return (
        '<div class="table-wrap">'
        f"<table><thead><tr>{thead}</tr></thead><tbody>{''.join(body)}</tbody></table>"
        "</div>"
    )


def extract_titles(markdown_text: str) -> tuple[str, str]:
    headings = [line[2:].strip() for line in markdown_text.splitlines() if line.startswith("# ")]

    if not headings:
        return "", ""
    if len(headings) == 1:
        return headings[0], headings[0]
    return headings[0], headings[1]


def render_markdown(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    blocks: list[str] = []
    heading_count = 0
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if not line:
            i += 1
            continue

        if line == "---":
            blocks.append('<div class="divider" aria-hidden="true"></div>')
            i += 1
            continue

        if line.startswith("### "):
            blocks.append(f"<h3>{render_inline(line[4:])}</h3>")
            i += 1
            continue

        if line.startswith("# "):
            heading_count += 1
            text = render_inline(line[2:])

            if heading_count == 1:
                blocks.append(f'<p class="doc-kicker">{text}</p>')
            else:
                blocks.append(f'<h1 class="doc-title">{text}</h1>')

            i += 1
            continue

        if line.startswith("|"):
            table_lines: list[str] = []

            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1

            blocks.append(render_table(table_lines))
            continue

        blocks.append(f"<p>{render_inline(line)}</p>")
        i += 1

    return "\n".join(blocks)


def build_page_data() -> list[dict[str, str]]:
    pages = []

    for spec in PAGE_SPECS:
        requirements_text = read_markdown(spec.requirements)
        sources_text = read_markdown(spec.sources)
        kicker, title = extract_titles(requirements_text)

        pages.append(
            {
                "slug": spec.slug,
                "kicker": kicker,
                "title": title,
                "requirementsFile": spec.requirements.name,
                "requirementsHtml": render_markdown(requirements_text),
                "sourcesFile": spec.sources.name,
                "sourcesHtml": render_markdown(sources_text),
            }
        )

    return pages


def render_index() -> str:
    return """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Linux Dev</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <header class="site-header">
    <div class="header-inner">
      <nav id="page-nav" class="page-nav" aria-label="Pages"></nav>
    </div>
  </header>
  <main id="app" class="app"></main>
  <script src="app.js"></script>
</body>
</html>
"""


def render_app_js(pages: list[dict[str, str]]) -> str:
    pages_json = json.dumps(pages, ensure_ascii=False)

    return f"""const SITE_PAGES = {pages_json};

const navElement = document.getElementById("page-nav");
const appElement = document.getElementById("app");

function getPageBySlug(slug) {{
  return SITE_PAGES.find((page) => page.slug === slug) || SITE_PAGES[0];
}}

function getCurrentSlug() {{
  const value = window.location.hash.replace(/^#/, "").trim();
  return value || SITE_PAGES[0].slug;
}}

function renderNav(activeSlug) {{
  navElement.innerHTML = SITE_PAGES.map((page) => {{
    const activeClass = page.slug === activeSlug ? " active" : "";
    return `
      <a class="page-link${{activeClass}}" href="#${{page.slug}}">
        <span class="nav-kicker">${{page.kicker}}</span>
        <span class="nav-title">${{page.title}}</span>
      </a>
    `;
  }}).join("");
}}

function renderPage(page) {{
  document.title = page.title || "Linux Dev";
  appElement.innerHTML = `
    <section class="page-view">
      <article class="doc-page">
        <p class="file-name">${{page.requirementsFile}}</p>
        ${{page.requirementsHtml}}
      </article>
      <article class="doc-page">
        <p class="file-name">${{page.sourcesFile}}</p>
        ${{page.sourcesHtml}}
      </article>
    </section>
  `;
}}

function renderRoute() {{
  const page = getPageBySlug(getCurrentSlug());
  renderNav(page.slug);
  renderPage(page);

  if (window.location.hash.replace(/^#/, "").trim() !== page.slug) {{
    window.location.hash = page.slug;
  }}
}}

window.addEventListener("hashchange", renderRoute);
renderRoute();
"""


def remove_old_html_pages() -> None:
    for pattern in ("part*.html", "sources-part*.html"):
        for path in OUTPUT_DIR.glob(pattern):
            path.unlink()


def main() -> None:
    remove_old_html_pages()
    pages = build_page_data()
    INDEX_FILE.write_text(render_index(), encoding="utf-8")
    APP_JS_FILE.write_text(render_app_js(pages), encoding="utf-8")


if __name__ == "__main__":
    main()
