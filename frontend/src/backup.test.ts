// @vitest-environment node
import { expect, test } from "vitest";
import { createBackup, readBackup, mergeBackup } from "./backup";
import type { Conversation } from "./types";
const cs: Conversation[] = [
  {
    id: "old",
    title: "Question",
    turns: [{ id: "t", question: "Q", jobId: "foreign-job" }],
  },
];
test("backup validates checksum and strips active foreign jobs", async () => {
  const backup = await createBackup(cs);
  const incoming = await readBackup(backup);
  expect(incoming[0].id).not.toBe("old");
  expect(incoming[0].turns[0].jobId).toBeUndefined();
  expect(incoming[0].turns[0].error).toContain("Uvezen");
  const tampered = JSON.parse(backup);
  tampered.payload.conversations[0].title = "changed";
  await expect(readBackup(JSON.stringify(tampered))).rejects.toThrow(
    "checksum",
  );
});
test("merge refuses overflow rather than dropping existing conversations", () => {
  expect(mergeBackup(cs, cs)).toHaveLength(2);
  expect(() => mergeBackup(Array(10).fill(cs[0]), cs)).toThrow(
    "Ništa nije prepisano",
  );
});
