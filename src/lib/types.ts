export type SubjectType = "person" | "event" | "org";
export type PatternType =
  | "BOB_RUBIN_TRADE"
  | "REVOLVING_DOOR"
  | "BAILOUT_TO_BOARDROOM"
  | "COMPLEXITY_ARBITRAGE"
  | "POSTDICTING_STIGLITZ"
  | "IATROGENIC_INTERVENTION";

export interface Evidence {
  id: string;
  source_type: "registry" | "filing" | "watchdog_db" | "news" | "report" | "court" | "webpage" | "other";
  publisher: string;
  title: string;
  url: string;
  accessed_at: string;
  trust_tier: 1 | 2 | 3 | 4;
}

export interface Discovery {
  id: string;
  subject_type: SubjectType;
  subject_id: string;
  pattern_type: PatternType;
  pattern_label: string;
  severity_score: number;
  confidence: number;
  detected_at: string;
  explanation_json: Record<string, unknown>;
  status: "suggested" | "captured" | "dismissed" | "flagged_for_review";
  evidence_ids: string[];
}
