import { useState } from "react";
import { api } from "./api";
import type { Answer } from "./types";

export function AnswerQuality({ answer }: { answer: Answer }) {
  const [label, setLabel] = useState("incorrect"),
    [comment, setComment] = useState(""),
    [message, setMessage] = useState(""),
    [saving, setSaving] = useState(false);
  async function save() {
    setSaving(true);
    setMessage("");
    try {
      await api("/feedback", { label, comment, answer });
      setMessage("Ocena je sačuvana lokalno, uz tačan odgovor i izvore.");
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setSaving(false);
    }
  }
  return (
    <details className="quality-details">
      <summary>Provera tvrdnji i ocena odgovora</summary>
      {answer.quality ? (
        <>
          <p>{answer.quality.caveat}</p>
          <p>
            <strong>{answer.quality.risk_count}</strong> rizičnih tvrdnji ·{" "}
            <strong>{answer.quality.review_count}</strong> zahteva pregled
          </p>
          <ul>
            {answer.quality.claims.map((c, i) => (
              <li key={i}>
                <span className="meta-label">
                  {c.status === "literal"
                    ? "Prepisan izvor"
                    : c.status === "risk"
                      ? "Upozorenje"
                      : "Potreban pregled"}
                </span>{" "}
                {c.text}
                {c.reasons.length > 0 && (
                  <small> — {c.reasons.join(", ")}</small>
                )}
              </li>
            ))}
          </ul>
          {answer.quality.completeness.map((p) => (
            <p key={p.part}>
              {p.part === "location" ? "Lokacija" : "Trajanje"}:{" "}
              {p.present
                ? "prisutno u glavnom odgovoru"
                : "nije pronađeno u glavnom odgovoru"}
            </p>
          ))}
        </>
      ) : (
        <p>Istorijski odgovor nema novi audit. Ponovite pitanje za pregled.</p>
      )}
      {answer.usage && (
        <p>
          Pozivi: embeddings {answer.usage.requests.embeddings}, LLM{" "}
          {answer.usage.requests.llm} · Cache hits:{" "}
          {answer.usage.cache_hits.embeddings + answer.usage.cache_hits.llm}.
          Tokeni upit/odgovor: {answer.usage.prompt_tokens ?? "nepoznato"} /{" "}
          {answer.usage.output_tokens ?? "nepoznato"}. Model:{" "}
          {answer.usage.model_seconds.toFixed(2)} s.
        </p>
      )}
      {answer.retrieval_question &&
        answer.retrieval_question !== answer.question && (
          <p>
            Pretraga: <code>{answer.retrieval_question}</code>
          </p>
        )}
      {answer.usage?.phases && (
        <details>
          <summary>Vreme po fazama</summary>
          <ul>
            {answer.usage.phases.map((p, i) => (
              <li key={i}>
                {p.stage}: {p.seconds.toFixed(3)} s
              </li>
            ))}
          </ul>
        </details>
      )}
      {answer.provenance && (
        <details>
          <summary>Poreklo odgovora i podešavanja</summary>
          <pre>{JSON.stringify(answer.provenance, null, 2)}</pre>
        </details>
      )}
      <div className="work-fields">
        <label>
          Vrsta ocene
          <select value={label} onChange={(e) => setLabel(e.target.value)}>
            <option value="incorrect">Netačan odgovor</option>
            <option value="incomplete">Nepotpun odgovor</option>
            <option value="wrong_citation">Pogrešan citat</option>
            <option value="reviewed">Pregledao/la sam odgovor</option>
          </select>
        </label>
        <label>
          Komentar
          <textarea
            maxLength={4000}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Šta treba proveriti ili ispraviti?"
          />
        </label>
      </div>
      <button
        className="work-button"
        disabled={saving}
        onClick={() => void save()}
      >
        {saving ? "Čuvanje…" : "Sačuvaj lokalnu ocenu"}
      </button>
      <p role="status">{message}</p>
    </details>
  );
}
