import { useEffect, useState } from "react";
import {
  ArrowDownToLine,
  ArrowRight,
  Check,
  CircleAlert,
  FlaskConical,
  LoaderCircle,
  RefreshCw,
  X,
} from "lucide-react";
import { api, download } from "./api";
import type { Evaluation, EvalRow } from "./types";

const labels: Record<string, string> = {
  eval: "Obavezni skup",
  holdout: "Holdout",
  test1: "Dodatni test 1",
  test2: "Dodatni test 2",
};
const pct = (v: number) => `${Math.round(v * 100)}%`;
function failureReasons(row: EvalRow) {
  return [
    !row.behaviour_correct && "Pogrešna odluka o odgovaranju.",
    row.retrieval_hit === false && "Očekivani izvor nije pronađen.",
    row.fact_in_citations === false &&
      "Tražena činjenica nije pronađena u citatima.",
    typeof row.citation_precision === "number" &&
      row.citation_precision < 1 &&
      "Citati uključuju dokument koji se ne očekuje.",
  ].filter(Boolean) as string[];
}

export function EvaluationView() {
  const [data, setData] = useState<Evaluation | null>(null);
  const [set, setSet] = useState("eval");
  const [onlyFailures, setOnlyFailures] = useState(false);
  const [selected, setSelected] = useState<EvalRow | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  async function load(baseline = false) {
    setLoading(true);
    setError("");
    try {
      setData(
        await api<Evaluation>(
          baseline ? "/evaluations/baseline" : "/evaluations",
        ),
      );
      setSelected(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, []);
  async function replay() {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      setData(await api<Evaluation>("/evaluations/run", {}));
      setSelected(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const run = data?.runs[set];
  const summary = run?.summary;
  const rows = run?.results.filter((r) => !onlyFailures || !r.pass) || [];
  const selectedIndex =
    run?.results.findIndex((r) => r.id === selected?.id) ?? -1;
  const selectedAnswer = run?.answers[selectedIndex];
  const totals = data
    ? Object.values(data.runs).reduce(
        (all, r) => ({
          passed: all.passed + (r.summary?.passed || 0),
          total: all.total + (r.summary?.total || 0),
        }),
        { passed: 0, total: 0 },
      )
    : null;
  return (
    <div className="content-page evaluation-page">
      <div className="work-tabs">
        <button disabled={busy || loading} onClick={() => void load()}>
          Aktuelno merenje
        </button>
        <button disabled={busy || loading} onClick={() => void load(true)}>
          Polazno merenje 98/102
        </button>
      </div>
      <div className="page-heading">
        <div>
          <h1>Kvalitet koji može da se proveri.</h1>
          <p>Četiri skupa pitanja. Stvarni rezultati. Vidljive regresije.</p>
        </div>
        <button
          className="primary-button"
          disabled={busy || loading}
          onClick={replay}
        >
          {busy ? (
            <LoaderCircle size={17} className="spin" />
          ) : (
            <RefreshCw size={17} />
          )}{" "}
          {busy ? "Provera je u toku…" : "Ponovi iz keša"}
        </button>
      </div>
      {error && (
        <div className="error-notice" role="alert">
          <CircleAlert size={18} />
          <span>{error}</span>
          <button onClick={() => void load()}>Pokušaj ponovo</button>
        </div>
      )}
      {loading ? (
        <div className="loading-page" role="status">
          <LoaderCircle size={24} className="spin" /> Učitavam rezultate…
        </div>
      ) : (
        data && (
          <>
            <div className="evaluation-provenance">
              <FlaskConical size={23} />
              <div>
                <strong>
                  {data.origin === "replayed"
                    ? "Ponovljena evaluacija iz keša"
                    : data.origin === "baseline"
                      ? "Polazno merenje pre unapređenja"
                      : "Sačuvana evaluacija iz keša"}
                </strong>
                <p>
                  {new Date(data.created_at).toLocaleString("sr-Latn-RS")} ·
                  commit {data.revision.slice(0, 7)} · {totals?.passed}/
                  {totals?.total} ukupno
                  {data.git_dirty ? " · radna kopija izmenjena" : ""}
                </p>
              </div>
              <button
                className="icon-button"
                onClick={() =>
                  download(
                    "izvor-evaluacija.json",
                    JSON.stringify(data, null, 2),
                    "application/json",
                  )
                }
                title="Preuzmi rezultate"
                aria-label="Preuzmi evaluaciju"
              >
                <ArrowDownToLine size={19} />
              </button>
            </div>
            <p className="evaluation-caveat">
              Ovo je ponavljanje sa prethodno sačuvanim izlazima modela, bez
              novog generisanja. Rezultati malih skupova ne dokazuju opštu
              tačnost sistema.
            </p>
            <div
              className="eval-sets"
              role="tablist"
              aria-label="Evaluacioni skupovi"
            >
              {Object.entries(data.runs).map(([key, value]) => (
                <button
                  role="tab"
                  aria-selected={set === key}
                  key={key}
                  onClick={() => {
                    setSet(key);
                    setSelected(null);
                  }}
                >
                  <span>{labels[key] || key}</span>
                  <strong>
                    {value.summary
                      ? `${value.summary.passed}/${value.summary.total}`
                      : "Greška"}
                  </strong>
                  <div className="score-track">
                    <div
                      style={{
                        width: `${value.summary ? (value.summary.passed / value.summary.total) * 100 : 0}%`,
                      }}
                    />
                  </div>
                </button>
              ))}
            </div>
            {summary && (
              <div className="metric-strip">
                <div>
                  <span>Tačno ponašanje</span>
                  <strong>{pct(summary.behaviour_accuracy)}</strong>
                </div>
                <div>
                  <span>Pogodak izvora</span>
                  <strong>{pct(summary.retrieval_hit_rate)}</strong>
                </div>
                <div>
                  <span>Preciznost citata</span>
                  <strong>{pct(summary.mean_citation_precision)}</strong>
                </div>
                <div>
                  <span>Rezervni odgovori</span>
                  <strong>{run?.fallback_count ?? 0}</strong>
                </div>
              </div>
            )}
            {run?.error && (
              <div role="alert" className="error-notice">
                {run.error.message}
              </div>
            )}
            <div className="table-heading">
              <h2>
                Pitanja i rezultati <span>{labels[set]}</span>
              </h2>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={onlyFailures}
                  onChange={(e) => setOnlyFailures(e.target.checked)}
                />
                Samo neuspešni
              </label>
            </div>
            <div className="results-layout">
              <div className="results-table-wrap">
                <table className="results-table">
                  <thead>
                    <tr>
                      <th>Pitanje</th>
                      <th>Rezultat</th>
                      <th>Ponašanje</th>
                      <th>Citati</th>
                      <th>
                        <span className="sr-only">Detalji</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row) => (
                      <tr
                        className={selected?.id === row.id ? "selected" : ""}
                        key={row.id}
                      >
                        <td>
                          <button
                            className="table-question"
                            onClick={() => setSelected(row)}
                          >
                            <strong>{row.id}</strong>
                            <span>
                              {run?.answers[run.results.indexOf(row)]
                                ?.question || String(row.category || "")}
                            </span>
                          </button>
                        </td>
                        <td>
                          <span
                            className={row.pass ? "result-pass" : "result-fail"}
                          >
                            {row.pass ? <Check size={14} /> : <X size={14} />}{" "}
                            {row.pass ? "Prošao" : "Neuspešan"}
                          </span>
                        </td>
                        <td>{row.behaviour_correct ? "Tačno" : "Netačno"}</td>
                        <td>{row.cited_chunk_ids?.length ?? 0}</td>
                        <td>
                          <button
                            className="icon-button"
                            aria-label={`Detalji ${row.id}`}
                            onClick={() => setSelected(row)}
                          >
                            <ArrowRight size={16} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!rows.length && (
                  <div className="empty-results">
                    <Check size={25} />
                    <p>Nema neuspešnih pitanja u ovom skupu.</p>
                  </div>
                )}
              </div>
              {selected && (
                <section className="eval-detail">
                  <div className="detail-heading">
                    <span className="muted">
                      {selected.id} · {String(selected.category || "")}
                    </span>
                    <button
                      className="icon-button"
                      onClick={() => setSelected(null)}
                      aria-label="Zatvori detalje evaluacije"
                    >
                      <X size={18} />
                    </button>
                  </div>
                  <h3>{selectedAnswer?.question}</h3>
                  <p>{selectedAnswer?.answer.split(/\nSource \[/)[0]}</p>
                  {!selected.pass && (
                    <div className="failure-explanation">
                      <strong>Zašto nije prošlo</strong>
                      {failureReasons(selected).map((reason) => (
                        <p key={reason}>{reason}</p>
                      ))}
                    </div>
                  )}
                  <dl>
                    <dt>Očekivano</dt>
                    <dd>
                      {selected.expected === "answer" ? "Odgovor" : "Odbijanje"}
                    </dd>
                    <dt>Dobijeno</dt>
                    <dd>
                      {selected.got === "answer" ? "Odgovor" : "Odbijanje"}
                    </dd>
                    <dt>Preciznost citata</dt>
                    <dd>
                      {typeof selected.citation_precision === "number"
                        ? pct(selected.citation_precision)
                        : "—"}
                    </dd>
                  </dl>
                  <h4>Korišćeni citati</h4>
                  {selected.cited_chunk_ids?.length ? (
                    selected.cited_chunk_ids.map((id) => (
                      <code key={id}>{id}</code>
                    ))
                  ) : (
                    <p className="muted">Bez citata.</p>
                  )}
                </section>
              )}
            </div>
            <details className="fingerprint">
              <summary>Identitet skupa i ponovljivost</summary>
              <p>
                Preciznost citata meri pripadnost očekivanom dokumentu; ne
                potvrđuje tačnost svake rečenice odgovora.
              </p>
              <p>
                Originalna pitanja i kod za metrike nisu menjani. Poređenje
                koristi iste skupove pitanja.
              </p>
              <code>SHA-256: {data.question_set_sha256[set]}</code>
              <p>
                Režim: {data.mode}. Pozivi pri ovoj evaluaciji:{" "}
                {data.requests.embeddings ?? 0} embeddings,{" "}
                {data.requests.llm ?? 0} LLM.
              </p>
            </details>
          </>
        )
      )}
    </div>
  );
}
