# Current Focus

## Active Phase

**Phase 1: Project Foundation & Documentation**

## Status

In Progress

## What We're Doing

Setting up the foundational structure for the Auto Code platform. This phase establishes the directory structure, core documentation, agent definitions, infrastructure configurations, and development environment tooling that all subsequent phases build upon.

### Completed

- Project repository initialized with `.gitignore` covering all relevant patterns (Python, Node, Docker, Terraform, IDE, data files).
- ICD-10-CM April 2026 XML release data acquired and placed in `data/ICD-10-CM/`. All 5 XML source files and supporting documentation (PDFs, XSDs, TXT code lists) are present.
- Agent definitions created in `.ai/agents/` for all 7 system domains (frontend, backend-api, rag-pipeline, infrastructure, documentation, testing, security).
- Context files established in `.ai/context/` for tracking focus, decisions, and open questions.

### In Progress

- Core documentation: CLAUDE.md, glossary, architecture docs, initial specs.
- Infrastructure scaffolding: Docker Compose for dev environment, Makefile, initial Terraform module structure.
- Backend project setup: Python project configuration (pyproject.toml), dependency management, FastAPI app skeleton.
- Frontend project setup: Next.js 15 initialization, Tailwind + shadcn/ui configuration, project structure.

### Not Yet Started

- Database schema design and initial Alembic migration.
- Qdrant collection configuration.
- CI/CD pipeline definitions.
- ADR documents for the 5 key decisions already made.

## Next Phase

**Phase 2: Data Ingestion Pipeline** -- Build the ICD-10-CM XML parsers, code-centric chunking logic, embedding generation, and Qdrant loading pipeline. This is the foundation of the RAG system and must be solid before any retrieval work begins.

## Key Constraint

No feature code should be written until the foundation (documentation, project structure, dev environment, CI/CD) is stable and usable by all agents.
