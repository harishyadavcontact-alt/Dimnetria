import type { Discovery, Evidence, PatternType } from "./types.js";

const uuid = (n: number) => `00000000-0000-4000-8000-${n.toString().padStart(12, "0")}`;

export const people = Array.from({ length: 20 }, (_, i) => ({
  id: uuid(i + 1),
  full_name: `Person ${i + 1}`,
  primary_country: i % 2 === 0 ? "US" : "UK",
  description: `Profile for Person ${i + 1}`,
}));

export const organizations = Array.from({ length: 10 }, (_, i) => ({
  id: uuid(100 + i + 1),
  name: `Organization ${i + 1}`,
  org_type: ["agency", "corp", "ngo", "party", "thinktank", "other"][i % 6],
}));

export const events = Array.from({ length: 30 }, (_, i) => ({
  id: uuid(200 + i + 1),
  title: `Event ${i + 1}`,
  category: ["policy", "vote", "reg_action", "corp_action", "advisory", "forecast", "public_statement", "other"][i % 8],
  summary: `Sourced event summary ${i + 1}`,
}));

export const evidence: Evidence[] = Array.from({ length: 60 }, (_, i) => ({
  id: uuid(300 + i + 1),
  source_type: (i % 4 === 0 ? "watchdog_db" : i % 3 === 0 ? "filing" : "news") as Evidence["source_type"],
  publisher: i % 4 === 0 ? "OpenSecrets" : `Publisher ${i + 1}`,
  title: `Evidence ${i + 1}`,
  url: `https://example.org/evidence/${i + 1}`,
  accessed_at: new Date(Date.now() - i * 86400000).toISOString(),
  trust_tier: ((i % 4) + 1) as 1 | 2 | 3 | 4,
}));

const patternTypes: PatternType[] = [
  "BOB_RUBIN_TRADE",
  "REVOLVING_DOOR",
  "BAILOUT_TO_BOARDROOM",
  "COMPLEXITY_ARBITRAGE",
  "POSTDICTING_STIGLITZ",
  "IATROGENIC_INTERVENTION",
];

export const discoveries: Discovery[] = Array.from({ length: 30 }, (_, i) => ({
  id: uuid(400 + i + 1),
  subject_type: "person",
  subject_id: people[i % people.length].id,
  pattern_type: patternTypes[i % patternTypes.length],
  pattern_label: `${patternTypes[i % patternTypes.length]} detected`,
  severity_score: 40 + (i % 50),
  confidence: 0.55 + (i % 40) / 100,
  detected_at: new Date(Date.now() - i * 3600000).toISOString(),
  explanation_json: { notes: "seeded" },
  status: "suggested",
  evidence_ids: [evidence[i % evidence.length].id, evidence[(i + 1) % evidence.length].id],
}));

export const demoUser = { id: uuid(900), email: "demo@vetala.local" };

export const captures = Array.from({ length: 18 }, (_, i) => ({
  id: uuid(500 + i + 1),
  user_id: demoUser.id,
  discovery_id: discoveries[i].id,
  captured_at: new Date(Date.now() - i * 7200000).toISOString(),
  note: `Capture note ${i + 1}`,
  verification_level: "viewed_evidence",
  share_token: `share-${i + 1}`,
}));
