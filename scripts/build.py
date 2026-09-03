#!/usr/bin/env python3
"""Static content builder.

Reads Markdown + YAML front matter files from content/{publications,projects,
courses,talks} and injects rendered HTML into the page templates at the repo
root, writing the result to dist/. Everything else (assets, robots.txt,
sitemap.xml, 404.html) is copied through unchanged.

Usage:
    pip install -r scripts/requirements.txt
    python3 scripts/build.py

Then preview with: python3 -m http.server -d dist
"""
import html
import re
import shutil
import sys
from datetime import date
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("Missing dependency: run `pip install -r scripts/requirements.txt` first.")

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
DIST = ROOT / "dist"

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

TEMPLATE_PAGES = ["index.html", "projects.html", "publications.html", "teaching.html"]
PASSTHROUGH = ["assets", "images", "robots.txt", "sitemap.xml", "404.html"]


def esc(value):
    return html.escape(str(value or ""), quote=True)


def load_items(folder):
    """Load every *.md file in content/<folder> as a front-matter dict + body."""
    items = []
    dirpath = CONTENT / folder
    if not dirpath.exists():
        return items
    for path in sorted(dirpath.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
        if not match:
            raise ValueError(f"{path}: missing '---' front matter block")
        front, body = match.groups()
        data = yaml.safe_load(front) or {}
        data["_body"] = body.strip()
        data["_slug"] = path.stem
        items.append(data)
    return items


def as_date(value):
    if isinstance(value, date):
        return value
    return date.min


def markdown_to_html(text):
    """Minimal markdown: blank-line paragraphs, **bold**, *italic*, [text](url)."""
    if not text:
        return ""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    rendered = []
    for para in paragraphs:
        para = esc(para)
        para = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", para)
        para = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", para)
        para = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>', para)
        rendered.append(f"<p>{para}</p>")
    return "\n".join(rendered)


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------

def render_pub_card(item):
    links = []
    if item.get("pdf"):
        links.append(f'<a href="{esc(item["pdf"])}" target="_blank" rel="noopener noreferrer">PDF</a>')
    if item.get("doi"):
        links.append(f'<a href="{esc(item["doi"])}" target="_blank" rel="noopener noreferrer">DOI</a>')
    elif item.get("paperurl"):
        links.append(f'<a href="{esc(item["paperurl"])}" target="_blank" rel="noopener noreferrer">PAPER</a>')
    if item.get("code"):
        links.append(f'<a href="{esc(item["code"])}" target="_blank" rel="noopener noreferrer">CODE</a>')
    links_html = f'<div class="pub-card__links">{"".join(links)}</div>' if links else ""
    return (
        '<article class="pub-card reveal">\n'
        f'  <h3>{esc(item.get("title"))}</h3>\n'
        f'  <p class="pub-card__meta">{esc(item.get("citation"))}</p>\n'
        f"  {links_html}\n"
        "</article>"
    )


def render_publications(items):
    items = sorted(items, key=lambda d: as_date(d.get("date")), reverse=True)
    out = []
    current_year = None
    for item in items:
        year = as_date(item.get("date")).year
        if year != current_year:
            out.append(f'<h2 class="year-heading">{year}</h2>')
            current_year = year
        out.append(render_pub_card(item))
    return "\n\n".join(out)


def render_project_card(item):
    tags_html = ""
    if item.get("lang"):
        tags_html += f'<span class="tag tag--lang">{esc(item["lang"])}</span>'
    if item.get("license"):
        tags_html += f'<span class="tag tag--license">{esc(item["license"])}</span>'

    features = item.get("features") or []
    features_html = ""
    if features:
        li = "\n".join(f"    <li>{esc(f)}</li>" for f in features)
        features_html = (
            '<p class="detail-label">Features</p>\n'
            f'<ul class="feature-list">\n{li}\n</ul>\n'
        )

    repo_html = ""
    if item.get("repo"):
        repo_html = f'<a href="{esc(item["repo"])}" class="repo-link" target="_blank" rel="noopener noreferrer">VIEW REPOSITORY →</a>'

    body_html = markdown_to_html(item.get("_body", ""))

    return (
        '<details class="project-card reveal">\n'
        "  <summary>\n"
        "    <div>\n"
        f'      <h3 class="project-card__title">{esc(item.get("title"))}</h3>\n'
        f'      <div class="tag-row">{tags_html}</div>\n'
        f'      <p class="project-card__summary">{esc(item.get("summary"))}</p>\n'
        "    </div>\n"
        '    <span class="chevron" aria-hidden="true">▾</span>\n'
        "  </summary>\n"
        '  <div class="project-card__detail">\n'
        f"    {body_html}\n"
        f"    {features_html}"
        f"    {repo_html}\n"
        "  </div>\n"
        "</details>"
    )


def render_projects(items):
    items = sorted(items, key=lambda d: (d.get("order", 999), d.get("title", "")))
    return "\n\n".join(render_project_card(p) for p in items)


def render_featured(items):
    featured = [p for p in items if p.get("featured")]
    featured = sorted(featured, key=lambda d: (d.get("order", 999), d.get("title", "")))[:3]
    out = []
    for i, item in enumerate(featured, start=1):
        kind = esc(item.get("kind", "PROJECT"))
        out.append(
            '<article class="card reveal">\n'
            f'  <p class="card-tag">{i:02d} / {kind}</p>\n'
            f'  <h3>{esc(item.get("title"))}</h3>\n'
            f'  <p>{esc(item.get("summary"))}</p>\n'
            '  <a href="projects.html" class="card-link">LEARN MORE →</a>\n'
            "</article>"
        )
    return "\n\n".join(out)


def render_courses(items):
    items = sorted(items, key=lambda d: (d.get("order", 999), d.get("title", "")))
    out = []
    for item in items:
        out.append(
            '<article class="teaching-card reveal">\n'
            "  <div>\n"
            f'    <h3>{esc(item.get("title"))}</h3>\n'
            f'    <p>{esc(item.get("role"))} · {esc(item.get("institution"))}</p>\n'
            "  </div>\n"
            f'  <p class="teaching-card__term">{esc(item.get("term"))}</p>\n'
            "</article>"
        )
    return "\n\n".join(out)


def render_talks(items):
    items = sorted(items, key=lambda d: as_date(d.get("date")), reverse=True)
    out = []
    for item in items:
        d = as_date(item.get("date"))
        month_year = f"{MONTHS[d.month - 1].upper()} {d.year}" if d != date.min else ""
        event = esc(item.get("event"))
        meta = f"{month_year} · {event}" if month_year and event else (month_year or event)

        link_html = ""
        if item.get("slides"):
            link_html = f'<a href="{esc(item["slides"])}" class="timeline__link" target="_blank" rel="noopener noreferrer">SLIDES →</a>'
        elif item.get("video"):
            link_html = f'<a href="{esc(item["video"])}" class="timeline__link" target="_blank" rel="noopener noreferrer">VIDEO →</a>'

        out.append(
            '<li class="timeline__item reveal">\n'
            f'  <p class="timeline__meta">{meta}</p>\n'
            f'  <h3>{esc(item.get("title"))}</h3>\n'
            f'  <p>{esc(item.get("description"))}</p>\n'
            f"  {link_html}\n"
            "</li>"
        )
    return "\n\n".join(out)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def inject(text, marker, content):
    start, end = f"<!-- BUILD:{marker} -->", f"<!-- /BUILD:{marker} -->"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not pattern.search(text):
        raise ValueError(f"marker {marker!r} not found in template")
    return pattern.sub(f"{start}\n{content}\n{end}", text)


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    publications = load_items("publications")
    projects = load_items("projects")
    courses = load_items("courses")
    talks = load_items("talks")

    injections = {
        "index.html": {"FEATURED_PROJECTS": render_featured(projects)},
        "projects.html": {"PROJECTS": render_projects(projects)},
        "publications.html": {"PUBLICATIONS": render_publications(publications)},
        "teaching.html": {"COURSES": render_courses(courses), "TALKS": render_talks(talks)},
    }

    for name in PASSTHROUGH:
        src = ROOT / name
        if not src.exists():
            continue
        dst = DIST / name
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    for name in TEMPLATE_PAGES:
        text = (ROOT / name).read_text(encoding="utf-8")
        for marker, content in injections[name].items():
            text = inject(text, marker, content)
        (DIST / name).write_text(text, encoding="utf-8")

    print(f"Built {len(publications)} publications, {len(projects)} projects, "
          f"{len(courses)} courses, {len(talks)} talks -> {DIST}")


if __name__ == "__main__":
    main()
