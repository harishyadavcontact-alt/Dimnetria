import express from "express";
import { captures, demoUser, discoveries, events, evidence, organizations, people } from "./lib/seed.js";

const app = express();
app.use(express.json());

const viewedEvidence = new Set<string>();
const mutableCaptures = [...captures];

app.get("/api/v1/search", (req, res) => {
  const q = String(req.query.q || "").toLowerCase();
  const type = String(req.query.type || "all");
  const include = (target: string) => type === "all" || type === target;

  const results = {
    people: include("people") ? people.filter((p) => p.full_name.toLowerCase().includes(q)) : [],
    orgs: include("orgs") ? organizations.filter((o) => o.name.toLowerCase().includes(q)) : [],
    events: include("events") ? events.filter((e) => e.title.toLowerCase().includes(q)) : [],
  };
  res.json(results);
});

app.get("/api/v1/people/:id", (req, res) => {
  const person = people.find((p) => p.id === req.params.id);
  if (!person) return res.status(404).json({ error: "Not found" });
  const personDiscoveries = discoveries.filter((d) => d.subject_id === person.id);
  res.json({ ...person, discoveries: personDiscoveries });
});

app.get("/api/v1/organizations/:id", (req, res) => {
  const org = organizations.find((o) => o.id === req.params.id);
  if (!org) return res.status(404).json({ error: "Not found" });
  res.json(org);
});

app.get("/api/v1/events/:id", (req, res) => {
  const event = events.find((e) => e.id === req.params.id);
  if (!event) return res.status(404).json({ error: "Not found" });
  res.json(event);
});

app.get("/api/v1/evidence/:id", (req, res) => {
  const item = evidence.find((e) => e.id === req.params.id);
  if (!item) return res.status(404).json({ error: "Not found" });
  viewedEvidence.add(item.id);
  res.json(item);
});

app.get("/api/v1/discoveries", (req, res) => {
  const { subject_type, subject_id, status } = req.query;
  const results = discoveries.filter((d) => {
    if (subject_type && d.subject_type !== subject_type) return false;
    if (subject_id && d.subject_id !== subject_id) return false;
    if (status && d.status !== status) return false;
    return true;
  });

  const expanded = results.map((d) => ({
    ...d,
    evidence: d.evidence_ids
      .map((id) => evidence.find((e) => e.id === id))
      .filter(Boolean)
      .sort((a, b) => (a!.trust_tier - b!.trust_tier) || (b!.accessed_at.localeCompare(a!.accessed_at))),
  }));

  res.json(expanded);
});

app.get("/api/v1/discoveries/:id", (req, res) => {
  const discovery = discoveries.find((d) => d.id === req.params.id);
  if (!discovery) return res.status(404).json({ error: "Not found" });
  res.json(discovery);
});

app.get("/api/v1/me", (_req, res) => res.json(demoUser));

app.get("/api/v1/me/captures", (_req, res) => {
  res.json(mutableCaptures.filter((c) => c.user_id === demoUser.id));
});

app.post("/api/v1/captures", (req, res) => {
  const discoveryId = req.body.discovery_id as string;
  const discovery = discoveries.find((d) => d.id === discoveryId);
  if (!discovery) return res.status(404).json({ error: "Discovery not found" });

  const evidenceViewed = discovery.evidence_ids.some((id) => viewedEvidence.has(id));
  if (!evidenceViewed) {
    return res.status(400).json({
      error: "Capture blocked until evidence viewed",
      detail: "View Evidence before Capture.",
    });
  }

  const capture = {
    id: `capture-${Date.now()}`,
    user_id: demoUser.id,
    discovery_id: discoveryId,
    captured_at: new Date().toISOString(),
    note: req.body.note ?? null,
    verification_level: "viewed_evidence",
    share_token: `share-${Date.now()}`,
  };
  mutableCaptures.push(capture);
  res.status(201).json(capture);
});

app.get("/health", (_req, res) => res.json({ ok: true }));

const port = Number(process.env.PORT || 3000);
if (process.env.NODE_ENV !== "test") {
  app.listen(port, () => {
    console.log(`Vetala API running on :${port}`);
  });
}

export default app;
