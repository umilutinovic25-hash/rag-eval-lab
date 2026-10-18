import type { Answer, Chunk } from "./types";

type RecordValue = Record<string, unknown>;
const record = (v: unknown): v is RecordValue =>
  !!v && typeof v === "object" && !Array.isArray(v);
const strings = (v: unknown): v is string[] =>
  Array.isArray(v) && v.every((x) => typeof x === "string");
const number = (v: unknown): v is number =>
  typeof v === "number" && Number.isFinite(v) && v >= 0;
const count = (v: unknown) => number(v) && Number.isInteger(v);
const ratio = (v: unknown) => number(v) && v <= 1;
const fields = (v: RecordValue, keys: string[]) =>
  keys.every((k) => typeof v[k] === "string");
const arrayOf = (v: unknown, check: (x: unknown) => boolean) =>
  Array.isArray(v) && v.every(check);

export function validChunk(v: unknown): v is Chunk {
  return (
    record(v) &&
    fields(v, ["chunk_id", "doc_id", "title", "version", "status", "text"]) &&
    (v.score === undefined ||
      (typeof v.score === "number" && Number.isFinite(v.score)))
  );
}

export function validAnswer(v: unknown): v is Answer {
  return (
    record(v) &&
    fields(v, ["question", "answer", "created_at"]) &&
    typeof v.refused === "boolean" &&
    (v.profile === "current" || v.profile === "offline") &&
    (v.fallback === null || typeof v.fallback === "string") &&
    number(v.seconds) &&
    arrayOf(v.citations, validChunk) &&
    arrayOf(v.retrieved, validChunk) &&
    arrayOf(v.trace, (x) => record(x) && typeof x.stage === "string")
  );
}

function validDocument(v: unknown) {
  return (
    record(v) &&
    fields(v, ["doc_id", "title", "section", "version", "status", "text"]) &&
    arrayOf(v.chunks, validChunk)
  );
}

function validRun(v: unknown) {
  if (
    !record(v) ||
    !fields(v, ["status"]) ||
    !count(v.fallback_count) ||
    !number(v.seconds)
  )
    return false;
  const summary = v.summary;
  if (
    summary !== null &&
    !(
      record(summary) &&
      count(summary.total) &&
      count(summary.passed) &&
      Number(summary.passed) <= Number(summary.total) &&
      [
        "behaviour_accuracy",
        "retrieval_hit_rate",
        "mean_citation_precision",
      ].every((k) => ratio(summary[k]))
    )
  )
    return false;
  return (
    (v.error === null ||
      (record(v.error) && typeof v.error.message === "string")) &&
    arrayOf(
      v.results,
      (r) =>
        record(r) &&
        typeof r.id === "string" &&
        typeof r.pass === "boolean" &&
        typeof r.behaviour_correct === "boolean" &&
        (r.citation_precision === null || ratio(r.citation_precision)) &&
        strings(r.cited_chunk_ids),
    ) &&
    arrayOf(
      v.answers,
      (a) =>
        record(a) &&
        fields(a, ["question", "answer"]) &&
        strings(a.citations) &&
        typeof a.refused === "boolean" &&
        (a.fallback === null || typeof a.fallback === "string"),
    )
  );
}

export function validApiPayload(path: string, v: unknown): boolean {
  if (path === "/chat") return validAnswer(v);
  if (!record(v)) return false;
  if (path === "/documents") return arrayOf(v.documents, validDocument);
  if (path === "/status")
    return (
      typeof v.ollama === "boolean" &&
      strings(v.models) &&
      strings(v.required_models) &&
      count(v.documents) &&
      count(v.current_documents)
    );
  if (path === "/evaluations" || path === "/evaluations/run") {
    const runs = v.runs;
    return (
      fields(v, ["origin", "mode", "created_at", "revision", "status"]) &&
      record(v.question_set_sha256) &&
      Object.values(v.question_set_sha256).every(
        (h) => typeof h === "string",
      ) &&
      record(v.requests) &&
      Object.values(v.requests).every(count) &&
      record(runs) &&
      ["eval", "holdout", "test1", "test2"].every((k) => validRun(runs[k])) &&
      Object.values(runs).every(validRun)
    );
  }
  return true;
}
