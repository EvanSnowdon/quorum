"""Report export: render the deliverable to formats beyond Markdown.

The CLI writes the engagement's Markdown report itself; when the user asks for
another format it hands the rendered Markdown to :func:`export_report`, which
writes the converted file and returns its path. Markdown stays the canonical
artifact, so this module only handles downstream conversions and never has to
reproduce the report skeleton.

HTML conversion uses a small self-contained Markdown subset covering exactly what
:mod:`.report` emits — headings, paragraphs, unordered and ordered lists, simple
tables, blockquotes, fenced code, inline code, bold, and links — so the export
path adds no third-party dependency. A genuine Markdown engine can be swapped in
later without changing this signature.

JSON export wraps the report in a structured envelope (the report text plus
fields derived from it — title, section headings, source URLs, and label
counts), so a downstream system can consume the deliverable without re-parsing
Markdown. Binary office formats (``docx``, ``pptx``, ``xlsx``, ``pdf``) are named
but not implemented here; requesting one raises :class:`UnsupportedFormatError`
so the CLI falls back to the Markdown deliverable deliberately rather than
shipping an empty file.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

SUPPORTED_FORMATS = ("html", "json")

# Office and print formats that callers may request but the pure-Python output
# layer does not render. They are recognized (so the error names them as known
# but unimplemented) and rejected, leaving the Markdown file as the deliverable.
KNOWN_UNIMPLEMENTED_FORMATS = ("docx", "pptx", "xlsx", "pdf")

_INLINE_CODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
_ORDERED_ITEM = re.compile(r"^(\d+)[.)]\s+(.*)$")


class UnsupportedFormatError(ValueError):
    """Raised when an export format is not handled by this module."""


def export_report(report_md: str, fmt: str = "markdown", path: str = "report.md") -> str:
    """Convert a rendered report to ``fmt`` and write it next to ``path``.

    ``path`` is the Markdown file the orchestrator already wrote. The converted
    file is written with the format's extension substituted (``report.md`` ->
    ``report.html``, ``report.json``) and its path is returned. ``markdown`` is
    accepted as a no-op that returns ``path`` unchanged.

    Supported formats: ``markdown`` (no-op), ``html``, ``json``. The binary
    office formats in :data:`KNOWN_UNIMPLEMENTED_FORMATS` and any other value
    raise :class:`UnsupportedFormatError` so the caller can fall back to the
    Markdown deliverable deliberately rather than emit an empty file.
    """
    fmt_normalized = fmt.strip().lower()
    if fmt_normalized == "markdown":
        return path
    if fmt_normalized == "html":
        target = Path(path).with_suffix(".html")
        target.write_text(markdown_to_html(report_md), encoding="utf-8")
        return str(target)
    if fmt_normalized == "json":
        target = Path(path).with_suffix(".json")
        target.write_text(report_to_json(report_md), encoding="utf-8")
        return str(target)
    if fmt_normalized in KNOWN_UNIMPLEMENTED_FORMATS:
        raise UnsupportedFormatError(
            f"export format '{fmt}' is recognized but not implemented in the "
            f"pure-Python output layer; supported: markdown, {', '.join(SUPPORTED_FORMATS)}"
        )
    raise UnsupportedFormatError(
        f"unsupported export format '{fmt}'; supported: markdown, {', '.join(SUPPORTED_FORMATS)}"
    )


def report_to_json(report_md: str) -> str:
    """Wrap the report in a structured JSON envelope and return it as text.

    The envelope is ``{"report": <markdown>, ...generated fields}`` where the
    generated fields are derived from the Markdown so a consumer gets structure
    without re-parsing: the document ``title`` (first level-one heading), the
    ordered ``sections`` (all level-two headings), the unique ``source_urls``
    cited inline, and ``label_counts`` for the ``[DATA]``/``[INFERENCE]``
    discipline. Pretty-printed for diff-friendly artifacts.
    """
    document = {"report": report_md, **_generated_fields(report_md)}
    return json.dumps(document, indent=2, ensure_ascii=False)


def _generated_fields(report_md: str) -> dict[str, object]:
    """Derive the structured fields the JSON envelope adds to the raw report."""
    title = ""
    sections: list[str] = []
    for line in report_md.splitlines():
        stripped = line.strip()
        h1 = re.match(r"^#\s+(.*)$", stripped)
        if h1 and not title:
            title = h1.group(1).strip()
            continue
        h2 = re.match(r"^##\s+(.*)$", stripped)
        if h2:
            sections.append(h2.group(1).strip())
    source_urls = sorted({m.group(2) for m in _LINK.finditer(report_md)})
    label_counts = {
        "DATA": len(re.findall(r"\[DATA\]", report_md)),
        "INFERENCE": len(re.findall(r"\[INFERENCE\]", report_md)),
    }
    return {
        "title": title,
        "sections": sections,
        "source_urls": source_urls,
        "label_counts": label_counts,
    }


def markdown_to_html(markdown: str) -> str:
    """Render the report-Markdown subset to a standalone HTML document."""
    body = "\n".join(_render_blocks(markdown.splitlines()))
    return _HTML_TEMPLATE.format(body=body)


def _render_blocks(lines: list[str]) -> list[str]:
    out: list[str] = []
    list_state: str | None = None  # "ul" | "ol" | None
    in_code = False
    code_buffer: list[str] = []
    table_buffer: list[str] = []

    def close_list() -> None:
        nonlocal list_state
        if list_state is not None:
            out.append(f"</{list_state}>")
            list_state = None

    def flush_table() -> None:
        if table_buffer:
            out.append(_render_table(table_buffer))
            table_buffer.clear()

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code:
                out.append("<pre><code>" + html.escape("\n".join(code_buffer)) + "</code></pre>")
                code_buffer.clear()
                in_code = False
            else:
                close_list()
                flush_table()
                in_code = True
            continue
        if in_code:
            code_buffer.append(raw)
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            close_list()
            table_buffer.append(stripped)
            continue
        flush_table()

        if not stripped:
            close_list()
            continue

        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading:
            close_list()
            level = len(heading.group(1))
            out.append(f"<h{level}>{_inline(heading.group(2))}</h{level}>")
            continue

        if stripped.startswith(("- ", "* ", "+ ")):
            if list_state != "ul":
                close_list()
                out.append("<ul>")
                list_state = "ul"
            out.append(f"<li>{_inline(stripped[2:])}</li>")
            continue

        ordered = _ORDERED_ITEM.match(stripped)
        if ordered:
            if list_state != "ol":
                close_list()
                out.append("<ol>")
                list_state = "ol"
            out.append(f"<li>{_inline(ordered.group(2))}</li>")
            continue

        if stripped.startswith(">"):
            close_list()
            out.append(f"<blockquote>{_inline(stripped[1:].strip())}</blockquote>")
            continue

        close_list()
        out.append(f"<p>{_inline(stripped)}</p>")

    if in_code:
        out.append("<pre><code>" + html.escape("\n".join(code_buffer)) + "</code></pre>")
    flush_table()
    close_list()
    return out


def _render_table(rows: list[str]) -> str:
    parsed = [[cell.strip() for cell in row.strip("|").split("|")] for row in rows]
    # Drop a Markdown alignment separator row (---|---) if present.
    if len(parsed) >= 2 and all(set(cell) <= {"-", ":", " "} and cell for cell in parsed[1]):
        header, data = parsed[0], parsed[2:]
    else:
        header, data = parsed[0], parsed[1:]
    head_html = "".join(f"<th>{_inline(cell)}</th>" for cell in header)
    body_html = "".join(
        "<tr>" + "".join(f"<td>{_inline(cell)}</td>" for cell in row) + "</tr>" for row in data
    )
    return f"<table><thead><tr>{head_html}</tr></thead><tbody>{body_html}</tbody></table>"


def _inline(text: str) -> str:
    escaped = html.escape(text)
    escaped = _LINK.sub(r'<a href="\2">\1</a>', escaped)
    escaped = _BOLD.sub(r"<strong>\1</strong>", escaped)
    escaped = _INLINE_CODE.sub(r"<code>\1</code>", escaped)
    return escaped


_HTML_TEMPLATE = (
    "<!DOCTYPE html>\n"
    '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
    "<title>Quorum engagement report</title>\n</head>\n<body>\n{body}\n</body>\n</html>\n"
)
