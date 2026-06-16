# Design: {Feature or Component Name}

## Feature: FEAT-{NNN}
## Author: {author}
## Status: {Draft | Review | Approved | Superseded}
## Created: {YYYY-MM-DD}
## Last Updated: {YYYY-MM-DD}

---

## Overview

<!-- Brief summary of the design and its purpose. What is being designed and why? -->

{Overview of the design}

## Context

<!-- Background information needed to understand the design decisions.
     Reference the feature spec and any prior decisions. -->

- Feature Spec: [FEAT-{NNN}]({path to spec.md})
- Related ADRs: {list any relevant ADRs}

## Goals & Non-Goals

### Goals
- {Goal 1}
- {Goal 2}

### Non-Goals
- {What this design explicitly does NOT address}

## Architecture

<!-- High-level architecture diagram and description.
     Show how this component fits into the overall system. -->

```
{ASCII architecture diagram}
```

{Description of architecture}

## Detailed Design

### Component 1: {Name}

<!-- Describe each major component: purpose, interface, behavior -->

**Purpose:** {What this component does}

**Interface:**
```python
# or TypeScript, SQL, etc.
{Interface definition}
```

**Behavior:**
{How the component works}

### Component 2: {Name}

{Same structure as above}

## Data Model

<!-- Database tables, collections, or data structures introduced or modified -->

```sql
{Schema definitions}
```

## API Design

<!-- Endpoints, request/response formats, error handling -->

```
{HTTP method} {path}
{Request/response examples}
```

## Error Handling

<!-- How errors are handled, propagated, and surfaced to users -->

| Error Condition | Handling | User-Facing Message |
|----------------|----------|---------------------|
| {Condition} | {How handled} | {Message shown} |

## Security Considerations

<!-- Authentication, authorization, data protection, input validation -->

- {Security consideration 1}
- {Security consideration 2}

## Performance Considerations

<!-- Expected load, latency targets, optimization strategies -->

- {Performance consideration 1}
- {Performance consideration 2}

## Testing Strategy

<!-- How the design will be tested beyond unit tests -->

- {Testing approach 1}
- {Testing approach 2}

## Migration & Rollback

<!-- If applicable: how to migrate from current state, how to roll back -->

{Migration plan or "N/A -- greenfield implementation"}

## Alternatives Considered

<!-- Other approaches that were considered and why they were rejected -->

### Alternative 1: {Name}
- **Approach:** {Description}
- **Rejected because:** {Reason}

### Alternative 2: {Name}
- **Approach:** {Description}
- **Rejected because:** {Reason}

## Open Questions

- [ ] {Unresolved question 1}
- [ ] {Unresolved question 2}

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| {date} | {decision} | {why} |
