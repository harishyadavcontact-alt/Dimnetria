import { captures, discoveries, events, evidence, organizations, people } from "../src/lib/seed.js";

console.log(
  JSON.stringify(
    {
      people: people.length,
      organizations: organizations.length,
      events: events.length,
      evidence: evidence.length,
      discoveries: discoveries.length,
      captures: captures.length,
    },
    null,
    2,
  ),
);
