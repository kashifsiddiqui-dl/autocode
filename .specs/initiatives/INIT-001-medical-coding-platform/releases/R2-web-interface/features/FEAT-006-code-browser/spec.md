# FEAT-006: Code Browser

## Status: Not Started
## Priority: P1
## Release: R2 Web Interface
## Owner: TBD
## Estimated Effort: 1 week
## Depends On: FEAT-001, FEAT-003

---

## Summary

Build a hierarchical tree view browser for the ICD-10-CM codeset, enabling medical coders to navigate the full code hierarchy (22 chapters > sections > categories > codes), perform semantic search, and view detailed code information including descriptions, includes/excludes notes, and related codes.

## Problem Statement

Medical coders frequently need to manually browse the ICD-10-CM codeset to find specific codes, understand code relationships, or verify that the correct level of specificity has been applied. A hierarchical browser with semantic search provides a faster alternative to manual PDF lookups and helps coders understand the context around AI-suggested codes.

## Functional Requirements

### FR-1: Hierarchical Tree View

**Level 1 -- Chapters (22 total)**
Display all 22 ICD-10-CM chapters as expandable root nodes:

| Chapter | Code Range | Description |
|---------|-----------|-------------|
| 1 | A00-B99 | Certain infectious and parasitic diseases |
| 2 | C00-D49 | Neoplasms |
| 3 | D50-D89 | Diseases of the blood and blood-forming organs |
| 4 | E00-E89 | Endocrine, nutritional and metabolic diseases |
| 5 | F01-F99 | Mental, behavioral and neurodevelopmental disorders |
| 6 | G00-G99 | Diseases of the nervous system |
| 7 | H00-H59 | Diseases of the eye and adnexa |
| 8 | H60-H95 | Diseases of the ear and mastoid process |
| 9 | I00-I99 | Diseases of the circulatory system |
| 10 | J00-J99 | Diseases of the respiratory system |
| 11 | K00-K95 | Diseases of the digestive system |
| 12 | L00-L99 | Diseases of the skin and subcutaneous tissue |
| 13 | M00-M99 | Diseases of the musculoskeletal system and connective tissue |
| 14 | N00-N99 | Diseases of the genitourinary system |
| 15 | O00-O9A | Pregnancy, childbirth and the puerperium |
| 16 | P00-P96 | Certain conditions originating in the perinatal period |
| 17 | Q00-Q99 | Congenital malformations, deformations and chromosomal abnormalities |
| 18 | R00-R99 | Symptoms, signs and abnormal clinical and laboratory findings |
| 19 | S00-T88 | Injury, poisoning and certain other consequences of external causes |
| 20 | V00-Y99 | External causes of morbidity |
| 21 | Z00-Z99 | Factors influencing health status and contact with health services |
| 22 | U00-U85 | Codes for special purposes |

**Level 2 -- Sections**
Expand a chapter to show its sections (code ranges within the chapter).

**Level 3 -- Categories**
Expand a section to show 3-character category codes (e.g., A01, E11).

**Level 4 -- Codes**
Expand a category to show all specific codes (e.g., A01.0, A01.00, E11.9).

### FR-2: Tree View UX

- Lazy loading: Only fetch children when a node is expanded
- Expand/collapse toggle with arrow icon
- Visual indicators:
  - Folder icon for non-leaf nodes (chapters, sections, categories)
  - Document icon for leaf/billable codes
  - Green dot for billable codes
  - Code count badge showing number of children
- Keyboard navigation: Arrow keys to navigate, Enter to expand/collapse
- Breadcrumb trail showing current location in hierarchy
- "Expand all" and "Collapse all" buttons for current subtree

### FR-3: Semantic Search

- Search input at the top of the code browser
- Searches both code and description fields
- Uses the RAG dense retrieval (Qdrant vector search) for semantic matching
- Results displayed as a flat list with hierarchy context
- Clicking a search result navigates to that code in the tree (auto-expanding parents)
- Debounced search (300ms delay after typing stops)
- Minimum 2 characters to trigger search
- Results show: code, description, chapter, billable status, relevance score

### FR-4: Code Detail View

Clicking a code in the tree or search results opens a detail panel:

| Section | Content |
|---------|---------|
| Code | ICD-10-CM code (e.g., E11.9) |
| Short Description | Brief description |
| Long Description | Full clinical description |
| Billable | Yes/No indicator |
| Hierarchy | Full path: Chapter > Section > Category > Code |
| Includes | Included conditions/terms |
| Excludes1 | Conditions excluded from this code (mutually exclusive) |
| Excludes2 | Conditions not included here but may be coded additionally |
| Code First | "Code first" instructions |
| Use Additional | "Use additional code" instructions |
| 7th Character | Required 7th character extensions (if applicable) |
| Parent Code | Link to parent code |
| Child Codes | Links to more specific child codes (if any) |
| Sibling Codes | Other codes at the same level under the same parent |

### FR-5: Integration with Coding Workflow

- "Add to session" button on code detail view (when a coding session is active)
- Adds the code as a manually-added coding result with status "accepted"
- Link from code cards in FEAT-004 (hierarchy breadcrumb) to code browser
- Deep linking: URL path `/codes/{code}` opens browser at that code

## Non-Functional Requirements

- **Performance**: Tree expansion < 200ms, search results < 500ms
- **Rendering**: Virtual scrolling for large result sets (sections with 100+ codes)
- **Accessibility**: Tree view follows WAI-ARIA Treeview pattern
- **State**: Tree expansion state preserved during session (not persisted across page loads)

## Technical Design

### Component Architecture

```
src/frontend/src/components/browser/
├── CodeBrowser.tsx              # Main browser layout (tree + detail panel)
├── CodeTree.tsx                 # Hierarchical tree view container
├── CodeTreeNode.tsx             # Individual tree node (chapter/section/category/code)
├── CodeSearch.tsx               # Semantic search input and results
├── CodeSearchResults.tsx        # Search results list
├── CodeDetail.tsx               # Code detail panel
├── CodeHierarchyPath.tsx        # Breadcrumb navigation
└── AddToSessionButton.tsx       # Add code to active session
```

### API Calls

```
GET /api/v1/codes/chapters                        -> Level 1 nodes
GET /api/v1/codes/chapters/{chapter}/sections      -> Level 2 nodes
GET /api/v1/codes/browse?parent={code}             -> Level 3-4 nodes
GET /api/v1/codes/{code}                           -> Code detail
GET /api/v1/codes/search?q={query}&limit=20        -> Search results
```

## Acceptance Criteria

- [ ] Tree view displays all 22 ICD-10-CM chapters as root nodes
- [ ] Expanding a chapter loads and displays its sections
- [ ] Expanding a section loads and displays its categories
- [ ] Expanding a category loads and displays its codes
- [ ] Billable codes are visually distinguished from non-billable codes
- [ ] Semantic search returns relevant codes for clinical terms
- [ ] Clicking a search result navigates to that code in the tree
- [ ] Code detail panel shows all fields (description, hierarchy, includes, excludes, annotations)
- [ ] "Add to session" button adds code to the active coding session
- [ ] Breadcrumb navigation shows current position in hierarchy
- [ ] Virtual scrolling handles sections with 100+ codes without performance degradation
- [ ] Keyboard navigation works (arrow keys, Enter, search focus)
- [ ] Deep linking via URL path works (/codes/E11.9 opens code detail)

## Test Plan

### Component Tests
- Test CodeTreeNode expand/collapse behavior
- Test CodeSearch debouncing and minimum character requirement
- Test CodeDetail rendering with complete and partial code data
- Test AddToSessionButton integration with coding store

### Integration Tests
- Test lazy loading of tree nodes from API
- Test search with various clinical terms
- Test navigation from search result to tree position
- Test deep link URL parsing and rendering

### Performance Tests
- Measure tree expansion time for chapters with many sections
- Measure search response time for common clinical terms
- Verify virtual scrolling smoothness with 500+ codes visible
