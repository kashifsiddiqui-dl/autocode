# FEAT-004: Coding UI

## Status: Not Started
## Priority: P0
## Release: R2 Web Interface
## Owner: TBD
## Estimated Effort: 1.5 weeks
## Depends On: FEAT-003

---

## Summary

Build a responsive web interface for medical coders to input clinical notes, receive AI-suggested ICD-10-CM codes via SSE streaming, and review/accept/reject coding suggestions. The input experience uses a social-media-post-like card metaphor, and results display as interactive code cards with full hierarchy and exclusion context.

## Problem Statement

Medical coders need a purpose-built interface that makes AI-assisted coding intuitive and efficient. The UI must handle the SSE streaming nature of the API, present complex hierarchical code data clearly, and support rapid accept/reject decisions. A poor UI experience would negate the time savings of AI-assisted coding.

## Functional Requirements

### FR-1: Clinical Notes Input

- Large, resizable text area styled as a social-media-post-like card
- Patient demographics fields above the text area (name, DOB, MRN, gender)
- Character count indicator (current / 10,000 max)
- Word count display
- "Analyze" submit button (disabled while streaming, enabled when text is non-empty)
- Visual indication of streaming state (pulsing border, animated indicator)
- Ability to edit text and resubmit after viewing results
- Auto-save of draft text to localStorage

### FR-2: Streaming Results Display

- Results section appears below the input card
- Pipeline stage indicators showing progress through retrieval -> reranking -> analysis -> validation
- Each stage shows: name, status (pending/in-progress/completed), duration
- Code cards appear progressively as SSE `code` events arrive
- Smooth entry animation for each new code card
- Total count and processing time shown in completion banner

### FR-3: Code Cards

Each suggested code displays as an interactive card:

| Element | Description |
|---------|-------------|
| Code badge | ICD-10-CM code in a colored badge (color by confidence level) |
| Description | Short and long description |
| Confidence | Visual bar + percentage (green >= 0.8, amber 0.5-0.8, red < 0.5) |
| Reasoning | LLM's explanation (collapsible, collapsed by default) |
| Hierarchy | Breadcrumb: Chapter > Section > Category > Code |
| Excludes1 | Red-flagged mutually exclusive codes (if any) |
| Excludes2 | Amber-noted additional codes to consider (if any) |
| Annotations | Code-first, use-additional notes |
| Billable indicator | Green checkmark for billable, amber warning for non-billable |
| Accept button | Marks code as accepted (fills green) |
| Reject button | Marks code as rejected (fills red, dims card) |

### FR-4: Code Card Interactions

- **Accept/Reject toggle**: Click to toggle status, visual feedback immediate
- **Expand reasoning**: Click to show/hide LLM reasoning text
- **View hierarchy**: Click breadcrumb to open code browser at that location (FEAT-006)
- **Excludes warning**: If user accepts two codes that are Excludes1 of each other, show inline warning
- **Bulk actions**: "Accept All Above Threshold" button with configurable threshold slider
- **Manual code add**: Search input to find and add codes not in the AI suggestions

### FR-5: Session Management UI

- **Dashboard**: List of recent coding sessions with status badges (draft, in_review, completed)
- **Session card**: Shows patient name, date, code count, status
- **Resume session**: Click to reopen a draft session with previous results
- **Delete session**: Confirmation dialog before deletion

### FR-6: Responsive Layout

- Minimum supported width: 1024px
- Two-column layout on wide screens (input left, results right)
- Single-column stacked layout on narrower screens
- Sticky header with navigation and user context
- Keyboard shortcuts:
  - `Ctrl+Enter` to submit clinical text
  - `A` to accept focused code card
  - `R` to reject focused code card
  - `Tab` to navigate between code cards

## Non-Functional Requirements

- **Performance**: Initial page load < 2 seconds, code card render < 50ms
- **Accessibility**: WCAG 2.1 AA compliance (color contrast, keyboard navigation, screen reader labels)
- **Browser support**: Chrome 120+, Firefox 120+, Edge 120+, Safari 17+
- **State management**: Zustand for global state, React Query for server state
- **Error handling**: Toast notifications for API errors, retry prompts for network failures

## Technical Design

### Component Architecture

```
src/frontend/src/
├── app/
│   ├── layout.tsx                # Root layout with providers
│   ├── page.tsx                  # Dashboard / session list
│   └── coding/
│       └── [sessionId]/
│           └── page.tsx          # Coding workspace
├── components/
│   ├── coding/
│   │   ├── ClinicalNotesInput.tsx    # Social-media-post-like input card
│   │   ├── PatientDemographics.tsx   # Patient info form fields
│   │   ├── PipelineProgress.tsx      # Stage indicators
│   │   ├── CodeCard.tsx              # Individual code suggestion card
│   │   ├── CodeCardList.tsx          # Scrollable list of code cards
│   │   ├── ConfidenceBar.tsx         # Visual confidence indicator
│   │   ├── HierarchyBreadcrumb.tsx   # Chapter > Section > Code breadcrumb
│   │   ├── ExcludesWarning.tsx       # Excludes conflict warning
│   │   ├── ManualCodeSearch.tsx      # Manual code addition search
│   │   └── BulkActions.tsx           # Accept all above threshold
│   ├── sessions/
│   │   ├── SessionList.tsx           # Dashboard session list
│   │   └── SessionCard.tsx           # Individual session card
│   └── ui/                           # shadcn/ui components
├── hooks/
│   ├── useCodingStream.ts            # SSE connection hook
│   ├── useSession.ts                 # Session CRUD hook
│   └── useCodeSearch.ts              # Code browser search hook
├── lib/
│   ├── api.ts                        # API client (fetch wrapper)
│   ├── sse.ts                        # SSE event parser
│   └── utils.ts                      # Utility functions
├── stores/
│   └── codingStore.ts                # Zustand store for coding state
└── types/
    ├── coding.ts                     # CodingSuggestion, Session types
    └── api.ts                        # API request/response types
```

### SSE Hook Design

```typescript
function useCodingStream() {
  const [stages, setStages] = useState<PipelineStage[]>([]);
  const [codes, setCodes] = useState<CodingSuggestion[]>([]);
  const [status, setStatus] = useState<'idle' | 'streaming' | 'complete' | 'error'>('idle');

  const startAnalysis = async (request: CodingRequest) => {
    setStatus('streaming');
    const eventSource = new EventSource(/* SSE endpoint */);

    eventSource.addEventListener('stage', (e) => {
      // Update pipeline stage progress
    });

    eventSource.addEventListener('code', (e) => {
      // Append new code card with animation
    });

    eventSource.addEventListener('complete', (e) => {
      setStatus('complete');
      eventSource.close();
    });
  };

  return { stages, codes, status, startAnalysis };
}
```

## Acceptance Criteria

- [ ] Clinical notes input renders as a styled card with patient demographics fields
- [ ] Character and word count update in real-time
- [ ] Submit triggers SSE connection and displays streaming progress
- [ ] Pipeline stages show visual progress (pending -> in-progress -> completed with timing)
- [ ] Code cards appear with smooth animation as SSE events arrive
- [ ] Code cards display: code, description, confidence bar, hierarchy breadcrumb
- [ ] Accept/reject toggles work with immediate visual feedback
- [ ] Expanding reasoning section shows LLM explanation
- [ ] Excludes1 conflict warning appears when accepting conflicting codes
- [ ] Manual code search allows adding codes not in AI suggestions
- [ ] Session dashboard shows list of recent sessions
- [ ] Sessions can be resumed, and previous results are loaded
- [ ] Keyboard shortcuts work (Ctrl+Enter, A/R for accept/reject, Tab navigation)
- [ ] Layout is responsive and usable at 1024px width
- [ ] Accessibility audit passes WCAG 2.1 AA requirements

## Test Plan

### Component Tests
- Test ClinicalNotesInput character counting and submit state
- Test CodeCard accept/reject toggling
- Test PipelineProgress stage transitions
- Test ExcludesWarning conflict detection

### Integration Tests
- Test full SSE streaming flow with mock API
- Test session creation, loading, and resumption
- Test manual code search and addition

### E2E Tests
- Complete coding workflow: enter text -> submit -> review codes -> accept/reject -> verify session saved
- Resume session workflow: load session -> verify previous results displayed
- Error handling: disconnect during streaming -> verify graceful recovery
