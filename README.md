# tmd

[![CI](https://github.com/typemnm/tmd/actions/workflows/ci.yml/badge.svg)](https://github.com/typemnm/tmd/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/tmd-cli.svg)](https://pypi.org/project/tmd-cli/)
[![Python](https://img.shields.io/pypi/pyversions/tmd-cli.svg)](https://pypi.org/project/tmd-cli/)

`tmd`는 키보드 중심의 터미널 마크다운 편집기입니다. Textual 기반 TUI에서 파일 탐색, 최근 파일, 마크다운 문법 강조, 문서 검색, 수동 저장과 2초 지연 자동 저장을 제공합니다.

> 현재 버전은 마크다운 원문을 스타일링하는 구문 강조 편집기입니다. 마크다운 기호를 숨기는 완전한 WYSIWYG 렌더러는 아직 제공하지 않습니다.

`Ctrl+P`를 누르면 현재 파일을 로컬 웹 브라우저 탭에 읽기 전용으로 렌더링해서 보여주고, 타이핑하는 동안 실시간으로 갱신됩니다. 서버는 `127.0.0.1`에만 바인딩됩니다.

## 설치

Python 3.11 이상이 필요합니다. CLI 도구를 독립된 환경에 설치하는 `pipx` 사용을 권장합니다.

```bash
pipx install tmd-cli
tmd --version
```

GitHub 릴리스에서 직접 설치하려면 다음 명령을 사용합니다.

```bash
pipx install git+https://github.com/typemnm/tmd.git@v0.1.0
```

> **주의:** `pip install tmd`는 이 프로젝트가 아닌 별개의 PyPI 패키지를 설치합니다. 이 프로젝트의 배포 이름은 `tmd-cli`이고 실행 명령은 `tmd`입니다.

소스 개발 설치:

```bash
git clone https://github.com/typemnm/tmd.git
cd tmd
python -m pip install -e '.[dev]'
```

## 사용법

```bash
tmd                 # 현재 디렉터리를 탐색기 루트로 사용
tmd note.md         # 파일을 열고 부모 디렉터리를 탐색
tmd ~/Documents     # 지정 디렉터리를 탐색
tmd --version
```

## 주요 단축키

| 키 | 동작 |
|---|---|
| `Ctrl+S` | 저장, 새 문서는 Save As 표시 |
| `Ctrl+Shift+S` | 다른 이름으로 저장 |
| `Ctrl+O` | 파일 열기 |
| `Ctrl+F` | 문서 검색 |
| `Ctrl+N` | 새 문서 |
| `Ctrl+Q` | 안전하게 저장 후 종료 |
| `Alt+B` / `Alt+I` | 선택 영역 굵게 / 기울임 |
| `Ctrl+\` | 사이드바 토글 |
| `Ctrl+P` | 웹 브라우저 미리보기 켜기/끄기 |
| `F1` | 도움말 |

기존 파일은 마지막 입력 2초 후 자동 저장됩니다. 파일 전환이나 종료 전에 대기 중인 변경 사항은 즉시 저장됩니다. 제목 없는 문서는 저장·버리기·취소 중 하나를 선택할 수 있습니다.

파일 열기(`Ctrl+O`)와 다른 이름으로 저장(`Ctrl+Shift+S`) 대화상자는 경로를 입력하는 동안 첫 번째로 일치하는 파일/디렉터리를 회색 인라인 텍스트로 제안합니다. → (오른쪽 화살표)를 누르면 제안을 그대로 받아들이고 이어서 하위 경로를 입력할 수 있습니다 — Tab은 포커스 이동에 쓰이므로 제안을 받아들이지 않습니다.

## 개발 및 테스트

```bash
python -m pip install -e '.[dev]'
ruff check tmd_cli tests
pytest -q
python -m build
python -m twine check dist/*
```

기여 방법은 [CONTRIBUTING.md](CONTRIBUTING.md), 변경 내역은 [CHANGELOG.md](CHANGELOG.md)를 참고하세요.

## 라이선스

[MIT License](LICENSE)
