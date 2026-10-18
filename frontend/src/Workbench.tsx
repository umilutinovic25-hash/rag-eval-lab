import { useEffect, useState } from "react";
import { api, download } from "./api";
import { AnswerQuality } from "./Quality";
import { validAnswer } from "./contracts";
import { createBackup, readBackup, mergeBackup } from "./backup";
import type {
  Comparison,
  Conversation,
  Filters,
  Job,
  LibraryDocument,
  Profile,
  WorkspaceData,
} from "./types";

export function FilterFields({
  documents,
  value,
  onChange,
}: {
  documents: Pick<LibraryDocument, "doc_id" | "title" | "section">[];
  value: Filters;
  onChange: (f: Filters) => void;
}) {
  return (
    <div className="work-fields filters">
      <label>
        Tema
        <select
          value={value.topic || ""}
          onChange={(e) =>
            onChange({ ...value, topic: e.target.value, doc_ids: [] })
          }
        >
          <option value="">Sve teme</option>
          {[...new Set(documents.map((d) => d.section))].map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </label>
      <label>
        Dokument
        <select
          value={value.doc_ids?.[0] || ""}
          onChange={(e) =>
            onChange({
              ...value,
              doc_ids: e.target.value ? [e.target.value] : [],
            })
          }
        >
          <option value="">Svi dokumenti</option>
          {documents
            .filter((d) => !value.topic || d.section === value.topic)
            .map((d) => (
              <option key={d.doc_id} value={d.doc_id}>
                {d.title} · {d.doc_id}
              </option>
            ))}
        </select>
      </label>
      <label>
        Važi na datum
        <input
          type="date"
          value={value.as_of || ""}
          onChange={(e) => onChange({ ...value, as_of: e.target.value })}
        />
      </label>
      <label className="check-label">
        <input
          type="checkbox"
          checked={value.sandbox || false}
          onChange={(e) => onChange({ ...value, sandbox: e.target.checked })}
        />{" "}
        Uključi aktivne lokalne dokumente
      </label>
    </div>
  );
}

function Dates({
  doc,
  onSave,
}: {
  doc: LibraryDocument;
  onSave: (changes: Record<string, unknown>) => void;
}) {
  const [published, setPublished] = useState(doc.published_on || ""),
    [start, setStart] = useState(doc.effective_from || ""),
    [end, setEnd] = useState(doc.effective_until || "");
  return (
    <details>
      <summary>Datumi i aktivacija · {doc.doc_id}</summary>
      <div className="work-fields">
        <label>
          Datum objave
          <input
            type="date"
            value={published}
            onChange={(e) => setPublished(e.target.value)}
          />
        </label>
        <label>
          Važi od
          <input
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
          />
        </label>
        <label>
          Važi do (uključivo)
          <input
            type="date"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
          />
        </label>
      </div>
      <button
        className="work-button"
        onClick={() =>
          onSave({
            published_on: published || null,
            effective_from: start || null,
            effective_until: end || null,
          })
        }
      >
        Sačuvaj datume
      </button>
      {doc.origin === "sandbox" && (
        <button
          className="work-button"
          disabled={doc.quarantined}
          onClick={() => onSave({ active: !doc.active })}
        >
          {doc.quarantined
            ? "Karantin"
            : doc.active
              ? "Deaktiviraj dokument"
              : "Aktiviraj dokument"}
        </button>
      )}
    </details>
  );
}

export function Workbench({
  conversations,
  onImport,
}: {
  conversations: Conversation[];
  onImport: (cs: Conversation[]) => void;
}) {
  const [tab, setTab] = useState("library"),
    [data, setData] = useState<WorkspaceData | null>(null),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [loading, setLoading] = useState(false);
  const [filename, setFilename] = useState("policy.md"),
    [content, setContent] = useState(""),
    [title, setTitle] = useState(""),
    [section, setSection] = useState("Sandbox"),
    [version, setVersion] = useState("v1"),
    [preview, setPreview] = useState<LibraryDocument | null>(null);
  const [left, setLeft] = useState("hb-02"),
    [right, setRight] = useState("hb-03"),
    [diff, setDiff] = useState<{
      left: LibraryDocument;
      right: LibraryDocument;
      diff: string;
      note: string;
    } | null>(null);
  const [question, setQuestion] = useState(
      "Is the training budget per team or per person?",
    ),
    [profiles, setProfiles] = useState<Profile[]>(["baseline", "current"]),
    [filters, setFilters] = useState<Filters>({}),
    [comparison, setComparison] = useState<Comparison | null>(null),
    [job, setJob] = useState<Job | null>(null);
  const [incoming, setIncoming] = useState<Conversation[] | null>(null);
  const answers = data?.jobs.map((j) => j.result).filter(validAnswer) ?? [];
  async function refresh() {
    setError("");
    try {
      setData(await api<WorkspaceData>("/workspace"));
    } catch (e) {
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    void refresh();
  }, []);
  async function action(fn: () => Promise<void>) {
    setLoading(true);
    setError("");
    setNotice("");
    try {
      await fn();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }
  async function update(
    doc: LibraryDocument,
    changes: Record<string, unknown>,
  ) {
    await action(async () => {
      await api("/library/update", { doc_id: doc.doc_id, changes });
      setNotice("Promena dokumenta je sačuvana.");
      await refresh();
    });
  }
  async function compare() {
    await action(async () => {
      setComparison(null);
      let current = await api<Job>("/jobs", {
        kind: "comparison",
        question,
        language: "en",
        profiles,
        filters,
      });
      for (;;) {
        setJob(current);
        if (current.status === "completed") {
          setComparison(current.result as unknown as Comparison);
          break;
        }
        if (["failed", "cancelled"].includes(current.status))
          throw new Error(current.error || "Poređenje je otkazano.");
        await new Promise((r) => setTimeout(r, 300));
        current = await api<Job>(`/jobs/${current.id}`);
      }
      await refresh();
    });
  }
  return (
    <section className="workbench">
      <header className="section-intro">
        <p className="eyebrow">LOKALNA RADIONICA</p>
        <h1>Dokazi pre zaključka.</h1>
        <p>
          Biblioteka, poređenje konfiguracija i pregled kvaliteta na jednom
          mestu. Originalni zadatak ostaje sačuvan.
        </p>
      </header>
      <div className="work-tabs" role="tablist" aria-label="Radionica">
        {[
          ["library", "Biblioteka"],
          ["compare", "Eksperimenti"],
          ["quality", "Kvalitet i poslovi"],
          ["backup", "Backup razgovora"],
        ].map(([id, label]) => (
          <button
            role="tab"
            aria-selected={tab === id}
            key={id}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </div>
      {error && (
        <p className="work-alert" role="alert">
          {error}
        </p>
      )}
      {notice && (
        <p role="status" className="work-notice">
          {notice}
        </p>
      )}
      <div role="tabpanel">
        {tab === "library" && (
          <>
            <div className="work-grid">
              <article className="work-card">
                <h2>Unesi novi izvor</h2>
                <p>
                  TXT, MD ili JSON, do 256 kB. Pregled ne aktivira dokument.
                  Sadržaj se čuva samo na ovom računaru.
                </p>
                <label className="file-label">
                  Izaberi dokument
                  <input
                    type="file"
                    accept=".txt,.md,.json"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file)
                        void action(async () => {
                          if (file.size > 256000)
                            throw new Error("Dokument je veći od 256 kB.");
                          setFilename(file.name);
                          setContent(await file.text());
                          setPreview(null);
                        });
                    }}
                  />
                </label>
                <div className="work-fields">
                  <label>
                    Naziv datoteke
                    <input
                      value={filename}
                      onChange={(e) => setFilename(e.target.value)}
                    />
                  </label>
                  <label>
                    Naslov
                    <input
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                    />
                  </label>
                  <label>
                    Tema
                    <input
                      value={section}
                      onChange={(e) => setSection(e.target.value)}
                    />
                  </label>
                  <label>
                    Verzija
                    <input
                      value={version}
                      onChange={(e) => setVersion(e.target.value)}
                    />
                  </label>
                </div>
                <label>
                  Tekst dokumenta
                  <textarea
                    rows={7}
                    value={content}
                    maxLength={256000}
                    onChange={(e) => setContent(e.target.value)}
                  />
                </label>
                <button
                  className="work-button primary"
                  disabled={loading || !content.trim()}
                  onClick={() =>
                    void action(async () => {
                      const p = await api<{ document: LibraryDocument }>(
                        "/library/preview",
                        {
                          filename,
                          content,
                          metadata: {
                            ...(title ? { title } : {}),
                            section,
                            version,
                          },
                        },
                      );
                      setPreview(p.document);
                      await refresh();
                    })
                  }
                >
                  Napravi pregled
                </button>
                {preview && (
                  <div className="work-preview">
                    <h3>{preview.title}</h3>
                    <p>
                      {preview.quarantined
                        ? "Instrukcije su sumnjive: dokument je u karantinu."
                        : "Pregled je sačuvan kao neaktivan dokument. Aktivirajte ga u biblioteci."}
                    </p>
                    <pre>{preview.text}</pre>
                  </div>
                )}
              </article>
              <article className="work-card">
                <h2>Zdravlje biblioteke</h2>
                <p>{data?.note}</p>
                <p>
                  <strong>{data?.documents.length ?? "—"}</strong> izvora ·{" "}
                  <strong>{data?.warnings.length ?? "—"}</strong> izvora sa
                  upozorenjima ·{" "}
                  <strong>{data?.conflicts.length ?? "—"}</strong> mogućih
                  sukoba
                </p>
                <button className="work-button" onClick={() => void refresh()}>
                  Osveži biblioteku
                </button>
                {data?.conflicts.map((c, i) => (
                  <div className="work-alert" key={i}>
                    <h3>{c.title}</h3>
                    <p>
                      Mogući sukob: {c.documents.join(" / ")}. Potreban pregled
                      osobe odgovorne za politiku.
                    </p>
                    {c.evidence.map((e, j) => (
                      <blockquote key={j}>{e}</blockquote>
                    ))}
                  </div>
                ))}
                <details>
                  <summary>Upozorenja po dokumentu</summary>
                  <ul>
                    {data?.warnings.map((w) => (
                      <li key={w.doc_id}>
                        <strong>{w.doc_id}</strong>: {w.reasons.join(", ")}
                      </li>
                    ))}
                  </ul>
                </details>
              </article>
            </div>
            <article className="work-card">
              <h2>Verzije politika</h2>
              <div className="work-fields">
                {[
                  ["Prethodna verzija", left, setLeft],
                  ["Nova verzija", right, setRight],
                ].map(([label, value, setter]) => (
                  <label key={String(label)}>
                    {String(label)}
                    <select
                      value={String(value)}
                      onChange={(e) =>
                        (setter as (v: string) => void)(e.target.value)
                      }
                    >
                      {data?.documents.map((d) => (
                        <option key={d.doc_id} value={d.doc_id}>
                          {d.title} · {d.version} · {d.doc_id}
                        </option>
                      ))}
                    </select>
                  </label>
                ))}
              </div>
              <button
                className="work-button"
                disabled={loading || left === right}
                onClick={() =>
                  void action(async () =>
                    setDiff(await api("/library/compare", { left, right })),
                  )
                }
              >
                Uporedi verzije
              </button>
              {diff && (
                <>
                  <p>{diff.note}</p>
                  <div className="work-grid">
                    {[diff.left, diff.right].map((d) => (
                      <blockquote key={d.doc_id}>
                        <strong>
                          {d.title} · {d.version} · {d.status}
                        </strong>
                        <p>{d.text}</p>
                        <small>
                          [{d.doc_id}] ·{" "}
                          {d.effective_from ?? "početak nepoznat"} —{" "}
                          {d.effective_until ?? "kraj nepoznat"}
                        </small>
                      </blockquote>
                    ))}
                  </div>
                  <pre>{diff.diff}</pre>
                </>
              )}
            </article>
            <article className="work-card">
              <h2>Izvori i metapodaci</h2>
              {data?.documents.map((d) => (
                <div className="library-row" key={d.doc_id}>
                  <h3>
                    {d.title}{" "}
                    <small>
                      {d.version} ·{" "}
                      {d.origin === "handbook" ? "Priručnik" : "Lokalni unos"} ·{" "}
                      {d.status} · {d.active ? "aktivan" : "neaktivan"}
                    </small>
                  </h3>
                  <Dates
                    doc={d}
                    onSave={(changes) => void update(d, changes)}
                  />
                </div>
              ))}
            </article>
          </>
        )}
        {tab === "compare" && (
          <article className="work-card">
            <h2>Isto pitanje. Dve konfiguracije.</h2>
            <p>
              Baseline čuva prethodno ponašanje. Aktuelni profil uključuje nova
              pravila dokaza. Provereni profil vezuje keš za digest modela i
              može zahtevati nove lokalne pozive. Engleski upit koristi
              originalne izvore.
            </p>
            <label>
              Pitanje za poređenje
              <textarea
                maxLength={2000}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
              />
            </label>
            <div className="work-fields">
              {[0, 1].map((i) => (
                <label key={i}>
                  Konfiguracija {i + 1}
                  <select
                    value={profiles[i]}
                    onChange={(e) =>
                      setProfiles((ps) =>
                        ps.map((p, j) =>
                          i === j ? (e.target.value as Profile) : p,
                        ),
                      )
                    }
                  >
                    <option value="baseline">Baseline</option>
                    <option value="current">Aktuelni</option>
                    <option value="offline">Bez modela</option>
                    <option value="verified">Digest proveren</option>
                  </select>
                </label>
              ))}
            </div>
            <FilterFields
              documents={data?.documents ?? []}
              value={filters}
              onChange={setFilters}
            />
            <button
              className="work-button primary"
              disabled={
                loading || !question.trim() || profiles[0] === profiles[1]
              }
              onClick={() => void compare()}
            >
              Uporedi konfiguracije
            </button>
            {loading && job && (
              <>
                <p role="status">{job.progress.message}</p>
                <button
                  className="work-button"
                  onClick={() =>
                    void api(`/jobs/${job.id}/cancel`, {}).catch((e) =>
                      setError((e as Error).message),
                    )
                  }
                >
                  Otkaži poređenje
                </button>
              </>
            )}
            {comparison && (
              <>
                <p>
                  Razlike — odgovor:{" "}
                  {comparison.differences.answer ? "da" : "ne"} · citati:{" "}
                  {comparison.differences.citations ? "da" : "ne"} · odbijanje:{" "}
                  {comparison.differences.refused ? "da" : "ne"}
                </p>
                <div className="work-grid">
                  {comparison.results.map((a) => (
                    <article className="comparison-answer" key={a.profile}>
                      <h3>
                        {a.profile} · {a.seconds.toFixed(2)} s
                      </h3>
                      <p>{a.answer}</p>
                      <ul>
                        {a.citations.map((c) => (
                          <li key={c.chunk_id}>
                            <strong>[{c.chunk_id}]</strong> {c.text}
                          </li>
                        ))}
                      </ul>
                      <AnswerQuality answer={a} />
                    </article>
                  ))}
                </div>
                <button
                  className="work-button"
                  onClick={() =>
                    download(
                      "izvor-poredjenje.json",
                      JSON.stringify(comparison, null, 2),
                      "application/json",
                    )
                  }
                >
                  Izvezi poređenje
                </button>
              </>
            )}
          </article>
        )}
        {tab === "quality" && (
          <>
            <article className="work-card">
              <h2>Lokalni pregled kvaliteta</h2>
              <p>
                Ljudske ocene se ne generišu automatski. Zapisi sadrže tačan
                odgovor, izvore, konfiguraciju i hash. Identitet autora ocene
                nije nezavisno potvrđen.
              </p>
              <p>
                <strong>{data?.feedback.length ?? 0}</strong> sačuvanih ocena ·{" "}
                <strong>
                  {data?.jobs.filter(
                    (j) => j.status === "completed" && j.result?.fallback,
                  ).length ?? 0}
                </strong>{" "}
                sačuvanih odgovora sa fallback-om
              </p>
              <p>
                {answers.reduce((n, a) => n + (a.quality?.risk_count ?? 0), 0)}{" "}
                rizičnih tvrdnji ·{" "}
                {answers.reduce(
                  (n, a) => n + (a.quality?.review_count ?? 0),
                  0,
                )}{" "}
                tvrdnji za pregled ·{" "}
                {
                  answers.filter((a) =>
                    a.quality?.completeness.some((p) => !p.present),
                  ).length
                }{" "}
                odgovora sa nedostajućim delom. Obuhvat: samo trenutno zadržani
                poslovi.
              </p>
              <button className="work-button" onClick={() => void refresh()}>
                Osveži pregled
              </button>
              <button
                className="work-button"
                disabled={!data}
                onClick={() =>
                  download(
                    "izvor-kvalitet.json",
                    JSON.stringify(
                      { feedback: data?.feedback, jobs: data?.jobs },
                      null,
                      2,
                    ),
                    "application/json",
                  )
                }
              >
                Izvezi kvalitet i poslove
              </button>
              {!data?.feedback.length && (
                <p>
                  Još nema ocena. Otvorite „Provera tvrdnji i ocena odgovora” uz
                  odgovor u razgovoru.
                </p>
              )}
              {data?.feedback.map((f) => (
                <details key={f.id}>
                  <summary>
                    {f.label} · {f.answer.question}
                  </summary>
                  <p>{f.comment || "Bez komentara."}</p>
                  <p>{f.answer.answer}</p>
                  <code>{f.answer_sha256}</code>
                </details>
              ))}
            </article>
            <article className="work-card">
              <h2>Trajni poslovi</h2>
              <p>
                Aktivni posao se oporavlja posle prekida u okviru roka od 5
                minuta. Završeni rezultati ostaju 15 minuta, najviše 64 zapisa.
              </p>
              {data?.jobs.map((j) => (
                <details key={j.id}>
                  <summary>
                    {j.status} · {j.id.slice(0, 10)} · {j.seconds.toFixed(2)} s
                  </summary>
                  <p>
                    {j.progress.message} {j.error}
                  </p>
                  {!["completed", "failed", "cancelled"].includes(j.status) && (
                    <button
                      className="work-button"
                      onClick={() =>
                        void action(async () => {
                          await api(`/jobs/${j.id}/cancel`, {});
                          await refresh();
                        })
                      }
                    >
                      Otkaži posao
                    </button>
                  )}
                  {validAnswer(j.result) && (
                    <>
                      <p>{j.result.question}</p>
                      <p>{j.result.answer}</p>
                      <AnswerQuality answer={j.result} />
                    </>
                  )}
                  <details>
                    <summary>Sačuvani podaci i faze</summary>
                    <pre>{JSON.stringify(j.result ?? j.phases, null, 2)}</pre>
                  </details>
                </details>
              ))}
            </article>
            {data?.stability && (
              <article className="work-card">
                <h2>Ponovljivost sa praznim kešom</h2>
                <p>{data.stability.note}</p>
                <p>
                  Stvarni pozivi: embeddings{" "}
                  {data.stability.requests.embeddings} · LLM{" "}
                  {data.stability.requests.llm}.
                </p>
                {data.stability.groups.map((g) => (
                  <p key={g.question}>
                    <strong>{g.question}</strong>
                    <br />
                    {g.stable
                      ? "Isti odgovor i citati u sva tri ponavljanja."
                      : `${g.distinct_outputs} različita izlaza.`}{" "}
                    Vremena:{" "}
                    {g.seconds.map((s) => `${s.toFixed(2)} s`).join(" / ")}.
                  </p>
                ))}
                <button
                  className="work-button"
                  onClick={() =>
                    download(
                      "izvor-ponovljivost.json",
                      JSON.stringify(data.stability, null, 2),
                      "application/json",
                    )
                  }
                >
                  Izvezi probu ponovljivosti
                </button>
              </article>
            )}
          </>
        )}
        {tab === "backup" && (
          <article className="work-card">
            <h2>Backup bez prepisivanja</h2>
            <p>
              JSON v3 sadrži SHA-256 checksum. Uvoz prvo prikazuje pregled, daje
              nove ID-jeve razgovorima i uklanja veze ka aktivnim poslovima
              drugog servera. Najviše 10 razgovora ukupno; postojeći se čuvaju.
            </p>
            <button
              className="work-button"
              onClick={() =>
                void action(async () =>
                  download(
                    "izvor-backup.json",
                    await createBackup(conversations),
                    "application/json",
                  ),
                )
              }
            >
              Preuzmi JSON backup
            </button>
            <label className="file-label">
              Uvezi backup za pregled
              <input
                type="file"
                accept=".json"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file)
                    void action(async () => {
                      if (file.size > 5000000)
                        throw new Error("Backup je veći od 5 MB.");
                      setIncoming(await readBackup(await file.text()));
                    });
                }}
              />
            </label>
            {incoming && (
              <div className="work-preview">
                <h3>Pregled uvoza</h3>
                <p>
                  {incoming.length} razgovora ·{" "}
                  {incoming.reduce((n, c) => n + c.turns.length, 0)} poruka.
                  Trenutno je sačuvano {conversations.length} razgovora.
                </p>
                <ul>
                  {incoming.map((c) => (
                    <li key={c.id}>{c.title}</li>
                  ))}
                </ul>
                <button
                  className="work-button primary"
                  disabled={loading}
                  onClick={() =>
                    void action(async () => {
                      mergeBackup(conversations, incoming);
                      onImport(incoming);
                      setIncoming(null);
                      setNotice(
                        "Razgovori su dodati. Sačekajte potvrdu čuvanja u istoriji.",
                      );
                    })
                  }
                >
                  Potvrdi uvoz
                </button>
                <button
                  className="work-button"
                  onClick={() => setIncoming(null)}
                >
                  Odustani od uvoza
                </button>
              </div>
            )}
          </article>
        )}
      </div>
    </section>
  );
}
