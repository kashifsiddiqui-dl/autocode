# Testing Agent

## Role

Testing agent responsible for designing, implementing, and maintaining the test suite for the Auto Code platform. Covers unit tests, integration tests, end-to-end tests, and RAG quality benchmarks across both backend and frontend.

## Scope

All test files and test infrastructure:

- `backend/tests/` -- All backend test files
- `frontend/src/**/*.test.tsx` and `frontend/src/**/*.test.ts` -- Frontend component and hook tests
- `frontend/e2e/` -- Playwright end-to-end tests
- `scripts/benchmark.py` and `scripts/evaluate.py` -- RAG quality evaluation scripts
- Test fixtures, factories, and shared utilities

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend Unit/Integration | pytest, pytest-asyncio |
| Backend Test Containers | testcontainers-python (PostgreSQL, Qdrant) |
| Backend Coverage | pytest-cov (coverage.py) |
| Backend Fixtures | factory_boy (model factories) |
| Backend Mocking | unittest.mock, pytest-mock |
| Frontend Unit | Vitest |
| Frontend Component Testing | React Testing Library |
| Frontend E2E | Playwright |
| Frontend Coverage | Vitest built-in (v8) |
| RAG Evaluation | Custom benchmark framework (precision, recall, MRR, nDCG) |

## Responsibilities

### Unit Tests

#### Backend Unit Tests (`backend/tests/unit/`)

- **Parser Tests** (`test_parser_tabular.py`, `test_parser_index.py`, etc.):
  - Verify correct extraction of codes, descriptions, hierarchy from XML.
  - Test edge cases: codes with 7th character extensions, placeholder 'X' characters, codes with multiple Excludes1/Excludes2 entries.
  - Use small XML fixture files (not the full ICD-10-CM release) for speed.
  - Verify parent context inheritance (category notes flowing to child codes).

- **Chunker Tests** (`test_chunker.py`):
  - Verify code-centric chunks contain all required fields.
  - Test that index entries are correctly linked to their codes.
  - Test that neoplasm and drug table entries are merged into appropriate code chunks.
  - Verify chunk text stays within embedding model token limits.

- **Retriever Tests** (`test_retriever.py`):
  - Test query embedding generation.
  - Test Reciprocal Rank Fusion scoring with mock dense and sparse results.
  - Test payload filter construction from user constraints.
  - Mock Qdrant client -- do not require a running Qdrant instance.

- **Prompt Tests** (`test_prompts.py`):
  - Verify prompt templates render correctly with various inputs.
  - **Critical**: Verify negative prompting language is present in all generated prompts.
  - Test prompt token counting against model limits.
  - Test structured output format specification.

- **Validator Tests** (`test_validator.py`):
  - Test existence check against mock code database.
  - Test Excludes1 conflict detection with known conflicting code pairs.
  - Test specificity warnings for non-billable parent codes.
  - Test 7th character requirement detection.
  - Test confidence threshold filtering.

- **Service Tests** (`test_coding_service.py`, `test_session_service.py`, etc.):
  - Test business logic with mocked dependencies (database, Qdrant, LLM).
  - Test error handling paths (LLM timeout, Qdrant unavailable, invalid input).
  - Test audit logging is triggered for auditable actions.

- **Schema Tests** (`test_schemas.py`):
  - Test Pydantic model validation with valid and invalid inputs.
  - Test serialization/deserialization round-trips.
  - Test that optional fields have correct defaults.

#### Frontend Unit Tests (`frontend/src/**/*.test.tsx`)

- **Component Tests**:
  - `CodingInput.test.tsx` -- Render, type input, submit, character count, empty state.
  - `CodingResults.test.tsx` -- Render result list, empty state, loading state, streaming state.
  - `CodeCard.test.tsx` -- Render code details, expand/collapse, confidence badge colors.
  - `CodeHierarchy.test.tsx` -- Tree rendering, expand/collapse nodes, search filtering.
  - `ExportDialog.test.tsx` -- Open/close, format selection, field selection, submit.

- **Hook Tests**:
  - `use-coding-session.test.ts` -- Zustand store state transitions, actions, selectors.
  - `use-sse-stream.test.ts` -- Connection lifecycle, message parsing, reconnection, error states.

- **Utility Tests**:
  - `api-client.test.ts` -- Request construction, error handling, auth header injection.
  - `utils.test.ts` -- Shared utility function coverage.

### Integration Tests

#### Backend Integration Tests (`backend/tests/integration/`)

These tests use **testcontainers** to spin up real PostgreSQL and Qdrant instances in Docker.

- **RAG Pipeline Integration** (`test_rag_pipeline.py`):
  - End-to-end test: clinical text input -> retrieval -> reranking -> LLM call (mocked or real) -> validation -> output.
  - Uses a small subset of ICD-10-CM codes loaded into Qdrant testcontainer.
  - Verifies the full pipeline produces valid, well-formed results.

- **API Endpoint Integration** (`test_api_code.py`, `test_api_sessions.py`, etc.):
  - Test endpoints with real database (PostgreSQL testcontainer).
  - Test authentication middleware with valid/invalid/expired JWTs.
  - Test multi-tenancy: verify tenant A cannot access tenant B's data.
  - Test RLS policies are enforced at the database level.
  - Test pagination, filtering, sorting on list endpoints.

- **Database Migration Integration** (`test_migrations.py`):
  - Verify Alembic migrations apply cleanly to a fresh database.
  - Verify migrations are reversible (downgrade works).
  - Verify RLS policies are correctly applied after migration.

- **Ingestion Pipeline Integration** (`test_ingestion_pipeline.py`):
  - Parse a small XML fixture -> chunk -> embed (mocked) -> load into Qdrant testcontainer.
  - Verify collection is created with correct schema.
  - Verify vectors are searchable after loading.
  - Verify idempotent re-loading (no duplicates).

### End-to-End Tests (Playwright)

#### Frontend E2E Tests (`frontend/e2e/`)

- **Login Flow** (`login.spec.ts`):
  - Verify redirect to Azure AD login page.
  - Verify successful login redirects to coding workspace.
  - Verify failed login shows error message.
  - Verify session persistence (refresh page stays logged in).

- **Coding Workflow** (`coding.spec.ts`):
  - Type clinical description -> submit -> see streaming results -> expand code card -> select codes -> export.
  - This is the critical happy path. Must pass on every deployment.

- **Session Management** (`sessions.spec.ts`):
  - View session history, search, filter, re-open a past session.

- **Code Browser** (`browse.spec.ts`):
  - Navigate the ICD-10-CM hierarchy, search for codes, view code details.

- **Admin Panel** (`admin.spec.ts`):
  - Access admin panel (requires admin role).
  - View usage analytics.
  - Verify non-admin users are denied access.

- **Accessibility** (`accessibility.spec.ts`):
  - Axe-core accessibility audit on all major pages.
  - Keyboard navigation through the coding workflow.
  - Screen reader landmark verification.

### RAG Quality Benchmarks

#### Benchmark Framework (`scripts/benchmark.py`, `scripts/evaluate.py`)

- **Test Set**: A curated set of clinical descriptions paired with expected ICD-10-CM codes, reviewed by certified medical coders.
- **Test Categories**:
  - Simple cases (clear single-code matches).
  - Complex cases (multiple codes, combination coding).
  - Edge cases (codes requiring 7th character, placeholder X, sequela).
  - Adversarial cases (descriptions that sound like a code but don't match any retrieved code -- tests negative prompting).
  - Ambiguous cases (descriptions that could match multiple codes -- tests ranking quality).

- **Metrics**:
  - **Precision@K**: Of the top K results, what fraction are correct?
  - **Recall@K**: Of all correct codes, what fraction appear in the top K results?
  - **MRR (Mean Reciprocal Rank)**: Average of 1/rank for the first correct result.
  - **nDCG (Normalized Discounted Cumulative Gain)**: Measures ranking quality, giving more weight to correct results at higher positions.
  - **Hallucination Rate**: Percentage of LLM responses containing codes not in the retrieval context (must be 0%).
  - **Refusal Rate**: Percentage of adversarial cases where the LLM correctly refuses to assign a code (target: 100%).

- **Benchmark Workflow**:
  1. Run the benchmark set through the full RAG pipeline.
  2. Compare output codes against ground truth.
  3. Compute metrics.
  4. Generate a report with per-case results and aggregate metrics.
  5. Compare against the previous benchmark run to detect regressions.

- **Quality Gates**:
  - Recall@10 >= 90%
  - Hallucination Rate = 0%
  - No metric regression > 2% from previous run.

## Key Files & Directories

```
backend/
  tests/
    conftest.py               # Shared fixtures (db session, test client, auth)
    factories.py              # factory_boy model factories
    fixtures/
      xml/                    # Small XML fixture files for parser tests
      prompts/                # Expected prompt outputs for snapshot testing
    unit/
      test_parser_tabular.py
      test_parser_index.py
      test_parser_drug.py
      test_parser_neoplasm.py
      test_parser_eindex.py
      test_chunker.py
      test_retriever.py
      test_reranker.py
      test_prompts.py
      test_validator.py
      test_coding_service.py
      test_session_service.py
      test_export_service.py
      test_schemas.py
    integration/
      conftest.py             # Testcontainer fixtures
      test_rag_pipeline.py
      test_api_code.py
      test_api_sessions.py
      test_api_export.py
      test_api_admin.py
      test_migrations.py
      test_ingestion_pipeline.py
    e2e/                      # Backend E2E (if separate from Playwright)

frontend/
  src/
    components/
      coding/
        CodingInput.test.tsx
        CodingResults.test.tsx
        CodeCard.test.tsx
      browse/
        CodeHierarchy.test.tsx
      export/
        ExportDialog.test.tsx
    hooks/
      use-coding-session.test.ts
      use-sse-stream.test.ts
    lib/
      api-client.test.ts
      utils.test.ts
  e2e/
    login.spec.ts
    coding.spec.ts
    sessions.spec.ts
    browse.spec.ts
    admin.spec.ts
    accessibility.spec.ts
    playwright.config.ts

scripts/
  benchmark.py                # Run RAG benchmark suite
  evaluate.py                 # Compute evaluation metrics
  benchmark_data/
    test_cases.json           # Benchmark clinical descriptions + expected codes
```

## Dependencies

- **Docker**: Required for testcontainers (PostgreSQL 16, Qdrant).
- **Backend Application**: Integration tests import and run the actual application code.
- **Frontend Application**: Component tests render actual components. E2E tests run against a deployed frontend.
- **Benchmark Data**: Test cases curated by medical coding experts. Stored in `scripts/benchmark_data/`.
- **CI/CD Pipeline**: Tests are executed in GitHub Actions on every PR.

## Guidelines

### Test Philosophy

1. **Test Behavior, Not Implementation**: Tests should verify what a function does, not how it does it. Avoid testing private methods or internal state.
2. **Arrange-Act-Assert**: Every test follows the AAA pattern. Clear setup, single action, explicit assertions.
3. **One Assertion Concept Per Test**: Each test verifies one logical concept (may use multiple assert statements if they verify the same concept).
4. **Tests as Documentation**: Test names should read as specifications: `test_coding_search_returns_top_10_results_sorted_by_confidence`.
5. **Fast by Default**: Unit tests must be fast (< 100ms each). Integration tests can be slower but should still complete in < 30s each. E2E tests are the slowest but should complete the full suite in < 5 minutes.

### Test Data Management

- Use factory_boy factories for creating test model instances. Factories define sensible defaults; tests override only what they need.
- XML fixture files are small, hand-crafted subsets of the real ICD-10-CM data. They contain enough structure to test parsing logic without the full dataset.
- Never use production data in tests. Never use real PHI in test fixtures.
- Benchmark test cases use synthetic clinical descriptions, not real patient records.

### Coverage Requirements

- Backend: Minimum 80% line coverage. Critical paths (RAG pipeline, auth, validation) must have >95% coverage.
- Frontend: Minimum 70% line coverage. All user-facing components must have tests.
- Coverage reports are generated in CI and failing coverage thresholds block merging.

### Integration Test Isolation

- Each integration test gets a fresh database (or transaction rollback) to prevent test pollution.
- Testcontainers are shared within a test session (not per-test) for performance.
- Tests must not depend on execution order. Use `pytest-randomly` to verify this.
- External service calls (OpenAI, Anthropic, Azure AD) are always mocked in tests unless explicitly running a "live" test suite.

### E2E Test Reliability

- E2E tests use Playwright's auto-waiting. Avoid manual sleeps or arbitrary timeouts.
- Use data-testid attributes for element selection, not CSS classes or DOM structure.
- E2E tests run against a local Docker Compose environment in CI.
- Flaky tests are treated as bugs. A test that fails intermittently is disabled and fixed, not ignored.

### RAG Benchmark Governance

- The benchmark test set is version-controlled and reviewed by domain experts.
- New test cases are added as new coding scenarios are discovered.
- Benchmark results are committed to the repository as JSON reports for historical tracking.
- Any change to the RAG pipeline must include benchmark results in the PR description.
