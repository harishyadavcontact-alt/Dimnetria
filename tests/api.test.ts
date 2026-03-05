import request from "supertest";
import { describe, expect, it } from "vitest";
import app from "../src/server.js";

describe("capture gating", () => {
  it("blocks capture until evidence is viewed", async () => {
    const list = await request(app).get("/api/v1/discoveries");
    const discovery = list.body[0];

    const blocked = await request(app).post("/api/v1/captures").send({ discovery_id: discovery.id });
    expect(blocked.status).toBe(400);

    await request(app).get(`/api/v1/evidence/${discovery.evidence_ids[0]}`);
    const allowed = await request(app).post("/api/v1/captures").send({ discovery_id: discovery.id });
    expect(allowed.status).toBe(201);
  });
});
