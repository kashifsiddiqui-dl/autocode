# Release 2: Web Interface

## Initiative: INIT-001 Medical Coding Platform
## Status: Not Started
## Target Date: TBD
## Owner: kashif.siddiqui@disrupt.com

---

## Scope

Release 2 delivers the user-facing web application that medical coders use to interact with the AI coding engine. It includes the primary coding workflow UI, multi-format export, and a hierarchical code browser for manual lookup.

## Goals

1. Provide a complete browser-based coding workflow (input -> review -> export)
2. Support PDF, CSV, JSON, and HL7 FHIR export formats
3. Build an interactive ICD-10-CM code browser with hierarchical navigation and search
4. Deliver a responsive, accessible UI that meets healthcare UX standards

## Features

| Feature | Name | Priority | Status |
|---------|------|----------|--------|
| [FEAT-004](features/FEAT-004-coding-ui/spec.md) | Coding UI | P0 | Not Started |
| [FEAT-005](features/FEAT-005-export/spec.md) | Export | P1 | Not Started |
| [FEAT-006](features/FEAT-006-code-browser/spec.md) | Code Browser | P1 | Not Started |

## Dependencies

- Release 1 complete (API endpoints available)
- FEAT-003 Coding API deployed and stable
- Frontend project scaffolded (Next.js + shadcn/ui)

## Success Criteria

| Criterion | Target | Validation |
|-----------|--------|------------|
| End-to-end workflow | Complete coding cycle in browser | Manual QA walkthrough |
| Export accuracy | All formats produce valid output | Automated export validation tests |
| Code browser coverage | All 98,186 codes navigable | Browser renders full hierarchy |
| Responsive design | Works on 1024px+ screens | Cross-browser testing |
| Accessibility | WCAG 2.1 AA compliance | axe/lighthouse audit |
| Page load time | < 2s initial load | Lighthouse performance score >= 80 |

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| SSE streaming browser compatibility | Broken experience in some browsers | EventSource polyfill, fallback polling |
| Large code tree rendering | UI performance degradation | Virtual scrolling, lazy loading |
| Export format complexity (HL7 FHIR) | Development time | Start with PDF/CSV, FHIR as stretch |
| Real-time state management | UI bugs | Zustand + React Query for clear state boundaries |

## Release Checklist

- [ ] All FEAT-004 acceptance criteria met
- [ ] All FEAT-005 acceptance criteria met
- [ ] All FEAT-006 acceptance criteria met
- [ ] Cross-browser testing complete (Chrome, Firefox, Edge, Safari)
- [ ] Accessibility audit passed
- [ ] Performance benchmarks met
- [ ] User acceptance testing with medical coder feedback
- [ ] Frontend deployed and integrated with R1 API
