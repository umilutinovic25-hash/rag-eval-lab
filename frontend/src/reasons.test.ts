import { describe, expect, it } from "vitest";
import { decisionReason, fallbackReason, traceNote } from "./reasons";

describe("reasons", () => {
  it("explains the last decision step", () => {
    const trace = [
      { stage: "retrieval" },
      { stage: "decision", reason: "assistant_meta_request", refused: true },
    ];
    expect(decisionReason(trace)).toContain("sam sistem");
    expect(traceNote(trace[1])).toContain("sam sistem");
    expect(traceNote(trace[0])).toBeNull();
  });

  it("explains missing subject evidence", () => {
    expect(decisionReason([{stage: "decision", reason: "evidence_missing_subject"}])).toContain("okolnosti");
  });

  it("returns null for unknown or missing decisions", () => {
    expect(decisionReason([])).toBeNull();
    expect(decisionReason([{ stage: "decision", reason: "x" }])).toBeNull();
    expect(decisionReason(undefined)).toBeNull();
  });

  it("explains known fallbacks and gives a safe default for new ones", () => {
    expect(fallbackReason("polarity_conflict")).toContain("„da“ ili „ne“");
    expect(fallbackReason("something_new")).toContain("nije prošao proveru");
    expect(fallbackReason(null)).toBeNull();
  });
});
