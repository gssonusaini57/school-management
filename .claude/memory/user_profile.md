---
name: User profile — solo builder, Indian market
description: Single-developer building Indian-market business software; runs two projects on one shared VPS; values reusable, idempotent infra over per-project bespoke setup.
type: user
originSessionId: a28c76aa-d68b-4bf2-ac4b-fb655aa4a1d3
---
User builds and operates two projects:

1. **uploadmytds.com** — Java/Spring Boot 3 (Java 21) + Angular 19 + MySQL 8 + Tomcat 11. NSDL TIN-FC partner doing TDS return filing in India. Production: `104.237.2.140`. Test: `104.237.5.113`.
2. **school-management** (KIS School Management Portal) — FastAPI + MySQL + React/Vite/TS for a single school in India. Migrated from Firebase Firestore in May 2026. Test deploy on the same `104.237.5.113` VPS as uploadmytds, served at `https://expressonly.in/school/`.

User is a single-developer operator. Decisions to keep in mind:
- Operates on a shared VPS — no Kubernetes, no cloud-native services. Simple is right.
- Has Angular experience (uploadmytds) but accepted React for school-management when given a comparison.
- Doesn't have on-call rotation — auto-rollback on failed health checks is critical, not nice-to-have.
- Indian context: Aadhaar, IFSC, INR currency, English+Hindi audience, 12-grade school system.

How to apply: Default to lightweight, single-VPS-friendly architectures. Don't propose Redis / Kafka / message queues unless the user specifically asks. Keep ops surface area small — one DB engine (MySQL), one nginx config, one server.
