# Specification Quality Checklist: Music Source Expansion

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-30
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain — resolved in iteration 2: Q1 video platforms → reference sources, Q2 credentialed services → reference sources (link-out only), Q3 lyrics → out of scope
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Validation Notes

**Content Quality**

- *No implementation details* — The spec names no library, framework, endpoint, schema, or code construct. Existing project capabilities are referenced only as assumptions about what already exists (e.g. "existing source plugin contract"), not as instructions to build something.
- *User value focus* — All five user stories are written as listener and maintainer journeys. The source registry, fixtures, and time budgets appear only as constraints serving those journeys.
- *Non-technical audience* — Terms like "direct link", "quality level", and "domain parking" are used with plain-language explanation in the Edge Cases and Out of Scope sections.
- *Mandatory sections* — User Scenarios & Testing, Requirements (with Functional Requirements and Key Entities), and Success Criteria are all present and populated. Optional sections (Scope Interpretation, Assumptions, Dependencies, Out of Scope) are included because the 20-name input is heterogeneous and would otherwise read as an unexplained scope reduction.

**Requirement Completeness**

- *3 open clarifications* — **RESOLVED in iteration 2.** All three were asked with tables of options and consequences, and all three were answered:
  - **Q1 (video platforms)** answered *C*. Encoded as FR-023: Aparat, Namasha, Rubika, and Fam are registered as reference sources, no video variant is added to the media model.
  - **Q2 (credentialed streaming)** answered *list-only*. Encoded as FR-011 and FR-012: reference sources resolve to a page address only, offer no player or download control, and never prompt for or store credentials. The No Media Relaying principle is preserved rather than compromised, which is the main reason this option is the safe one.
  - **Q3 (lyrics)** answered *A*, audio only. Encoded as FR-027, an explicit prohibition, so a later contributor does not quietly add a lyrics field on the assumption it was merely forgotten.
  - **Interpretation flagged**: the video-platform letter answer (*C*) and the streaming-services prose answer describe different outcomes — option C as offered was "extract a video's audio as a playable stream", while the stated intent was "list and link out, no listening or downloading". The spec treats both groups identically as reference sources, following the stated intent. This is recorded in the spec's Clarification Resolutions section and was raised with the user for confirmation.
  - **The three answers are now load-bearing, not cosmetic.** Turning credentialed services into supported sources required introducing the full/reference source distinction (FR-002) as a first-class concept rather than a special case. That distinction now runs through the user stories, requirements, key entities, and success criteria.

**`/speckit-clarify` session (4 further questions answered)**

All items above were re-evaluated after the clarify session; no marker changed state, but the following spec gaps were closed:

- *Result ordering across kinds* — was undefined. Now FR-005a: full-source results always precede reference-source results, with intra-group relevance order unchanged. Covered by a new User Story 1 scenario.
- *Degraded-source threshold* — SC-009 previously said "within one refresh", which was not measurable. Now FR-018a/FR-018b and a rewritten SC-009 specify 3 separate failed searches as the trigger, independent of maintainer action, and confirm 1–2 failures leave a source active and still queried. Two new User Story 4 scenarios.
- *Per-user source hiding* — was Missing entirely; the spec had actively promised no personalization. Now FR-029 through FR-031: a browser-local filter that affects only that user, cannot override a system-determined inactive state, and requires no account. The contradicting "no personalization" assumption was rewritten rather than left to conflict, and two new User Story 3 scenarios.
- *Terminology* — "kind" and "tier" were both used for the same concept. Normalised to "kind" throughout, including two incidental uses of "tier" in ordinary English, so the term carries exactly one meaning.
- *Testability* — Every FR is stated as an observable capability ("MUST return results from every other enabled source", "MUST yield zero results rather than junk entries") and is traceable to at least one acceptance scenario.
- *Measurable success criteria* — SC-001 through SC-010 carry counts, time bounds, percentages, or explicit zero-tolerance conditions.
- *Technology-agnostic criteria* — SC-001, SC-002, SC-003, SC-005, SC-006 are stated in listener-visible terms. SC-008 is stated as an observable property of network behaviour rather than an internal mechanism.
- *Scope bounded* — The Scope Interpretation section and Out of Scope list name all 20 sites and give a specific reason for each exclusion. SC-007 makes the completeness of that accounting a measurable criterion.
- *Dependencies and assumptions* — Both sections are present. The offline-capture constraint is called out explicitly as a real risk to SC-004 rather than assumed away.

**Feature Readiness**

- *Acceptance criteria coverage* — Each FR maps to at least one user story acceptance scenario or edge case. FR-024 (reconcile existing entries) and FR-025 (missing domain) are covered by the "Two names, one site", "A name already present", and "Missing domain" edge cases respectively. The reference-source requirements (FR-011, FR-012) are covered by all four scenarios in User Story 3.
- *Primary flows covered* — P1 search, P2 playback and download from a full source, P3 reaching a reference-only track, P4 honest status reporting, and P5 offline verification cover the full loop from discovery to consumption to maintenance, for both source kinds.
- *No regressions* — FR-016, FR-028, and SC-010 guard the existing movies, games, and already-supported music behaviour, which is the main risk of a change that is purely additive in the registry.
- *No leaked implementation* — Verified on re-read; no file paths, class names, or library references appear in the requirements or success criteria.

**Two specification risks flagged for planning, not failures**

1. **The input supplies 20 names but only ~12 usable domains**, and several of those are unconfirmed or already present in the registry under a different domain. FR-025 and SC-007 make this explicit rather than leaving the implementer to discover it, but planning should expect real source capture work and should not assume all 20 resolve to shippable sources. SC-007 is written to be satisfiable honestly: a site that cannot be reached is recorded as inactive with a reason, which still counts as accounted for.
2. **The full/reference classification is an assumption about what these sites expose**, not a verified fact. FR-021 makes classification correctable after verification, and the "Reference source that turns out to expose direct files" and "Full source that turns out to be gated" edge cases cover both directions. Planning should treat the initial split as a starting point to be confirmed per source during capture, not a fixed input.

## Notes

- Items marked incomplete require spec updates before `/speckit-clarify` or `/speckit-plan`
- `/speckit-implement` reads checklist checkbox state as a gate and must not modify markers
- `checklists/requirements.md` has a separate built-in lifecycle maintained by `/speckit-specify` and `/speckit-clarify`
