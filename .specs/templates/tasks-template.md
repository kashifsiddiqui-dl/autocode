# Tasks: FEAT-{NNN} {Feature Name}

## Feature: [FEAT-{NNN}]({path to spec.md})
## Assignee: {assignee or TBD}
## Sprint: {sprint number or TBD}
## Last Updated: {YYYY-MM-DD}

---

## Task Breakdown

### Phase 1: {Phase Name} (e.g., Setup / Scaffolding)

- [ ] **T-{NNN}-01**: {Task title}
  - **Effort:** {S/M/L or hours}
  - **Description:** {What needs to be done}
  - **Acceptance:** {How to verify completion}
  - **Files:** {Key files to create or modify}

- [ ] **T-{NNN}-02**: {Task title}
  - **Effort:** {S/M/L or hours}
  - **Description:** {What needs to be done}
  - **Acceptance:** {How to verify completion}
  - **Files:** {Key files to create or modify}

### Phase 2: {Phase Name} (e.g., Core Implementation)

- [ ] **T-{NNN}-03**: {Task title}
  - **Effort:** {S/M/L or hours}
  - **Description:** {What needs to be done}
  - **Acceptance:** {How to verify completion}
  - **Depends on:** T-{NNN}-01, T-{NNN}-02
  - **Files:** {Key files to create or modify}

### Phase 3: {Phase Name} (e.g., Testing & Validation)

- [ ] **T-{NNN}-04**: {Task title}
  - **Effort:** {S/M/L or hours}
  - **Description:** {What needs to be done}
  - **Acceptance:** {How to verify completion}
  - **Depends on:** T-{NNN}-03
  - **Files:** {Key files to create or modify}

---

## Task Dependency Graph

```
T-{NNN}-01 ──┐
              ├──> T-{NNN}-03 ──> T-{NNN}-04
T-{NNN}-02 ──┘
```

---

## Effort Summary

| Size | Count | Estimated Hours |
|------|-------|----------------|
| Small (S) | {count} | {hours} |
| Medium (M) | {count} | {hours} |
| Large (L) | {count} | {hours} |
| **Total** | **{total}** | **{total hours}** |

---

## Progress

| Task | Status | Started | Completed | Notes |
|------|--------|---------|-----------|-------|
| T-{NNN}-01 | {Not Started/In Progress/Done} | -- | -- | -- |
| T-{NNN}-02 | {Not Started/In Progress/Done} | -- | -- | -- |

---

## Notes

<!-- Implementation notes, decisions made during development, blockers encountered -->

- {Note 1}
- {Note 2}
