from tmd.markdown import annotate_line


# ── Headings ──────────────────────────────────────────────────────────────────

def test_h1_entire_line_styled():
    spans = annotate_line("# Hello")
    styles = [s for _, _, s in spans]
    assert any("bold" in s for s in styles)


def test_h2_styled():
    spans = annotate_line("## World")
    styles = [s for _, _, s in spans]
    assert any("bold" in s for s in styles)


def test_h3_styled():
    spans = annotate_line("### Section")
    styles = [s for _, _, s in spans]
    assert any("bold" in s for s in styles)


def test_h4_styled():
    spans = annotate_line("#### Sub")
    styles = [s for _, _, s in spans]
    assert any("bold" in s for s in styles)


def test_h5_styled():
    spans = annotate_line("##### Minor")
    styles = [s for _, _, s in spans]
    assert any("bold" in s for s in styles)


def test_h6_styled():
    spans = annotate_line("###### Tiny")
    styles = [s for _, _, s in spans]
    assert any("bold" in s for s in styles)


# ── Inline formatting ─────────────────────────────────────────────────────────

def test_bold_inline():
    spans = annotate_line("some **bold** text")
    styled = [(s, e, st) for s, e, st in spans if "bold" in st]
    assert len(styled) > 0
    # **bold** 포함 범위
    assert any(s <= 5 and e >= 11 for s, e, _ in styled)


def test_italic_inline():
    spans = annotate_line("some *italic* text")
    styled = [(s, e, st) for s, e, st in spans if "italic" in st]
    assert len(styled) > 0


def test_strikethrough_inline():
    spans = annotate_line("some ~~struck~~ text")
    styles = [st for _, _, st in spans]
    assert any("strike" in st for st in styles)


def test_link_inline():
    spans = annotate_line("see [example](https://example.com) here")
    styles = [st for _, _, st in spans]
    assert any("blue" in st for st in styles)


def test_inline_code():
    spans = annotate_line("use `code` here")
    styled = [(s, e, st) for s, e, st in spans if "on grey" in st or "reverse" in st or "dim" in st]
    # 인라인 코드는 배경 색상 스타일 포함
    assert len(styled) > 0


# ── Checkboxes ────────────────────────────────────────────────────────────────

def test_checkbox_checked():
    spans = annotate_line("- [x] done")
    styles = [st for _, _, st in spans]
    assert any("green" in st for st in styles)


def test_checkbox_unchecked():
    spans = annotate_line("- [ ] todo")
    assert len(spans) > 0


def test_checkbox_checked_not_unordered_list():
    """- [x] must match as checkbox, not unordered list."""
    spans = annotate_line("- [x] done")
    styles = [st for _, _, st in spans]
    # Must have a green style (checkbox), not just bright_white (unordered list)
    assert any("green" in st for st in styles)
    # The line-level span must be the checkbox style, not unordered list
    line_spans = [(s, e, st) for s, e, st in spans if s == 0 and e == len("- [x] done")]
    assert all("green" in st for _, _, st in line_spans)


def test_checkbox_unchecked_not_unordered_list():
    """- [ ] must match as checkbox, not unordered list."""
    spans = annotate_line("- [ ] todo")
    # The line-level span must use "dim" (unchecked checkbox style)
    line_spans = [(s, e, st) for s, e, st in spans if s == 0]
    assert any("dim" in st for _, _, st in line_spans)


# ── Block elements ────────────────────────────────────────────────────────────

def test_blockquote():
    spans = annotate_line("> quote text")
    styles = [st for _, _, st in spans]
    assert any("green" in st or "italic" in st for st in styles)


def test_horizontal_rule():
    spans = annotate_line("---")
    assert len(spans) > 0


def test_horizontal_rule_asterisks():
    spans = annotate_line("***")
    assert len(spans) > 0


# ── Lists ─────────────────────────────────────────────────────────────────────

def test_unordered_list_dash():
    spans = annotate_line("- item one")
    styles = [st for _, _, st in spans]
    assert any("bright_white" in st for st in styles)


def test_unordered_list_asterisk():
    spans = annotate_line("* item two")
    styles = [st for _, _, st in spans]
    assert any("bright_white" in st for st in styles)


def test_ordered_list():
    spans = annotate_line("1. first item")
    styles = [st for _, _, st in spans]
    assert any("bright_white" in st for st in styles)


def test_ordered_list_multidigit():
    spans = annotate_line("42. answer")
    styles = [st for _, _, st in spans]
    assert any("bright_white" in st for st in styles)


# ── Table ─────────────────────────────────────────────────────────────────────

def test_table_row():
    spans = annotate_line("| col1 | col2 |")
    styles = [st for _, _, st in spans]
    assert any("bright_yellow" in st for st in styles)


def test_table_separator():
    spans = annotate_line("|---|---|")
    styles = [st for _, _, st in spans]
    assert any("bright_yellow" in st for st in styles)


# ── Footnote ─────────────────────────────────────────────────────────────────

def test_footnote_inline():
    spans = annotate_line("See note[^1] for details.")
    styles = [st for _, _, st in spans]
    assert any("dim" in st for st in styles)


def test_footnote_named():
    spans = annotate_line("Cited[^author2024] here.")
    styles = [st for _, _, st in spans]
    assert any("dim" in st for st in styles)


# ── Plain text ────────────────────────────────────────────────────────────────

def test_plain_text_no_spans():
    spans = annotate_line("plain text no markdown")
    assert spans == []
