from tmd.markdown import annotate_line


def test_h1_entire_line_styled():
    spans = annotate_line("# Hello")
    styles = [s for _, _, s in spans]
    assert any("bold" in s for s in styles)


def test_h2_styled():
    spans = annotate_line("## World")
    assert len(spans) > 0


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


def test_inline_code():
    spans = annotate_line("use `code` here")
    styled = [(s, e, st) for s, e, st in spans if "on grey" in st or "reverse" in st or "dim" in st]
    # 인라인 코드는 배경 색상 스타일 포함
    assert len(styled) > 0


def test_checkbox_checked():
    spans = annotate_line("- [x] done")
    assert len(spans) > 0


def test_checkbox_unchecked():
    spans = annotate_line("- [ ] todo")
    assert len(spans) > 0


def test_blockquote():
    spans = annotate_line("> quote text")
    assert len(spans) > 0


def test_plain_text_no_spans():
    spans = annotate_line("plain text no markdown")
    assert spans == []
