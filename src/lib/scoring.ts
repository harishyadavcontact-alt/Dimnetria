import type { PatternType } from "./types.js";

export interface SignalInput {
  signal_type: string;
  value_numeric?: number;
}

const clamp100 = (n: number): number => Math.max(0, Math.min(100, Math.round(n)));

export function computeScoreFromSignals(scoreType: "SITG" | "ELI" | "FCS" | "II", signals: SignalInput[]): number {
  const weights: Record<string, number> = {
    insulated_role: 25,
    authority_level_high: 25,
    fixed_salary_only: 20,
    personal_exposure_present: -30,
    taxpayer_cost_mentioned: 35,
    shareholder_loss_large: 25,
    public_harm_policy: 20,
    bailout_or_subsidy: 25,
    moral_hazard_created: 25,
    increased_leverage: 25,
    concentrated_risk: 20,
    volatility_suppression: 15,
    intervention_backfire_documented: 40,
    unintended_consequences: 25,
    repeated_interventions_same_failure: 20,
  };
  const allowed: Record<string, string[]> = {
    SITG: ["insulated_role", "authority_level_high", "fixed_salary_only", "personal_exposure_present"],
    ELI: ["taxpayer_cost_mentioned", "shareholder_loss_large", "public_harm_policy", "bailout_or_subsidy"],
    FCS: ["moral_hazard_created", "increased_leverage", "concentrated_risk", "volatility_suppression"],
    II: ["intervention_backfire_documented", "unintended_consequences", "repeated_interventions_same_failure"],
  };

  const raw = signals
    .filter((s) => allowed[scoreType].includes(s.signal_type))
    .reduce((acc, s) => acc + (weights[s.signal_type] ?? 0) * (s.value_numeric ?? 1), 0);

  return clamp100(raw);
}

export function computeFs(sitg: number, eli: number, fcs: number, ii: number, persistenceBonus = 0): number {
  return clamp100(0.3 * sitg + 0.3 * eli + 0.25 * fcs + 0.15 * ii + Math.min(10, persistenceBonus));
}

export interface BobRubinInputs {
  authority_level_proxy: number;
  externalized_loss_proxy: number;
  sitg_gap_proxy: number;
  persistence_proxy: number;
  evidence_tiers: number[];
  evidence_ids: string[];
  avg_extraction_confidence: number;
  source_diversity_score: number;
  evidence_quality_score: number;
}

export function detectBobRubinTrade(input: BobRubinInputs): null | {
  pattern_type: PatternType;
  severity_score: number;
  confidence: number;
  explanation_json: Record<string, unknown>;
} {
  const tierOk = input.evidence_tiers.some((tier) => tier <= 2);
  const countOk = input.evidence_ids.length >= 2;
  const thresholdPass =
    input.authority_level_proxy >= 0.7 &&
    input.externalized_loss_proxy >= 0.6 &&
    input.sitg_gap_proxy >= 0.6 &&
    tierOk &&
    countOk;

  if (!thresholdPass) {
    return null;
  }

  const severityScore = clamp100(
    Math.round(
      (0.35 * input.externalized_loss_proxy +
        0.25 * input.sitg_gap_proxy +
        0.2 * input.authority_level_proxy +
        0.2 * input.persistence_proxy) *
        100,
    ),
  );
  const confidence = Math.min(
    input.avg_extraction_confidence,
    input.source_diversity_score,
    input.evidence_quality_score,
  );

  return {
    pattern_type: "BOB_RUBIN_TRADE",
    severity_score: severityScore,
    confidence,
    explanation_json: {
      pattern_type: "BOB_RUBIN_TRADE",
      pattern_label: "Bob Rubin Trade detected",
      triggered_rules: [
        {
          rule_id: "bob_rubin_trade_v1",
          description: "Authority, externalized loss, and SITG gap thresholds with minimum evidence quality.",
          passed: true,
          inputs: {
            authority_level_proxy: input.authority_level_proxy,
            externalized_loss_proxy: input.externalized_loss_proxy,
            sitg_gap_proxy: input.sitg_gap_proxy,
            persistence_proxy: input.persistence_proxy,
          },
          thresholds: {
            authority_level_proxy: 0.7,
            externalized_loss_proxy: 0.6,
            sitg_gap_proxy: 0.6,
          },
          evidence_ids: input.evidence_ids,
        },
      ],
      severity_calc: {
        formula:
          "round((0.35*externalized_loss_proxy + 0.25*sitg_gap_proxy + 0.20*authority_level_proxy + 0.20*persistence_proxy) * 100)",
        inputs: {
          authority_level_proxy: input.authority_level_proxy,
          externalized_loss_proxy: input.externalized_loss_proxy,
          sitg_gap_proxy: input.sitg_gap_proxy,
          persistence_proxy: input.persistence_proxy,
        },
        severity_score: severityScore,
      },
      confidence_calc: {
        inputs: {
          avg_extraction_confidence: input.avg_extraction_confidence,
          source_diversity_score: input.source_diversity_score,
          evidence_quality_score: input.evidence_quality_score,
        },
        confidence,
      },
    },
  };
}
