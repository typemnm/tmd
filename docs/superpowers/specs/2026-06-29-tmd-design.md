# tmd — Terminal Markdown Editor: Design Spec

**Date:** 2026-06-29
**Status:** Approved

---

## Overview

`tmd` (Terminal Markdown Editor)는 Ubuntu 환경의 터미널에서 동작하는 WYSIWYG 마크다운 에디터다.
CLI 명령어로 마크다운 파일을 열어 스타일이 적용된 상태로 읽고 편집할 수 있다.

---

## Goals

- `tmd note.md` 한 줄로 파일을 WYSIWYG 상태로 열고 편집
- 마크다운 문법 기호가 아닌 렌더링된 스타일로 내용을 표시
- 파일 탐색기 + 최근 파일 목록으로 빠른 파일 접근
- 자동 저장 + 수동 저장 모두 지원
- Ubuntu 터미널에서 추가 설치 없이 `pip install tmd`로 사용 가능

---

## Tech Stack

- **언어:** Python 3.11+
- **TUI 프레임워크:** Textual
- **마크다운 파서:** markdown-it-py (플러그인: mdit-py-plugins for 체크박스/각주/테이블)
- **구문 강조:** Rich (Textual 내장)
- **패키징:** pyproject.toml (hatchling), `tmd` CLI 명령어 등록

---

## Architecture

```
tmd/
├── tmd/
│   ├── __init__.py
│   ├── app.py          # Textual App 진입점, 레이아웃 조립
│   ├── editor.py       # WYSIWYG 편집 위젯 (TextArea 기반)
│   ├── sidebar.py      # 파일 탐색기 + 최근 파일 패널
│   ├── markdown.py     # 마크다운 파서/렌더러 래퍼
│   ├── history.py      # 최근 파일 목록 (~/.tmd_history JSON)
│   └── keybindings.py  # 단축키 정의
├── pyproject.toml
└── README.md
```

---

## Layout

```
┌─ 사이드바 (30%) ──┬─ 에디터 (70%) ──────────────┐
│ [최근 파일]        │  # 제목 (굵게 렌더링)         │
│ > note.md          │                               │
│   todo.md          │  - [x] 완료된 항목            │
│                    │  - [ ] 미완료 항목             │
│ [파일 탐색기]      │                               │
│ 📁 ~/Documents     │  | 표 | 헤더 |               │
│   📄 note.md       │  | -- | ---- |               │
└────────────────────┴───────────────────────────────┘
 Ctrl+S 저장 | Ctrl+Q 종료 | Tab 사이드바 전환
```

---

## CLI Interface

```bash
tmd              # 홈 화면: 최근 파일 목록 + 파일 탐색기 (현재 디렉토리 기준)
tmd note.md      # 해당 파일 즉시 열기
tmd ~/docs/      # 지정 디렉토리를 탐색기 루트로 열기
```

---

## WYSIWYG Editing

커서가 위치한 줄은 원본 마크다운 문법을 표시하고, 다른 줄은 렌더링된 스타일로 표시한다 (Typora 방식).

Textual의 Syntax Highlighting API를 활용해 마크다운 토큰별 스타일을 적용한다.

예시:
- 커서 있는 줄: `# 제목` (원본)
- 커서 없는 줄: `━━ 제목 ━━` (렌더링)

---

## Supported Markdown Elements

| 요소 | 문법 | 렌더링 |
|------|------|--------|
| 제목 H1-H6 | `# 제목` | 굵게 + 색상 강조 |
| 굵게 | `**텍스트**` | 굵게 |
| 기울임 | `*텍스트*` | 기울임 |
| 취소선 | `~~텍스트~~` | 취소선 |
| 인라인 코드 | `` `code` `` | 배경색 강조 |
| 코드블록 | ` ```lang ``` ` | 구문 강조 (Rich) |
| 순서없는 리스트 | `- 항목` | `• 항목` |
| 순서있는 리스트 | `1. 항목` | `1. 항목` |
| 체크박스 | `- [x]` / `- [ ]` | `✓` / `☐` |
| 테이블 | `\| col \|` | 테두리 있는 표 |
| 인용문 | `> 텍스트` | 세로선 + 색상 |
| 각주 | `[^1]` | 번호 + 하단 표시 |
| 링크 | `[텍스트](url)` | 색상 강조 |
| 수평선 | `---` | `──────────` |

---

## Save Behavior

- **자동 저장:** 마지막 키 입력 후 2초 경과 시 저장 (debounce)
- **수동 저장:** `Ctrl+S`
- **상태 표시:** 상태바에 `● 저장됨` / `○ 미저장` 표시

---

## Recent Files

- 저장 위치: `~/.tmd_history` (JSON)
- 최대 20개 항목
- 항목 구조: `{ "path": "/abs/path/file.md", "last_opened": "ISO8601" }`
- 파일 삭제/이동 시 해당 항목 자동 제거

---

## Keybindings

| 단축키 | 동작 |
|--------|------|
| `Ctrl+S` | 저장 |
| `Ctrl+Q` | 종료 |
| `Tab` | 에디터 ↔ 사이드바 포커스 전환 |
| `Ctrl+B` | 굵게 토글 (선택 영역) |
| `Ctrl+I` | 기울임 토글 |
| `Ctrl+N` | 새 파일 |
| `Ctrl+O` | 파일 열기 다이얼로그 |
| `Ctrl+F` | 파일 내 검색 |
| `Ctrl+\` | 사이드바 토글 |
| `F1` | 단축키 도움말 |

---

## Out of Scope

- 이미지 렌더링 (터미널 환경 한계)
- 플러그인 시스템
- 다중 탭/창
- Git 연동
- Notion 수준의 블록 데이터베이스
