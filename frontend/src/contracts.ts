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
    (v.translated_text === undefined ||
      typeof v.translated_text === "string") &&
    (v.score === undefined ||
      (typeof v.score === "number" && Number.isFinite(v.score)))
  );
}

export function validAnswer(v: unknown): v is Answer {
  return (
    record(v) &&
    fields(v, ["question", "answer", "created_at"]) &&
    (v.language === undefined || v.language === "en" || v.language === "sr") &&
    (v.translation_review_status === undefined ||
      v.translation_review_status === null ||
      typeof v.translation_review_status === "string") &&
    typeof v.refused === "boolean" &&
    ["current", "offline", "baseline", "verified"].includes(
      String(v.profile),
    ) &&
    (v.fallback === null || typeof v.fallback === "string") &&
    number(v.seconds) &&
    arrayOf(v.citations, validChunk) &&
    arrayOf(v.retrieved, validChunk) &&
    arrayOf(v.trace, (x) => record(x) && typeof x.stage === "string") &&
    (v.quality === undefined ||
      (record(v.quality) &&
        fields(v.quality, ["version", "caveat"]) &&
        count(v.quality.risk_count) &&
        count(v.quality.review_count) &&
        arrayOf(
          v.quality.claims,
          (c) =>
            record(c) &&
            fields(c, ["text", "status"]) &&
            strings(c.citations) &&
            strings(c.reasons),
        ) &&
        arrayOf(
          v.quality.completeness,
          (p) =>
            record(p) &&
            typeof p.part === "string" &&
            typeof p.present === "boolean",
        ))) &&
    (v.usage === undefined ||
      (record(v.usage) &&
        record(v.usage.requests) &&
        record(v.usage.cache_hits) &&
        ["embeddings", "llm"].every(
          (k) =>
            count(
              (v.usage as RecordValue).requests &&
                ((v.usage as RecordValue).requests as RecordValue)[k],
            ) && count(((v.usage as RecordValue).cache_hits as RecordValue)[k]),
        ) &&
        (v.usage.prompt_tokens === null || count(v.usage.prompt_tokens)) &&
        (v.usage.output_tokens === null || count(v.usage.output_tokens)) &&
        number(v.usage.model_seconds) &&
        (v.usage.phases === undefined ||
          arrayOf(
            v.usage.phases,
            (p) =>
              record(p) && typeof p.stage === "string" && number(p.seconds),
          )))) &&
    (v.provenance === undefined || record(v.provenance)) &&
    (v.clarification === undefined || strings(v.clarification)) &&
    (v.disposition === undefined || typeof v.disposition === "string") &&
    (v.retrieval_question === undefined ||
      typeof v.retrieval_question === "string")
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
  if (path === "/jobs" || path.startsWith("/jobs/"))
    return (
      typeof v.id === "string" &&
      [
        "queued",
        "running",
        "cancelling",
        "completed",
        "cancelled",
        "failed",
      ].includes(String(v.status)) &&
      record(v.progress) &&
      fields(v.progress, ["stage", "message"]) &&
      number(v.seconds) &&
      (v.error === null || typeof v.error === "string") &&
      (v.status === "completed"
        ? validAnswer(v.result) ||
          (record(v.result) &&
            v.result.kind === "comparison" &&
            Array.isArray(v.result.results) &&
            arrayOf(v.result.results, validAnswer) &&
            v.result.results.length === 2 &&
            record(v.result.differences) &&
            ["answer", "citations", "refused"].every(
              (k) =>
                typeof ((v.result as RecordValue).differences as RecordValue)[
                  k
                ] === "boolean",
            ))
        : v.result === null) &&
      arrayOf(
        v.phases,
        (p) => record(p) && typeof p.stage === "string" && number(p.seconds),
      )
    );
  if (path === "/documents") return arrayOf(v.documents, validDocument);
  if (path === "/workspace")
    return (
      arrayOf(
        v.documents,
        (x) =>
          record(x) &&
          fields(x, [
            "doc_id",
            "title",
            "section",
            "version",
            "status",
            "text",
            "origin",
            "source_sha256",
          ]) &&
          typeof x.active === "boolean",
      ) &&
      arrayOf(
        v.warnings,
        (x) => record(x) && typeof x.doc_id === "string" && strings(x.reasons),
      ) &&
      arrayOf(
        v.conflicts,
        (c) =>
          record(c) &&
          strings(c.documents) &&
          strings(c.evidence) &&
          fields(c, ["title", "reason"]),
      ) &&
      arrayOf(
        v.feedback,
        (f) =>
          record(f) &&
          fields(f, [
            "id",
            "label",
            "comment",
            "answer_sha256",
            "created_at",
          ]) &&
          validAnswer(f.answer),
      ) &&
      arrayOf(v.jobs, (j) => validApiPayload("/jobs", j)) &&
      typeof v.note === "string"
    );
  if (path === "/library/preview" || path === "/library/update")
    return (
      record(v.document) &&
      fields(v.document, ["doc_id", "title", "text"]) &&
      typeof v.document.active === "boolean"
    );
  if (path === "/library/compare")
    return (
      record(v.left) &&
      record(v.right) &&
      typeof v.diff === "string" &&
      typeof v.note === "string"
    );
  if (path === "/feedback")
    return (
      record(v.feedback) &&
      fields(v.feedback, ["id", "answer_sha256", "created_at"])
    );
  if (path === "/status")
    return (
      typeof v.ollama === "boolean" &&
      strings(v.models) &&
      strings(v.required_models) &&
      count(v.documents) &&
      count(v.current_documents)
    );
  if (
    path === "/evaluations" ||
    path === "/evaluations/run" ||
    path === "/evaluations/baseline"
  ) {
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
