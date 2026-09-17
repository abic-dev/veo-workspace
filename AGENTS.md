# Shared development

- Start from `master` in an isolated checkout and use a short-lived branch. Submit a PR; only the owner merges.
- Use Node 22.22.2 for Node code and Python 3.11 for source validation. Preserve lockfiles.
- Read `docs/development.md` before executing repository commands.
- Safe checks: `python3 scripts/ci/check_source.py`.
- Never run start, cron, scraper, deploy, live-test, render-worker or backfill commands for CI validation.
- Do not load production credentials, customer data, live DBs, queues, storage or messaging targets.
- Keep unrelated changes out of the PR. Do not remove assertions, disable checks, or claim unrun tests passed.
- Include behavior, verification, cross-repo/API/DB impact and rollback notes in the PR.
- 정적 구문 검증은 기능 테스트를 대체하지 않습니다. 이 레포에는 검증된 자동 기능 테스트가 아직 없습니다.
