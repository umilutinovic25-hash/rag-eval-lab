import { useCallback, useEffect, useRef, useState } from "react";
import { validAnswer } from "./contracts";
import type { Conversation, Turn } from "./types";

export const STORAGE_KEY = "izvor.conversations.v1";
export interface HistoryDocument {
  version: 2;
  conversations: Conversation[];
  deleted: Record<string, number>;
}
const empty = (): HistoryDocument => ({
  version: 2,
  conversations: [],
  deleted: {},
});
const same = (a: unknown, b: unknown) =>
  JSON.stringify(a) === JSON.stringify(b);

export function parseHistory(raw: string | null): HistoryDocument {
  let value;
  try {
    value = JSON.parse(raw || "[]");
  } catch {
    return empty();
  }
  const legacy = Array.isArray(value);
  const items = legacy
    ? value
    : value?.version === 2
      ? value.conversations
      : [];
  const conversations: Conversation[] = Array.isArray(items)
    ? items
        .filter(
          (c) =>
            c &&
            typeof c.id === "string" &&
            typeof c.title === "string" &&
            Array.isArray(c.turns),
        )
        .slice(0, 10)
        .map((c) => ({
          id: c.id,
          title: c.title,
          turns: c.turns
            .filter(
              (t: Turn) =>
                t && typeof t.id === "string" && typeof t.question === "string",
            )
            .slice(-30)
            .map((t: Turn) =>
              validAnswer(t.result)
                ? t
                : {
                    id: t.id,
                    question: t.question,
                    ...(typeof t.jobId === "string" ? { jobId: t.jobId } : {}),
                    ...(typeof t.error === "string"
                      ? { error: t.error }
                      : t.result
                        ? {
                            error:
                              "Prethodna obrada nije završena. Pošaljite pitanje ponovo.",
                          }
                        : {}),
                  },
            ),
        }))
    : [];
  const deleted: Record<string, number> = {};
  if (!legacy && value?.deleted && typeof value.deleted === "object")
    for (const [id, stamp] of Object.entries(value.deleted))
      if (typeof stamp === "number" && Number.isFinite(stamp))
        Object.defineProperty(deleted, id, {
          value: stamp,
          enumerable: true,
          configurable: true,
          writable: true,
        });
  return {
    version: 2,
    conversations: conversations.filter((c) => !Object.hasOwn(deleted, c.id)),
    deleted,
  };
}

export function mergeHistory(
  base: HistoryDocument,
  local: Conversation[],
  shared: HistoryDocument,
  restores = new Set<string>(),
): HistoryDocument {
  const deleted = { ...shared.deleted };
  const incoming = new Map(shared.conversations.map((c) => [c.id, c]));
  const previous = new Map(base.conversations.map((c) => [c.id, c]));
  const localIds = new Set(local.map((c) => c.id));
  for (const old of base.conversations)
    if (!localIds.has(old.id)) {
      Object.defineProperty(deleted, old.id, {
        value: Date.now(),
        enumerable: true,
        configurable: true,
        writable: true,
      });
      incoming.delete(old.id);
    }
  const added: string[] = [];
  for (const c of local) {
    if (Object.hasOwn(deleted, c.id) && !restores.has(c.id)) continue;
    if (restores.has(c.id)) delete deleted[c.id];
    const old = previous.get(c.id),
      remote = incoming.get(c.id);
    if (old && same(c, old) && !restores.has(c.id)) continue;
    const turns = new Map((remote?.turns || []).map((t) => [t.id, t]));
    const prior = new Map((old?.turns || []).map((t) => [t.id, t]));
    for (const t of c.turns)
      if (!remote || !same(t, prior.get(t.id))) turns.set(t.id, t);
    incoming.set(c.id, {
      id: c.id,
      title: remote?.title || c.title,
      turns: [...turns.values()].slice(-30),
    });
    if (!remote) added.push(c.id);
  }
  const ordered = [
    ...added,
    ...shared.conversations.map((c) => c.id),
    ...local.map((c) => c.id),
  ];
  return {
    version: 2,
    conversations: [...new Set(ordered)]
      .filter((id) => incoming.has(id) && !Object.hasOwn(deleted, id))
      .map((id) => incoming.get(id)!)
      .slice(0, 10),
    deleted,
  };
}

export function useHistory() {
  const [initial] = useState(() => {
    try {
      return {
        doc: parseHistory(localStorage.getItem(STORAGE_KEY)),
        failed: false,
      };
    } catch {
      return { doc: empty(), failed: true };
    }
  });
  const [conversations, render] = useState(initial.doc.conversations);
  const base = useRef(initial.doc),
    local = useRef(conversations),
    restores = useRef(new Set<string>());
  const [revision, tick] = useState(0),
    [saving, setSaving] = useState(false),
    [storageError, setError] = useState(initial.failed);
  const queued = useRef(false),
    mounted = useRef(true);
  const setConversations = useCallback(
    (value: Conversation[] | ((cs: Conversation[]) => Conversation[])) => {
      const next = typeof value === "function" ? value(local.current) : value;
      local.current = next;
      render(next);
      setSaving(true);
      tick((v) => v + 1);
    },
    [],
  );
  const markRestored = useCallback((id: string) => {
    restores.current.add(id);
  }, []);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  useEffect(() => {
    const receive = (event: StorageEvent) => {
      if (event.key === STORAGE_KEY) {
        setSaving(true);
        tick((v) => v + 1);
      }
    };
    window.addEventListener("storage", receive);
    return () => window.removeEventListener("storage", receive);
  }, []);
  useEffect(() => {
    if (!revision || queued.current) return;
    if (!navigator.locks) {
      setError(true);
      return;
    }
    queued.current = true;
    let committed = false;
    void navigator.locks
      .request("izvor.history.v1", () => {
        if (!mounted.current) return;
        const raw = localStorage.getItem(STORAGE_KEY);
        const merged = mergeHistory(
          base.current,
          local.current,
          parseHistory(raw),
          restores.current,
        );
        const encoded = JSON.stringify(merged);
        if (encoded !== raw) localStorage.setItem(STORAGE_KEY, encoded);
        base.current = merged;
        local.current = merged.conversations;
        restores.current.clear();
        render(merged.conversations);
        setSaving(false);
        setError(false);
        committed = true;
      })
      .catch(() => {
        if (mounted.current) setError(true);
      })
      .finally(() => {
        queued.current = false;
        if (
          committed &&
          mounted.current &&
          (!same(local.current, base.current.conversations) ||
            restores.current.size)
        )
          tick((v) => v + 1);
      });
  }, [revision]);
  useEffect(() => {
    if (!saving) return;
    const warn = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [saving]);
  return {
    conversations,
    setConversations,
    markRestored,
    storageError,
    saving,
  };
}
