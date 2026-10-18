import { useEffect, useRef, useState } from "react";
import {
  ArrowDownToLine,
  ArrowRight,
  ArrowUp,
  BookOpen,
  ChartNoAxesColumnIncreasing,
  Check,
  CheckCheck,
  ChevronDown,
  CircleAlert,
  Copy,
  Database,
  FileText,
  Info,
  Laptop,
  LoaderCircle,
  Menu,
  MessageSquare,
  Plus,
  Search,
  ShieldCheck,
  X,
} from "lucide-react";
import { api, download } from "./api";
import type {
  Answer,
  Conversation,
  Document,
  Page,
  Profile,
  Status,
  Turn,
} from "./types";
import { EvaluationView } from "./Evaluation";

const STORAGE_KEY = "izvor.conversations.v1";
const samples = [
  [
    "Koliko dana mogu da radim od kuće?",
    "How many days per week can I work remotely?",
  ],
  [
    "Kako da zamenim laptop?",
    "Where do I request a replacement laptop and how long does it take?",
  ],
  [
    "Koji je budžet za obuke?",
    "What is the yearly training budget per employee?",
  ],
];
const pageNames = {
  chat: "Razgovor",
  documents: "Dokumenti",
  evaluation: "Evaluacija",
};
const uid = () => crypto.randomUUID();
const chunksLabel = (n: number) =>
  `${n} ${n === 1 ? "odlomak" : n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 12 || n % 100 > 14) ? "odlomka" : "odlomaka"}`;

function loadConversations(): Conversation[] {
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    if (!Array.isArray(value)) return [];
    return value
      .filter(
        (c) =>
          typeof c.id === "string" &&
          typeof c.title === "string" &&
          Array.isArray(c.turns),
      )
      .slice(0, 10)
      .map((c) => ({
        ...c,
        turns: c.turns
          .filter(
            (t: Turn) =>
              typeof t.id === "string" && typeof t.question === "string",
          )
          .slice(-30)
          .map((t: Turn) => {
            const r = t.result;
            if (
              r &&
              typeof r.answer === "string" &&
              Array.isArray(r.citations) &&
              Array.isArray(r.trace) &&
              Array.isArray(r.retrieved) &&
              typeof r.seconds === "number"
            )
              return t;
            return {
              id: t.id,
              question: t.question,
              error:
                t.error ||
                "Prethodna obrada nije završena. Pošaljite pitanje ponovo.",
            };
          }),
      }));
  } catch {
    return [];
  }
}

export function AnswerText({
  result,
  onSource,
}: {
  result: Answer;
  onSource: (id: string) => void;
}) {
  const text = result.answer.split(/\nSource \[/)[0];
  return (
    <p className="answer-text">
      {text.split(/(\[hb-\d+-chunk-\d+\])/g).map((part, i) => {
        const citation = result.citations.find(
          (c) => `[${c.chunk_id}]` === part,
        );
        return citation ? (
          <button
            key={i}
            className="inline-citation"
            title={citation.title}
            onClick={() => onSource(citation.chunk_id)}
            aria-label={`Otvori izvor ${citation.chunk_id}`}
          >
            {result.citations.indexOf(citation) + 1}
          </button>
        ) : (
          <span key={i}>{part}</span>
        );
      })}
    </p>
  );
}

function SourceInspector({
  result,
  selected,
  onSelect,
  onDocuments,
  onClose,
}: {
  result?: Answer;
  selected: string | null;
  onSelect: (id: string) => void;
  onDocuments: () => void;
  onClose: () => void;
}) {
  const [tab, setTab] = useState("sources");
  const selectedChunk = result?.citations.find((c) => c.chunk_id === selected);
  useEffect(() => {
    if (selected) setTab("sources");
  }, [selected]);
  return (
    <aside
      className="inspector"
      id="source-inspector"
      aria-label="Izvori i odluke"
    >
      <div className="inspector-heading">
        <BookOpen size={25} />
        <h2>Izvori i odluke</h2>
        <button
          className="icon-button mobile-close"
          onClick={onClose}
          aria-label="Zatvori izvore"
        >
          <X size={20} />
        </button>
      </div>
      {result ? (
        <>
          <div
            className="segmented"
            role="tablist"
            aria-label="Pregled odgovora"
          >
            <button
              role="tab"
              aria-selected={tab === "sources"}
              onClick={() => setTab("sources")}
            >
              Izvori <span>{result.citations.length}</span>
            </button>
            <button
              role="tab"
              aria-selected={tab === "trace"}
              onClick={() => setTab("trace")}
            >
              Tok odluke
            </button>
          </div>
          <div className="inspector-scroll" role="tabpanel">
            {tab === "sources" ? (
              result.citations.length ? (
                result.citations.map((c, i) => (
                  <button
                    key={c.chunk_id}
                    className={`source-item ${selectedChunk?.chunk_id === c.chunk_id ? "selected" : ""}`}
                    onClick={() => onSelect(c.chunk_id)}
                  >
                    <div className="source-number">{i + 1}</div>
                    <div>
                      <h3>{c.title}</h3>
                      <div className="source-meta">
                        {c.version} <span className="dot" /> Aktuelan
                      </div>
                      <blockquote>{c.text}</blockquote>
                      <code>{c.chunk_id}</code>
                    </div>
                  </button>
                ))
              ) : (
                <div className="small-empty">
                  <ShieldCheck size={35} />
                  <h3>Nema dovoljnog dokaza</h3>
                  <p>
                    Sistem je odbio odgovor. Sličnost teme nije dokaz da
                    dokument sadrži traženu informaciju.
                  </p>
                </div>
              )
            ) : (
              <div className="trace-list">
                {result.trace.map((step, i) => (
                  <div className="trace-item" key={i}>
                    <span className="trace-index">{i + 1}</span>
                    <div>
                      <h3>
                        {(
                          {
                            retrieval: "Pretraga priručnika",
                            decision: "Odluka sistema",
                            context: "Proširenje konteksta",
                            generation: "Formiranje odgovora",
                            judge: "Provera relevantnosti",
                            rerank: "Provera relevantnosti",
                          } as Record<string, string>
                        )[step.stage] || step.stage}
                      </h3>
                      <details>
                        <summary>
                          Prikaži detalje <ChevronDown size={13} />
                        </summary>
                        <pre>{JSON.stringify(step, null, 2)}</pre>
                      </details>
                    </div>
                  </div>
                ))}
                <details className="retrieved-details">
                  <summary>
                    Pronađeni odlomci ({result.retrieved.length})
                  </summary>
                  {result.retrieved.map((c) => (
                    <div className="retrieved-item" key={c.chunk_id}>
                      <strong>{c.title}</strong>
                      <span>Rezultat sličnosti: {c.score?.toFixed(3)}</span>
                      <p>{c.text}</p>
                      <code>{c.chunk_id}</code>
                    </div>
                  ))}
                  <p className="muted fine">
                    Sličnost nije verovatnoća tačnosti odgovora.
                  </p>
                </details>
              </div>
            )}
          </div>
          <div className="inspector-note">
            <Info size={15} />
            <span>
              {result.profile === "offline"
                ? "Leksička pretraga · bez poziva modelima."
                : "Lokalni modeli i keširani odgovori. Ponovljeno pitanje može biti obrađeno iz keša."}
            </span>
          </div>
        </>
      ) : (
        <>
          <div className="inspector-empty">
            <svg
              className="document-stack"
              viewBox="0 0 96 112"
              fill="none"
              stroke="currentColor"
              aria-hidden="true"
            >
              <rect x="29" y="28" width="54" height="76" rx="6" />
              <rect
                x="23"
                y="22"
                width="54"
                height="76"
                rx="6"
                fill="#f9fafb"
              />
              <rect
                x="16"
                y="15"
                width="56"
                height="76"
                rx="6"
                fill="#f9fafb"
              />
              <rect x="10" y="4" width="57" height="76" rx="6" fill="#f9fafb" />
              <path
                d="M22 25h32M22 37h32M22 49h23M22 61h12"
                strokeLinecap="round"
              />
            </svg>
            <h3>Dokaz uz svaki odgovor</h3>
            <p>
              Ovde ćete videti korišćene odlomke, njihove verzije i tok odluke.
            </p>
          </div>
          <div className="handbook-box">
            <h3>
              <BookOpen size={24} />
              Priručnik kompanije
            </h3>
            <div>
              <FileText size={17} />
              10 dokumenata
            </div>
            <div>
              <FileText size={17} />9 aktuelnih · 1 arhiviran
            </div>
            <button onClick={onDocuments}>
              Pregledaj dokumente <ArrowRight size={17} />
            </button>
          </div>
        </>
      )}
    </aside>
  );
}

function DocumentsView({
  documents,
  error,
  retry,
}: {
  documents: Document[];
  error: string;
  retry: () => void;
}) {
  const [query, setQuery] = useState("");
  const [scope, setScope] = useState("current");
  const [selected, setSelected] = useState<Document | null>(null);
  const list = documents.filter(
    (d) =>
      (scope === "all" || d.status === scope) &&
      `${d.title} ${d.text} ${d.section}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  return (
    <div className="content-page documents-page">
      <div className="page-heading">
        <div>
          <h1>Znanje, na jednom mestu.</h1>
          <p>Originalni tekstovi priručnika i odlomci koje RAG pretražuje.</p>
        </div>
        <span className="count-label">{documents.length} dokumenata</span>
      </div>
      {error ? (
        <div className="error-notice" role="alert">
          {error}
          <button onClick={retry}>Pokušaj ponovo</button>
        </div>
      ) : (
        <>
          <div className="filter-bar">
            <label className="search-input">
              <Search size={18} />
              <input
                aria-label="Pretraži dokumente"
                placeholder="Pretraži priručnik…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </label>
            <select
              aria-label="Verzije dokumenata"
              value={scope}
              onChange={(e) => setScope(e.target.value)}
            >
              <option value="current">Aktuelni dokumenti</option>
              <option value="all">Sve verzije</option>
              <option value="superseded">Arhivirani dokumenti</option>
            </select>
          </div>
          <p className="muted fine">
            Arhivirana politika iz 2024. je dostupna za poređenje. Isključena je
            iz pretrage odgovora.
          </p>
          <div className="document-layout">
            <div className="document-list">
              {list.map((doc) => (
                <button
                  className={`document-row ${selected?.doc_id === doc.doc_id ? "active" : ""}`}
                  key={doc.doc_id}
                  onClick={() => setSelected(doc)}
                >
                  <FileText size={22} />
                  <div>
                    <h3>{doc.title}</h3>
                    <p>
                      {doc.section} · {chunksLabel(doc.chunks.length)}
                    </p>
                  </div>
                  <span
                    className={
                      doc.status === "current" ? "version" : "version archived"
                    }
                  >
                    {doc.version}
                  </span>
                  <ArrowRight size={17} />
                </button>
              ))}
              {!list.length && (
                <p className="empty-results">
                  Nema dokumenata za ovu pretragu.
                </p>
              )}
            </div>
            <div className="document-detail">
              {selected ? (
                <>
                  <div className="detail-heading">
                    <span
                      className={
                        selected.status === "current"
                          ? "status-label"
                          : "status-label archived"
                      }
                    >
                      {selected.status === "current"
                        ? "Aktuelan dokument"
                        : "Arhiviran · nije u pretrazi"}
                    </span>
                    <button
                      className="icon-button"
                      onClick={() => setSelected(null)}
                      aria-label="Zatvori dokument"
                    >
                      <X size={18} />
                    </button>
                  </div>
                  <h2>{selected.title}</h2>
                  <p className="muted">
                    {selected.section} · Verzija {selected.version}
                  </p>
                  <p className="document-text">{selected.text}</p>
                  <h3 className="chunks-heading">Odlomci dokumenta</h3>
                  {selected.chunks.map((c) => (
                    <div className="document-chunk" key={c.chunk_id}>
                      <code>{c.chunk_id}</code>
                      <p>{c.text}</p>
                    </div>
                  ))}
                </>
              ) : (
                <div className="small-empty">
                  <BookOpen size={42} strokeWidth={1} />
                  <h3>Otvorite dokument</h3>
                  <p>
                    Pročitajte originalni tekst i vidite kako je podeljen na
                    odlomke.
                  </p>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default function App() {
  const [page, setPage] = useState<Page>("chat");
  const [conversations, setConversations] =
    useState<Conversation[]>(loadConversations);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [profile, setProfile] = useState<Profile>("current");
  const [busy, setBusy] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [documentsError, setDocumentsError] = useState("");
  const [status, setStatus] = useState<Status | null>(null);
  const [statusOpen, setStatusOpen] = useState(false);
  const [storageError, setStorageError] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const [compact, setCompact] = useState(
    () =>
      typeof matchMedia === "function" &&
      matchMedia("(max-width:1100px)").matches,
  );
  useEffect(() => {
    if (typeof matchMedia !== "function") return;
    const query = matchMedia("(max-width:1100px)");
    const update = () => setCompact(query.matches);
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [selectedTurn, setSelectedTurn] = useState<string | null>(null);
  const [selectedSource, setSelectedSource] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const sending = useRef(false);
  const conversation = conversations.find((c) => c.id === activeId);
  const turns = conversation?.turns || [];
  const activeResult =
    turns.find((t) => t.id === selectedTurn)?.result ||
    [...turns].reverse().find((t) => t.result)?.result;

  function loadDocuments() {
    setDocumentsError("");
    api<{ documents: Document[] }>("/documents")
      .then((d) => setDocuments(d.documents))
      .catch((e) => setDocumentsError(e.message));
  }
  function refreshStatus() {
    api<Status>("/status")
      .then(setStatus)
      .catch(() => setStatus(null));
  }
  useEffect(() => {
    loadDocuments();
    refreshStatus();
  }, []);
  useEffect(() => {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(conversations.slice(0, 10)),
      );
      setStorageError(false);
    } catch {
      setStorageError(true);
    }
  }, [conversations]);
  useEffect(() => {
    if (turns.length)
      bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns.length, busy]);
  useEffect(() => {
    if (!busy) {
      setElapsed(0);
      return;
    }
    const timer = setInterval(() => setElapsed((v) => v + 1), 1000);
    return () => clearInterval(timer);
  }, [busy]);
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setStatusOpen(false);
        setNavOpen(false);
        setSourcesOpen(false);
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, []);

  function navigate(next: Page) {
    setPage(next);
    setNavOpen(false);
    setSourcesOpen(false);
  }
  function newConversation() {
    if (busy) return;
    setActiveId(null);
    setSelectedTurn(null);
    setSelectedSource(null);
    setDraft("");
    navigate("chat");
    textareaRef.current?.focus();
  }
  function selectSource(turn: string, source: string) {
    setSelectedTurn(turn);
    setSelectedSource(source);
    setSourcesOpen(true);
  }
  async function send(text = draft) {
    const question = text.trim();
    if (!question || question.length > 2000 || sending.current) return;
    sending.current = true;
    const id = activeId || uid();
    const turnId = uid();
    const turn: Turn = { id: turnId, question };
    setConversations((current) => {
      const exists = current.find((c) => c.id === id);
      return exists
        ? current.map((c) =>
            c.id === id ? { ...c, turns: [...c.turns, turn].slice(-30) } : c,
          )
        : [{ id, title: question, turns: [turn] }, ...current].slice(0, 10);
    });
    setActiveId(id);
    setDraft("");
    setBusy(true);
    setSelectedTurn(turnId);
    setSelectedSource(null);
    try {
      const result = await api<Answer>("/chat", { question, profile });
      setConversations((cs) =>
        cs.map((c) =>
          c.id === id
            ? {
                ...c,
                turns: c.turns.map((t) =>
                  t.id === turnId ? { ...t, result } : t,
                ),
              }
            : c,
        ),
      );
      setSelectedSource(result.citations[0]?.chunk_id || null);
    } catch (error) {
      setConversations((cs) =>
        cs.map((c) =>
          c.id === id
            ? {
                ...c,
                turns: c.turns.map((t) =>
                  t.id === turnId
                    ? { ...t, error: (error as Error).message }
                    : t,
                ),
              }
            : c,
        ),
      );
    } finally {
      setBusy(false);
      sending.current = false;
      refreshStatus();
    }
  }
  async function copy(turn: Turn) {
    try {
      await navigator.clipboard.writeText(turn.result?.answer || "");
      setCopied(turn.id);
      setTimeout(() => setCopied(null), 1800);
    } catch {
      setCopied("failed");
    }
  }
  function exportChat() {
    download(
      "izvor-razgovor.md",
      `# Izvor — razgovor\n\n${turns.map((t) => `## ${t.question}\n\n${t.result?.answer || t.error || "Obrada nije završena."}\n\n${t.result ? `Režim: ${t.result.profile}. Datum: ${t.result.created_at}.\n\n${t.result.citations.map((c) => `- ${c.chunk_id} — ${c.title}, ${c.version}: ${c.text}`).join("\n")}` : ""}`).join("\n\n---\n\n")}`,
    );
  }

  return (
    <div className="app-shell">
      {navOpen && (
        <button
          className="scrim"
          aria-label="Zatvori navigaciju"
          onClick={() => setNavOpen(false)}
        />
      )}
      <aside
        inert={statusOpen || (sourcesOpen && compact)}
        className={`sidebar ${navOpen ? "is-open" : ""}`}
      >
        <div className="brand">
          izvor<span>.</span>
        </div>
        <p className="brand-caption">RAG radni prostor</p>
        <nav aria-label="Glavna navigacija">
          {(
            [
              { id: "chat", icon: MessageSquare },
              { id: "documents", icon: FileText },
              { id: "evaluation", icon: ChartNoAxesColumnIncreasing },
            ] as const
          ).map(({ id, icon: Icon }) => (
            <button
              key={id}
              className={page === id ? "nav-item selected" : "nav-item"}
              onClick={() => navigate(id)}
              aria-current={page === id ? "page" : undefined}
            >
              <Icon size={21} />
              {pageNames[id]}
            </button>
          ))}
        </nav>
        <div className="sidebar-divider" />
        <button className="new-chat" onClick={newConversation} disabled={busy}>
          <Plus size={20} />
          Novi razgovor
        </button>
        {!!conversations.length && (
          <div className="history">
            <p>Prethodni razgovori</p>
            {conversations.map((c) => (
              <button
                title={c.title}
                className={activeId === c.id && page === "chat" ? "active" : ""}
                key={c.id}
                disabled={busy}
                onClick={() => {
                  setActiveId(c.id);
                  setSelectedTurn(null);
                  setSelectedSource(null);
                  navigate("chat");
                }}
              >
                <MessageSquare size={14} />
                <span>{c.title}</span>
              </button>
            ))}
          </div>
        )}
        <button
          className="system-button"
          onClick={() => {
            setStatusOpen(true);
            refreshStatus();
          }}
        >
          <Laptop size={18} />
          <span>Lokalni sistem</span>
          <span className="dot" /> <span className="week-label">Week 07</span>
        </button>
      </aside>
      <div
        inert={statusOpen}
        className={`workspace ${page === "chat" ? "with-inspector" : ""}`}
      >
        <main
          className="main-workspace"
          inert={statusOpen || navOpen || (sourcesOpen && compact)}
        >
          <header className="topbar">
            <button
              className="icon-button mobile-menu"
              aria-label="Otvori navigaciju"
              onClick={() => setNavOpen(true)}
            >
              <Menu size={22} />
            </button>
            <div className="breadcrumb">
              <span>Radni prostor</span>
              <span>/</span>
              <strong>{pageNames[page]}</strong>
            </div>
            <div className="header-actions">
              {page === "chat" && !!turns.length && (
                <button
                  className="icon-button"
                  title="Preuzmi razgovor"
                  aria-label="Preuzmi razgovor"
                  onClick={exportChat}
                >
                  <ArrowDownToLine size={18} />
                </button>
              )}
              <button
                className="local-status"
                onClick={() => {
                  setStatusOpen(true);
                  refreshStatus();
                }}
              >
                <span className="dot" />
                Lokalno
              </button>
            </div>
          </header>
          {page === "chat" ? (
            <>
              <div className={`chat-scroll ${turns.length ? "has-turns" : ""}`}>
                {!turns.length ? (
                  <div className="welcome">
                    <h1>Odgovori počinju izvorom.</h1>
                    <p className="welcome-description">
                      Pitajte interni priručnik. Proverite svaki odgovor.
                    </p>
                    <div className="suggestions">
                      <p>Predlozi za početak</p>
                      {samples.map(([label, question]) => (
                        <button
                          key={question}
                          disabled={busy}
                          onClick={() => send(question)}
                        >
                          {label}
                          <ArrowRight size={19} />
                        </button>
                      ))}
                    </div>
                    <div className="trust-note">
                      <ShieldCheck size={34} strokeWidth={1.6} />
                      <div>
                        <h2>Svaki odgovor ima trag.</h2>
                        <p>
                          Izvori, verzije dokumenata i odluke sistema na jednom
                          mestu.
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="turns">
                    {turns.map((turn) => (
                      <article className="turn" key={turn.id}>
                        <div className="question">
                          <span>Vi</span>
                          <h2>{turn.question}</h2>
                        </div>
                        {turn.result ? (
                          <div className="answer">
                            <div className="answer-label">
                              <span className="answer-mark">i.</span>
                              <strong>izvor.</strong>
                              <span
                                className={
                                  turn.result.refused
                                    ? "refused-label"
                                    : "grounded-label"
                                }
                              >
                                {turn.result.refused
                                  ? "Nedovoljno dokaza"
                                  : "Odgovor sa izvorima"}
                              </span>
                            </div>
                            <AnswerText
                              result={turn.result}
                              onSource={(id) => selectSource(turn.id, id)}
                            />
                            {turn.result.fallback && (
                              <div className="fallback-note">
                                <Info size={15} />
                                Prikazan je originalni odlomak: generisani
                                odgovor nije prošao proveru.
                              </div>
                            )}
                            <div className="answer-footer">
                              <button
                                className="source-trigger"
                                onClick={() => {
                                  setSelectedTurn(turn.id);
                                  setSourcesOpen(true);
                                }}
                              >
                                <BookOpen size={15} />
                                {turn.result.citations.length
                                  ? `${turn.result.citations.length} ${turn.result.citations.length === 1 ? "izvor" : "izvora"}`
                                  : "Pogledaj odluku"}
                                <ArrowRight size={14} />
                              </button>
                              <span>
                                {turn.result.profile === "offline"
                                  ? "Bez modela"
                                  : "Napredni RAG"}{" "}
                                · {turn.result.seconds.toFixed(1)} s
                              </span>
                              <button
                                className="icon-button"
                                aria-label="Kopiraj odgovor"
                                onClick={() => copy(turn)}
                              >
                                {copied === turn.id ? (
                                  <CheckCheck size={16} />
                                ) : (
                                  <Copy size={16} />
                                )}
                              </button>
                            </div>
                          </div>
                        ) : turn.error ? (
                          <div className="error-notice" role="alert">
                            <CircleAlert size={20} />
                            <div>
                              <p>{turn.error}</p>
                              <button onClick={() => setDraft(turn.question)}>
                                Vrati pitanje u unos
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div className="pending" role="status">
                            <LoaderCircle size={18} className="spin" />
                            <div>
                              <strong>Proveravam dokumente…</strong>
                              <p>
                                {elapsed < 5
                                  ? "Pretraga, provera dokaza i priprema odgovora."
                                  : `Lokalnim modelima može biti potrebno više vremena. ${elapsed} s`}
                              </p>
                            </div>
                          </div>
                        )}
                      </article>
                    ))}
                    {copied === "failed" && (
                      <p role="status">
                        Kopiranje nije dostupno. Možete preuzeti razgovor.
                      </p>
                    )}
                    <p className="conversation-note">
                      Svako pitanje obrađuje se nezavisno. Istorija razgovora se
                      ne šalje modelu.
                    </p>
                    <div ref={bottomRef} />
                  </div>
                )}
              </div>
              <div className="composer-area">
                {storageError && (
                  <p className="error-notice" role="alert">
                    Browser ne može da sačuva istoriju. Preuzmite razgovor pre
                    zatvaranja stranice.
                  </p>
                )}
                <form
                  className="composer"
                  onSubmit={(e) => {
                    e.preventDefault();
                    void send();
                  }}
                >
                  <textarea
                    ref={textareaRef}
                    aria-label="Pitanje o priručniku"
                    placeholder="Postavite pitanje o priručniku…"
                    value={draft}
                    maxLength={2000}
                    rows={2}
                    disabled={busy}
                    onChange={(e) => setDraft(e.target.value)}
                    onKeyDown={(e) => {
                      if (
                        e.key === "Enter" &&
                        !e.shiftKey &&
                        !e.nativeEvent.isComposing
                      ) {
                        e.preventDefault();
                        void send();
                      }
                    }}
                  />
                  <div className="composer-toolbar">
                    <label className="profile-select">
                      <Database size={16} />
                      <select
                        aria-label="Režim pretrage"
                        value={profile}
                        disabled={busy}
                        onChange={(e) => setProfile(e.target.value as Profile)}
                      >
                        <option value="current">Napredni RAG</option>
                        <option value="offline">Bez modela</option>
                      </select>
                      <ChevronDown size={14} />
                    </label>
                    <span className="send-hint">
                      {draft.length > 1800
                        ? `${draft.length}/2000`
                        : "Enter za slanje"}
                    </span>
                    <button
                      className="send-button"
                      aria-label="Pošalji pitanje"
                      disabled={busy || !draft.trim()}
                    >
                      {busy ? (
                        <LoaderCircle className="spin" size={20} />
                      ) : (
                        <ArrowUp size={21} />
                      )}
                    </button>
                  </div>
                </form>
                <p className="composer-caption">
                  <Info size={14} />
                  <span>
                    Odgovori se zasnivaju samo na dokumentima. Modeli obrađuju
                    pitanja na engleskom.
                  </span>
                </p>
              </div>
            </>
          ) : page === "documents" ? (
            <DocumentsView
              documents={documents}
              error={documentsError}
              retry={loadDocuments}
            />
          ) : (
            <EvaluationView />
          )}
        </main>
        {page === "chat" && (
          <div className={`inspector-wrapper ${sourcesOpen ? "is-open" : ""}`}>
            <SourceInspector
              result={activeResult}
              selected={selectedSource}
              onSelect={setSelectedSource}
              onDocuments={() => navigate("documents")}
              onClose={() => setSourcesOpen(false)}
            />
          </div>
        )}
      </div>
      {statusOpen && (
        <div className="modal-backdrop" onClick={() => setStatusOpen(false)}>
          <section
            className="system-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="status-title"
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => {
              if (e.key !== "Tab") return;
              const items = Array.from(
                e.currentTarget.querySelectorAll<HTMLButtonElement>(
                  "button:not([disabled])",
                ),
              );
              const first = items[0],
                last = items[items.length - 1];
              if (e.shiftKey && document.activeElement === first) {
                e.preventDefault();
                last?.focus();
              } else if (!e.shiftKey && document.activeElement === last) {
                e.preventDefault();
                first?.focus();
              }
            }}
          >
            <button
              autoFocus
              className="icon-button dialog-close"
              aria-label="Zatvori status"
              onClick={() => setStatusOpen(false)}
            >
              <X size={21} />
            </button>
            <div className="dialog-symbol">
              <Laptop size={29} />
            </div>
            <h2 id="status-title">Sve ostaje lokalno.</h2>
            <p>
              Pitanja se obrađuju na ovom računaru. Istorija se čuva u ovom
              browseru; poslednjih 10 razgovora sa najviše 30 pitanja po
              razgovoru.
            </p>
            <div className="system-state">
              <span className={`dot ${!status?.ollama ? "amber" : ""}`} />
              <strong>
                {status
                  ? status.ollama
                    ? "Ollama je dostupna"
                    : "Ollama nije pokrenuta"
                  : "Status nije dostupan"}
              </strong>
              <button onClick={refreshStatus}>Osveži</button>
            </div>
            <p className="fine muted">
              Napredni RAG koristi lokalne modele ili postojeći keš. Za nova
              pitanja pokrenite Ollama sa modelima ispod. Režim „Bez modela”
              uvek radi bez Ollama servisa.
            </p>
            <div className="model-list">
              {(
                status?.required_models || ["bge-m3", "qwen2.5:7b", "gemma3:4b"]
              ).map((model) => (
                <div key={model}>
                  <Database size={16} />
                  <span>{model}</span>
                  {status?.models.some(
                    (m) => m.replace(/:latest$/, "") === model,
                  ) ? (
                    <Check size={16} />
                  ) : (
                    <span className="muted">nije potvrđen</span>
                  )}
                </div>
              ))}
            </div>
            <div className="privacy-actions">
              <button
                onClick={() => {
                  if (busy) return;
                  setConversations([]);
                  setActiveId(null);
                  setSelectedTurn(null);
                  setSelectedSource(null);
                  setStatusOpen(false);
                }}
                disabled={busy}
              >
                Obriši istoriju ovog browsera
              </button>
              <span>Podaci se ne šalju u cloud.</span>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
