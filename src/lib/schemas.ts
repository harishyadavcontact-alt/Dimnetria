import { z } from "zod";

const nullableString = z.union([z.string(), z.literal("null")]);

export const extractionOutputSchema = z.object({
  people: z.array(
    z.object({
      name: z.string(),
      aliases: z.array(z.string()),
      country: nullableString,
      confidence: z.number().min(0).max(1),
    }),
  ),
  orgs: z.array(
    z.object({
      name: z.string(),
      org_type: z.enum(["agency", "corp", "ngo", "party", "thinktank", "other", "null"]),
      country: nullableString,
      confidence: z.number().min(0).max(1),
    }),
  ),
  events: z.array(
    z.object({
      title: z.string(),
      category: z.enum(["policy", "vote", "reg_action", "corp_action", "advisory", "forecast", "public_statement", "other"]),
      start_date: nullableString,
      end_date: nullableString,
      jurisdiction: nullableString,
      participants: z.array(
        z.object({
          person_name: z.string(),
          role_in_event: z.string(),
          org_name: nullableString,
          confidence: z.number().min(0).max(1),
        }),
      ),
      outcomes: z.array(
        z.object({
          outcome_type: z.enum(["financial", "legal", "social", "operational"]),
          magnitude_text: nullableString,
          affected_party: z.enum(["taxpayers", "shareholders", "customers", "public", "other", "null"]),
          confidence: z.number().min(0).max(1),
        }),
      ),
      claims: z.array(
        z.object({
          claim_text: z.string(),
          evidence_quote: z.string().max(25 * 8),
          confidence: z.number().min(0).max(1),
        }),
      ),
      confidence: z.number().min(0).max(1),
    }),
  ),
  meta: z.object({ extraction_notes: nullableString }),
});

export const discoveryExplanationSchema = z.object({
  pattern_type: z.string(),
  pattern_label: z.string(),
  triggered_rules: z.array(
    z.object({
      rule_id: z.string(),
      description: z.string(),
      passed: z.boolean(),
      inputs: z.object({
        authority_level_proxy: z.number(),
        externalized_loss_proxy: z.number(),
        sitg_gap_proxy: z.number(),
        persistence_proxy: z.number(),
      }),
      thresholds: z.object({
        authority_level_proxy: z.number(),
        externalized_loss_proxy: z.number(),
        sitg_gap_proxy: z.number(),
      }),
      evidence_ids: z.array(z.string().uuid()),
    }),
  ),
  severity_calc: z.object({
    formula: z.string(),
    inputs: z.object({
      authority_level_proxy: z.number(),
      externalized_loss_proxy: z.number(),
      sitg_gap_proxy: z.number(),
      persistence_proxy: z.number(),
    }),
    severity_score: z.number().int(),
  }),
  confidence_calc: z.object({
    inputs: z.object({
      avg_extraction_confidence: z.number(),
      source_diversity_score: z.number(),
      evidence_quality_score: z.number(),
    }),
    confidence: z.number(),
  }),
});

export const scoreExplanationSchema = z.object({
  score_type: z.enum(["SITG", "ELI", "FCS", "II", "FS"]),
  score_version: z.string(),
  signals: z.array(
    z.object({
      signal_id: z.string().uuid(),
      signal_type: z.string(),
      value_numeric: z.number(),
      value_text: z.union([z.string(), z.literal("null")]),
      evidence_id: z.union([z.string().uuid(), z.literal("null")]),
      weight: z.number(),
    }),
  ),
  calculation: z.object({
    raw_sum: z.number(),
    clamped: z.number().int(),
    notes: z.union([z.string(), z.literal("null")]),
  }),
});
