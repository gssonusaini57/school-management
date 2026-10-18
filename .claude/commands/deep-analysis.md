# Command: /deep-analysis
<!-- prompt-library-version: 2026-08-31 -->

## Description
Generate a multi-document onboarding knowledge base for the codebase.

## When to Use
When a project needs durable reference documentation, not a one-off summary.

## Project-Specific Notes
<!-- Local customizations go BELOW this line. They are preserved across updates. -->

**P1 — DOMAIN CONTEXT (pre-filled for this repo; skip the "fill this in" step).**
> Domain: K-12 school administration for ONE school — Khalsa International Senior
> Secondary School, Jalalabad (Patiala, Punjab), affiliated to PSEB. Students,
> attendance, marks/results, fees, notices, staff, branded PDF stationery.
> Constraints: single-tenant; one shared box 69.62.72.137 running two instances
> (PROD at the root of kisschool.in, TEST under `/kisschool/` on the bare IP over
> HTTP) next to an unrelated Tomcat app; bilingual English + Gurmukhi
> Punjabi everywhere; PSEB-mandated print formats; MySQL is the only store (blobs
> included); solo maintainer with AI assistance; no automated test suite.
> Audience: the maintainer plus any future full-stack developer (Python/FastAPI,
> React/TypeScript, Kotlin/Compose).

**P2 — SOURCES OF "WHY".** Read `.claude/CLAUDE.md`, `.claude/GOTCHAS_*.md`,
`.claude/SESSION_HISTORY_*.md` and `.claude/memory/` before the code — they hold
the rationale behind most non-obvious designs. BUT verify every claim against the
code on the current branch: CLAUDE.md is a session snapshot and has lagged the
code before (admin login constants, JWT expiry hours). Where they disagree, cite
the code and flag the discrepancy.

**P3 — OUTPUT LOCATION.** `.claude/doc/deep-analysis/` (README + 00–10). Regenerate
in place; the docs are checked in and reviewed like code. Cite paths relative to
the repo root. Never copy real credentials — the archived gotchas and
`backend/scripts/fix_staff_credentials.py` contain some; refer to them, do not
reproduce them.

## Instructions

Act as a senior software engineer, system architect, and technical tutor.

Fully explore, understand, and document a production codebase as if onboarding a
new engineer who will maintain it for years. Assume the reader is new to this
project, is beginner-to-intermediate technically, and needs durable reference
documentation rather than a one-off summary.

## DOMAIN CONTEXT (fill this in before running, or tell me to infer it)
State the domain up front, because it changes what matters:
> Domain: <e.g. payments, healthcare messaging, security/SIEM, e-commerce, telemetry>
> Constraints: <e.g. regulatory, real-time throughput, legacy history, HA requirements>
> Audience: <e.g. backend devs, platform engineers, SRE, support>

If the system has a long history (multiple acquisitions, framework generations,
deprecated-but-load-bearing components), respect that reality: explain WHY a design
that looks outdated exists, rather than dismissing it.

## ANALYSIS REQUIREMENTS — do this before writing any document
1. Scan the entire folder and file structure; understand each folder's responsibility
2. Identify entry points, core modules, shared utilities, and configuration
3. Understand how modules communicate (in-process, HTTP, queue, DB, files)
4. Identify the architectural style and the design patterns actually in use
5. Trace the critical flows: startup, main request/processing path, data flow,
   error propagation, shutdown
6. Identify conventions, best practices, and deliberate trade-offs
7. Identify risks, technical debt, scaling limits, and modernization opportunities

## OUTPUT RULE (critical)
❗ Do NOT produce one giant document.
✅ Produce MULTIPLE focused Markdown files, each with a single learning goal, plus
an index. The result should be readable over several days, in order.

Save to `.claude/doc/deep-analysis/` (create it). Cross-link the documents.

## DOCUMENTS TO GENERATE

**README.md** — index: what each document covers and the recommended reading order.

**00-project-overview.md**
What this project is; the business/technical problem it solves; high-level goals;
who uses and maintains it; how it fits into the larger ecosystem.

**01-domain-concepts.md**
The domain vocabulary and concepts a newcomer must hold before the code makes sense.
Explain the domain, not just the code. Skip only if the domain is truly generic.

**02-high-level-architecture.md**
Architectural style; major components and responsibilities; how they communicate;
ASCII architecture diagrams; why this architecture was likely chosen and how it evolved.

**03-folder-structure-guide.md**
For EVERY folder including nested ones: path, why it exists, what lives there, its
responsibilities, what NOT to change casually, and the anti-patterns to avoid.

**04-core-modules-and-business-logic.md**
The core modules; services, controllers, models, repositories, utilities; each one's
responsibility; how they communicate; the dependency relationships between them.

**05-execution-and-data-flow.md**
Startup sequence step by step; the main request/message/job flow; data
transformations; where validation, business rules, and persistence happen; how
errors propagate; what happens on shutdown.

**06-configuration-and-environment.md**
Config files; environment variables; secrets handling (names and mechanisms only —
never real values); build, deploy, and runtime configuration; per-environment
differences; the misconfigurations that actually bite people.

**07-design-patterns-and-tradeoffs.md**
Patterns used, explicit and implicit; coding conventions; error-handling strategy;
logging, metrics, and monitoring; testing strategy and structure; and the deliberate
trade-offs — including why some parts look old and what depends on them staying that way.

**08-risks-limitations-and-improvements.md**
Technical debt; scalability ceilings; maintainability, performance, and operational
risks; security risks; concrete, actionable improvements ranked by value vs effort.

**09-onboarding-guide.md**
How a new developer should approach the codebase; which files to read first, in
order; the mental model of the system; how to make a safe first change; how to debug
a production issue; common mistakes to avoid.

**10-glossary.md**
Domain terms, internal jargon, and acronyms — defined simply, with a pointer to
where each concept lives in the code.

## WRITING GUIDELINES
- Write like a senior engineer mentoring a new hire: explain WHY, not just WHAT
- Be explicit and concrete; never write vague filler like "this handles the logic"
- Every structural claim must be traceable to a real file or folder — cite paths
- Use ASCII diagrams, tables, and real examples from the code
- Prioritize understanding over brevity; this is long-term reference material
- Where you could not determine something from the code, write an explicit
  "UNKNOWN / needs owner confirmation" note rather than inventing an explanation
- Never include real secrets, credentials, tokens, or customer data
