# Current Sprint: Phase 1 - Foundation & Documentation

**Sprint:** 1
**Start Date:** 2026-06-16
**End Date:** 2026-06-20
**Goal:** Establish the complete project foundation -- architecture decisions, project scaffolding, development environment, and coding standards -- so that Phase 2 (Data Ingestion) can begin immediately in Week 2.

---

## Sprint Backlog

### Completed

| Task | Assignee | Notes |
|---|---|---|
| Initialize Git repository | Kashif | Done. Repo at `D:\Users\kashif.siddiqui\Projects\autocode`. |
| Create .gitignore | Kashif | Comprehensive exclusions for Python, Node, Terraform, data files. |
| Acquire ICD-10-CM April 2026 data | Kashif | All XML, TXT, PDF, XSD files in `data/ICD-10-CM/`. |
| ADR-001: Vector DB (Qdrant) | Kashif | Accepted. Self-hosted Qdrant with named vectors. |
| ADR-002: Chunking Strategy | Kashif | Accepted. Code-centric, ~130K chunks. |
| ADR-003: Embedding Model | Kashif | Accepted. Dual: OpenAI text-embedding-3-large + PubMedBERT. |
| ADR-004: Auth (Azure AD OIDC) | Kashif | Accepted. authlib + python-jose. |
| ADR-005: LLM Abstraction | Kashif | Accepted. Factory pattern, ABC, negative prompting. |
| Glossary | Kashif | Medical coding + project terminology. |
| Product vision document | Kashif | Core vision and value proposition. |
| Coding conventions | Kashif | Python, TypeScript, SQL, Git standards. |
| Project structure rules | Kashif | Directory layout and naming conventions. |
| Roadmap | Kashif | 8-phase plan with timeline estimates. |
| Backlog | Kashif | Feature backlog with P0-P3 priorities. |
| Task tracker | Kashif | Phase-by-phase task breakdown. |

### In Progress

| Task | Assignee | Target | Notes |
|---|---|---|---|
| Python project setup (pyproject.toml) | Kashif | 2026-06-17 | FastAPI, Pydantic, ruff, mypy, pytest config. |
| Next.js frontend scaffold | Kashif | 2026-06-17 | App Router, TypeScript, Tailwind, shadcn/ui. |
| Docker Compose (dev environment) | Kashif | 2026-06-18 | PostgreSQL 16, Qdrant latest, API dev server. |
| CLAUDE.md | Kashif | 2026-06-17 | Codebase context for AI-assisted development. |

### Not Started (This Sprint)

| Task | Assignee | Target | Notes |
|---|---|---|---|
| CI/CD skeleton (GitHub Actions) | Kashif | 2026-06-19 | Lint + test workflows. |
| Pre-commit hooks | Kashif | 2026-06-19 | ruff, mypy, eslint, prettier, conventional commits. |
| .env.example with variable schema | Kashif | 2026-06-18 | Document all required/optional env vars. |
| Local dev setup verification | Kashif | 2026-06-20 | End-to-end: clone, docker compose up, run tests. |

---

## Acceptance Criteria for Sprint Completion

1. **Python backend project** initializes with `pyproject.toml`, passes `ruff check` and `mypy`, and `pytest` runs (even with zero tests).
2. **Next.js frontend** initializes with App Router, TypeScript strict mode, Tailwind CSS, and passes `eslint` and `prettier --check`.
3. **Docker Compose** starts PostgreSQL, Qdrant, and a basic FastAPI dev server. All services are reachable and healthy.
4. **CLAUDE.md** exists with comprehensive codebase context.
5. **All ADRs** (001-005) are committed with status "Accepted."
6. **CI pipeline** runs lint and test on push (even if test suite is empty).
7. **Pre-commit hooks** enforce formatting and commit message conventions locally.
8. **.env.example** documents all environment variables with descriptions and defaults.

---

## Blockers

None currently.

---

## Notes

- Phase 2 (Data Ingestion Pipeline) starts Week 2. Prerequisite: Docker Compose with Qdrant running and Python project set up.
- Need to request OpenAI API key for embedding pipeline (Phase 2) and Anthropic API key for LLM integration (Phase 3). Create keys in respective platforms before Week 2.
- Consider setting up a development Azure AD tenant for auth testing in Phase 4. Entra ID free tier should be sufficient.
