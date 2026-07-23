import re
from typing import TypeAlias

LineStyle: TypeAlias = tuple[int, int, str]  # (start_col, end_col, rich_style_str)

HEADING_STYLES: dict[int, str] = {
    1: "bold bright_cyan",
    2: "bold cyan",
    3: "bold bright_blue",
    4: "bold blue",
    5: "bold bright_magenta",
    6: "bold magenta",
}

BLOCK_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # H1-H6: 줄 전체를 스타일링
    (re.compile(r"^(#{1}) .+"), HEADING_STYLES[1]),
    (re.compile(r"^(#{2}) .+"), HEADING_STYLES[2]),
    (re.compile(r"^(#{3}) .+"), HEADING_STYLES[3]),
    (re.compile(r"^(#{4}) .+"), HEADING_STYLES[4]),
    (re.compile(r"^(#{5}) .+"), HEADING_STYLES[5]),
    (re.compile(r"^(#{6}) .+"), HEADING_STYLES[6]),
    # 인용문
    (re.compile(r"^> .+"), "italic dim bright_green"),
    # 체크박스 (순서상 unordered list 보다 먼저 매칭되어야 함)
    (re.compile(r"^\s*[-*] \[[xX]\]"), "bold bright_green"),
    (re.compile(r"^\s*[-*] \[ \]"), "dim"),
    # 순서 없는 목록: - 또는 * 로 시작 (체크박스 제외)
    (re.compile(r"^[-*] (?!\[)"), "bright_white"),
    # 순서 있는 목록: 숫자. 로 시작
    (re.compile(r"^\d+\. "), "bright_white"),
    # 표: | 로 시작하고 | 로 끝남
    (re.compile(r"^\|.+\|"), "bright_yellow"),
    # 수평선
    (re.compile(r"^[-*_]{3,}$"), "dim"),
]

INLINE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # 굵게: **text** 또는 __text__
    (re.compile(r"\*\*.+?\*\*|__.+?__"), "bold"),
    # 기울임: *text* 또는 _text_ (굵게 패턴 제외 후 적용)
    (re.compile(r"(?<!\*)\*(?!\*).+?(?<!\*)\*(?!\*)|(?<!_)_(?!_).+?(?<!_)_(?!_)"), "italic"),
    # 취소선: ~~text~~
    (re.compile(r"~~.+?~~"), "strike"),
    # 인라인 코드: `code`
    (re.compile(r"`[^`]+`"), "bold on grey11"),
    # 각주: [^ref] (링크 패턴보다 먼저 매칭)
    (re.compile(r"\[\^[^\]]+\]"), "dim"),
    # 링크: [text](url)
    (re.compile(r"\[.+?\]\(.+?\)"), "bright_blue underline"),
]

CODE_FENCE_PATTERN = re.compile(r"^\s*(`{3,}|~{3,})")
CODE_STYLE = "bold on grey11"


def annotate_line(line: str) -> list[LineStyle]:
    spans: list[LineStyle] = []

    # 줄 전체 패턴 먼저 적용 (헤딩, 인용문 등)
    for pattern, style in BLOCK_PATTERNS:
        m = pattern.match(line)
        if m:
            spans.append((0, len(line), style))
            # 줄 전체 패턴이 매칭되면 인라인 패턴도 추가로 적용
            break

    # Inline code is a protected region: markdown markers inside it are literal.
    code_pattern, code_style = next(
        item for item in INLINE_PATTERNS if item[1] == CODE_STYLE
    )
    protected = [match.span() for match in code_pattern.finditer(line)]
    spans.extend((start, end, code_style) for start, end in protected)

    # 인라인 패턴 적용
    for pattern, style in INLINE_PATTERNS:
        if pattern is code_pattern:
            continue
        for m in pattern.finditer(line):
            if any(m.start() < end and start < m.end() for start, end in protected):
                continue
            spans.append((m.start(), m.end(), style))

    return spans


def annotate_document(text: str) -> list[list[LineStyle]]:
    """Annotate a document while retaining fenced-code-block state."""
    result: list[list[LineStyle]] = []
    fence_marker: str | None = None
    for line in text.split("\n"):
        fence = CODE_FENCE_PATTERN.match(line)
        if fence is not None:
            marker = fence.group(1)
            if fence_marker is None:
                fence_marker = marker[0]
            elif marker[0] == fence_marker:
                fence_marker = None
            result.append([(0, len(line), CODE_STYLE)] if line else [])
        elif fence_marker is not None:
            result.append([(0, len(line), CODE_STYLE)] if line else [])
        else:
            result.append(annotate_line(line))
    return result


# Backward-compatible aliases for integrations built against the MVP internals.
_PATTERNS = BLOCK_PATTERNS
_INLINE_PATTERNS = INLINE_PATTERNS
