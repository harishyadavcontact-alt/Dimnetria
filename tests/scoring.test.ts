import { describe, expect, it } from "vitest";
import { computeFs, computeScoreFromSignals, detectBobRubinTrade } from "../src/lib/scoring.js";

describe("scoring", () => {
  it("computes SITG score deterministically", () => {
    const score = computeScoreFromSignals("SITG", [
      { signal_type: "insulated_role", value_numeric: 1 },
      { signal_type: "authority_level_high", value_numeric: 1 },
      { signal_type: "personal_exposure_present", value_numeric: 1 },
    ]);
    expect(score).toBe(20);
  });

  it("computes FS composite with persistence bonus", () => {
    expect(computeFs(80, 70, 60, 40, 10)).toBe(76);
  });

  it("detects Bob Rubin trade with required thresholds and source tier", () => {
    const result = detectBobRubinTrade({
      authority_level_proxy: 0.75,
      externalized_loss_proxy: 0.9,
      sitg_gap_proxy: 0.7,
      persistence_proxy: 0.5,
      evidence_tiers: [2, 3],
      evidence_ids: ["00000000-0000-4000-8000-000000000001", "00000000-0000-4000-8000-000000000002"],
      avg_extraction_confidence: 0.9,
      source_diversity_score: 0.8,
      evidence_quality_score: 0.7,
    });

    expect(result?.pattern_type).toBe("BOB_RUBIN_TRADE");
    expect(result?.severity_score).toBeGreaterThan(0);
    expect(result?.confidence).toBe(0.7);
  });
});
