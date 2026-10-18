import { validAnswer } from "./contracts";
import type { Conversation } from "./types";

async function digest(text: string) {
  return [
    ...new Uint8Array(
      await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text)),
    ),
  ]
    .map((v) => v.toString(16).padStart(2, "0"))
    .join("");
}
export async function createBackup(conversations: Conversation[]) {
  const payload = { created_at: new Date().toISOString(), conversations };
  return JSON.stringify(
    {
      format: "izvor-history",
      version: 3,
      sha256: await digest(JSON.stringify(payload)),
      payload,
    },
    null,
    2,
  );
}
export async function readBackup(raw: string): Promise<Conversation[]> {
  if (new TextEncoder().encode(raw).length > 5000000)
    throw new Error("Backup može imati najviše 5 MB.");
  const value = JSON.parse(raw);
  if (
    value?.format !== "izvor-history" ||
    value.version !== 3 ||
    !value.payload ||
    (await digest(JSON.stringify(value.payload))) !== value.sha256
  )
    throw new Error("Verzija ili checksum backup-a nije ispravan.");
  const cs = value.payload.conversations;
  if (
    !Array.isArray(cs) ||
    cs.length > 10 ||
    !cs.every(
      (c) =>
        c &&
        typeof c.id === "string" &&
        typeof c.title === "string" &&
        Array.isArray(c.turns) &&
        c.turns.length <= 30 &&
        c.turns.every(
          (t: Record<string, unknown>) =>
            t &&
            typeof t.id === "string" &&
            typeof t.question === "string" &&
            (!t.result || validAnswer(t.result)),
        ),
    )
  )
    throw new Error("Backup nema ispravnu strukturu razgovora.");
  return cs.map((c) => ({
    id: crypto.randomUUID(),
    title: c.title,
    turns: c.turns.map((t: Conversation["turns"][number]) => ({
      id: crypto.randomUUID(),
      question: t.question,
      ...(t.result
        ? { result: t.result }
        : {
            error:
              "Uvezen nezavršen zahtev. Pokrenite ga ponovo na ovom serveru.",
          }),
    })),
  }));
}
export function mergeBackup(
  existing: Conversation[],
  incoming: Conversation[],
) {
  if (existing.length + incoming.length > 10)
    throw new Error(
      "Nema mesta za sve razgovore (najviše 10). Izvezite i uklonite odabrane razgovore pre uvoza. Ništa nije prepisano.",
    );
  return [...incoming, ...existing];
}
