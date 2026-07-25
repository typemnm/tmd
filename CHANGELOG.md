# Changelog

이 프로젝트는 [Semantic Versioning](https://semver.org/)을 따릅니다.

## [Unreleased]

### Added

- 파일 열기/다른 이름으로 저장 다이얼로그에 경로 인라인 자동완성 추가

### Changed

- 굵게/기울임 단축키를 `Ctrl+B`/`Ctrl+I`에서 `Alt+G`/`Alt+I`로 변경 — `Ctrl+I`는 Kitty 키보드 프로토콜을 지원하지 않는 터미널(대다수)에서 Tab과 동일한 바이트이고, `Ctrl+B`는 tmux 기본 prefix 키와 겹쳐 두 경우 모두 tmd에 도달하지 못할 수 있었다. 처음 시도한 `Alt+B`는 Kitty 프로토콜이 없는 터미널에서 Textual의 레거시 ANSI 매핑에 의해 `ctrl+left`로 가로채지는 것이 추가로 발견되어 `Alt+G`로 확정했다

## [0.2.0] - 2026-07-25

### Added

- `Ctrl+P` 웹 브라우저 미리보기 — 현재 파일을 노션 스타일로 렌더링하고 타이핑에 맞춰 실시간 갱신 (localhost 전용, 읽기 전용)

### Security

- 미리보기 렌더링에서 원본 HTML 통과를 비활성화하여 파일 내 스크립트 실행(XSS) 방지
- 미리보기 서버에 Host 헤더 검증 추가로 DNS 리바인딩 방어

## [0.1.0] - 2026-07-23

### Added

- Textual 기반 터미널 마크다운 편집기
- 최근 파일 및 지연 로딩 파일 탐색기
- 마크다운 구문 강조와 코드 블록 처리
- 문서 검색, Save As, 굵게 및 기울임 단축키
- 2초 지연 자동 저장과 수동 저장
- GitHub Actions CI 및 Trusted Publishing 릴리스 자동화

### Security

- 문서 전환과 종료 시 미저장 변경 보호
- 임시 파일을 통한 원자적 저장
- 장기 PyPI API 토큰이 필요 없는 OIDC 배포

[0.1.0]: https://github.com/typemnm/tmd/releases/tag/v0.1.0
