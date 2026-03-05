# Vetala (Fragilista Tracker) v0.1 skeleton

Evidence-first MVP scaffold for discovery and capture workflows.

## Included in this commit

- Postgres schema with all required core objects and constraints (`db/schema.sql`).
- Deterministic scoring engine for SITG/ELI/FCS/II/FS and Bob Rubin detector (`src/lib/scoring.ts`).
- JSON schemas (Zod) matching extraction/discovery/score explanation contracts (`src/lib/schemas.ts`).
- Seed dataset meeting demo minimums: 20 people, 10 orgs, 30 events, 60 evidence items, 30 discoveries, 18 captures (`src/lib/seed.ts`).
- REST API skeleton (`src/server.ts`) with:
  - search, profile, event, evidence, discovery, and captures endpoints
  - evidence-first capture gating (capture blocked until evidence has been viewed)
  - discovery evidence sorting by trust tier then recency
- Tests for scoring and capture gating behavior.

## Run

```bash
npm install
npm run test
npm run dev
```

API base: `http://localhost:3000/api/v1`
