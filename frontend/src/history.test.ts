import { describe, it, expect } from "vitest";
import * as history from "./history";
import type { Conversation } from "./types";
const a: Conversation = {
  id: "a",
  title: "One",
  turns: [{ id: "t1", question: "First", error: "interrupted" }],
};
const doc = (
  conversations: Conversation[],
  deleted: Record<string, number> = {},
) => ({ version: 2 as const, conversations, deleted });

describe("history merging", () => {
  it("preserves both new conversations from two stale writers", () => {
    expect(
      history
        .mergeHistory(
          doc([a]),
          [a, { id: "b", title: "Local", turns: [] }],
          doc([a, { id: "c", title: "Remote", turns: [] }]),
        )
        .conversations.map((c) => c.id)
        .sort(),
    ).toEqual(["a", "b", "c"]);
  });
  it("merges concurrent new questions in the same conversation", () => {
    const local = {
      ...a,
      turns: [...a.turns, { id: "t2", question: "Local" }],
    };
    const remote = {
      ...a,
      turns: [...a.turns, { id: "t3", question: "Remote" }],
    };
    expect(
      history
        .mergeHistory(doc([a]), [local], doc([remote]))
        .conversations[0].turns.map((t) => t.id)
        .sort(),
    ).toEqual(["t1", "t2", "t3"]);
  });
  it("keeps remote deletions despite a stale local answer", () => {
    const local = {
      ...a,
      turns: [...a.turns, { id: "t2", question: "Local" }],
    };
    expect(
      history.mergeHistory(doc([a]), [local], doc([], { a: 1 })).conversations,
    ).toEqual([]);
  });
  it("supports deliberate undo without losing another conversation", () => {
    const remote = { id: "b", title: "Remote", turns: [] };
    const merged = history.mergeHistory(
      doc([], { a: 1 }),
      [a],
      doc([remote], { a: 1 }),
      new Set(["a"]),
    );
    expect(merged.conversations.map((c) => c.id).sort()).toEqual(["a", "b"]);
    expect(merged.deleted.a).toBeUndefined();
  });
  it("migrates healthy legacy arrays", () => {
    expect(history.parseHistory(JSON.stringify([a])).conversations).toEqual([
      a,
    ]);
  });
});
