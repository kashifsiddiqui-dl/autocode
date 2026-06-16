# Product Context & Positioning

## Product Identity

**Name:** Auto Code
**Tagline:** Intelligent ICD-10-CM coding, grounded in the source.
**Category:** Healthcare AI / Revenue Cycle Management / Clinical Decision Support
**Deployment Model:** Multi-tenant SaaS (Azure-hosted, HIPAA-compliant)

## Market Context

The US medical coding market is driven by regulatory complexity (ICD-10-CM's 74K+ codes), staffing shortages (AAPC reports a persistent shortage of certified coders), and financial pressure (coding errors cause an estimated $36B in annual claim denials). Existing solutions fall into three categories:

1. **Manual reference tools** (codebooks, PDF viewers, simple search tools) - Accurate but slow. Coder productivity is limited by lookup speed.
2. **Legacy encoder software** (3M, Optum EncoderPro, TruCode) - Established but expensive ($500-2,000/seat/year), with outdated UIs and keyword-based search that misses semantic matches.
3. **General AI tools** (ChatGPT, Claude, Gemini used ad-hoc) - Fast and natural-language capable, but fundamentally unsafe for coding -- they hallucinate codes from training data, use outdated versions, and have no audit trail.

Auto Code occupies the gap between these categories: the natural-language understanding of modern AI, the accuracy of an authoritative code database, and the safety guarantees (grounding, validation, audit) that healthcare compliance demands.

## Target Customers

### Ideal Customer Profile

**Segment:** Mid-size physician practices, specialty clinics, and medical billing companies.

**Characteristics:**
- 5-50 coders/billing staff
- Process 500-10,000 encounters/month
- Currently using manual lookup or legacy encoder software
- Azure AD / Microsoft 365 for identity management
- Cost-sensitive (cannot afford $1,000+/seat/year legacy encoder licenses)
- Open to AI-assisted workflows but require compliance guarantees

**Why this segment?**
- Large enough to have coding pain (volume creates lookup burden) but small enough to not have custom-built internal tools.
- Legacy encoder contracts are a known budget line item we can displace at lower cost.
- Azure AD prevalence simplifies our SSO story.
- Decision-makers (practice managers, RCM directors) are accessible and have budget authority.

### Expansion Segments (Post-Launch)

- **Large health systems** (50+ coders) - Require SAML, on-premise options, EMR integration
- **Individual coders** (freelance, consulting) - Self-service tier, lower price point
- **Coding education** (training programs, certification prep) - Modified UX for learning scenarios

## Competitive Positioning

### vs. Legacy Encoders (3M, Optum, TruCode)

| Dimension | Legacy Encoders | Auto Code |
|---|---|---|
| Input method | Keyword search, code browsing | Natural language description |
| Search quality | Exact/fuzzy keyword match | Semantic + keyword hybrid |
| Coding rules | Displayed alongside codes | Proactively surfaced as warnings |
| AI assistance | None or basic | LLM-powered reasoning with grounding |
| Pricing | $500-2,000/seat/year | Competitive SaaS pricing |
| Deployment | Installed software or legacy web | Modern web application, any browser |
| Updates | Manual update installation | Automatic, same-day updates |

**Positioning statement:** "Auto Code replaces keyword search with semantic understanding. Describe the condition, get the code -- with every coding rule checked automatically."

### vs. General AI (ChatGPT, Claude ad-hoc)

| Dimension | General AI (ad-hoc) | Auto Code |
|---|---|---|
| Code accuracy | Unreliable (training data, outdated) | Grounded in current ICD-10-CM (April 2026) |
| Hallucination risk | High | Near-zero (RAG + validation) |
| Coding rules | May or may not mention | Systematically checked and surfaced |
| Audit trail | None | Full session logging |
| HIPAA compliance | No (PHI sent to consumer API) | Yes (BAA-ready, PHI on controlled infra) |
| Version currency | Unknown training cutoff | Known, verified data version |
| Cost tracking | Per-token, unpredictable | Per-seat or per-query, predictable |

**Positioning statement:** "Auto Code gives you the natural-language experience of ChatGPT with the accuracy and compliance guarantees your revenue cycle demands."

## Pricing Strategy (Planned)

Pricing is not finalized. Initial thinking:

| Tier | Target | Model | Estimated Price |
|---|---|---|---|
| **Starter** | Small practices (1-5 users) | Per-seat/month | $49/seat/month |
| **Professional** | Mid-size practices (6-25 users) | Per-seat/month, volume discount | $39/seat/month |
| **Enterprise** | Large organizations (25+ users) | Custom pricing, annual contract | Contact sales |

All tiers include:
- Unlimited coding queries
- Full ICD-10-CM database (current version)
- Azure AD SSO
- Session history and audit logs
- CSV/PDF export

Enterprise adds:
- Custom LLM model selection
- SAML support
- Dedicated support
- SLA guarantees
- Custom integrations

## Key Metrics to Track

### Product Metrics
- Daily/weekly/monthly active users (DAU/WAU/MAU)
- Queries per user per day
- Code acceptance rate (recommended code accepted vs. modified vs. rejected)
- Time to code (query submission to code acceptance)
- Feedback rating distribution

### Business Metrics
- Customer acquisition cost (CAC)
- Monthly recurring revenue (MRR)
- Customer lifetime value (LTV)
- Churn rate (monthly/annual)
- Net Promoter Score (NPS)

### Quality Metrics
- Top-3 accuracy (correct code in top 3 recommendations)
- Hallucination rate (recommended codes not in ICD-10-CM)
- Excludes1 violation rate (mutually exclusive codes recommended together)
- Coding instruction miss rate (Code First/Use Additional not surfaced)

## Go-to-Market Strategy (Initial)

1. **Beta program** with 3-5 friendly practices. Collect feedback, measure accuracy, iterate on UX.
2. **Case study** from beta: quantify time savings, denial rate reduction, user satisfaction.
3. **Content marketing:** Blog posts on ICD-10-CM coding challenges, AI in healthcare, coding accuracy.
4. **AAPC/AHIMA conference presence:** Demo at medical coding professional events.
5. **Partnership exploration:** Medical billing companies as channel partners (they serve multiple practices).
6. **Referral program:** Existing customers refer new practices for account credit.
