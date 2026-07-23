# Contributing

## 개발 환경

```bash
git clone https://github.com/typemnm/tmd.git
cd tmd
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

## 변경 전 확인

```bash
ruff check tmd_cli tests
pytest -q
python -m build
python -m twine check dist/*
```

기능 변경에는 회귀 테스트를 포함해 주세요. 버그 보고에는 OS, Python 버전, `tmd --version`, 재현 절차를 기재해 주세요.
