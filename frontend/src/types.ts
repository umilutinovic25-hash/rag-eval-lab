export type Profile = "current" | "offline" | "baseline" | "verified";
export type Page = "chat" | "documents" | "evaluation" | "workbench";
export interface Filters {
  topic?: string;
  doc_ids?: string[];
  as_of?: string;
  sandbox?: boolean;
}
export interface Quality {
  version: string;
  caveat: string;
  risk_count: number;
  review_count: number;
  claims: {
    text: string;
    citations: string[];
    status: string;
    reasons: string[];
  }[];
  completeness: { part: string; present: boolean }[];
}
export interface Usage {
  phases?: { stage: string; seconds: number }[];
  requests: { embeddings: number; llm: number };
  cache_hits: { embeddings: number; llm: number };
  prompt_tokens: number | null;
  output_tokens: number | null;
  unknown_token_calls: number;
  model_seconds: number;
}
export interface LibraryDocument extends Omit<Document, "chunks"> {
  origin: string;
  active: boolean;
  quarantined?: boolean;
  published_on: string | null;
  effective_from: string | null;
  effective_until: string | null;
  source_sha256: string;
}
export interface Feedback {
  id: string;
  label: string;
  comment: string;
  answer: Answer;
  answer_sha256: string;
  created_at: string;
}
export interface WorkspaceData {
  stability?: {
    groups: {
      question: string;
      stable: boolean;
      distinct_outputs: number;
      seconds: number[];
    }[];
    requests: { embeddings: number; llm: number };
    note: string;
  } | null;
  documents: LibraryDocument[];
  warnings: { doc_id: string; reasons: string[] }[];
  conflicts: {
    documents: string[];
    title: string;
    reason: string;
    evidence: string[];
  }[];
  note: string;
  feedback: Feedback[];
  jobs: Job[];
}
export interface Comparison {
  kind: "comparison";
  results: Answer[];
  differences: { answer: boolean; citations: boolean; refused: boolean };
}
export interface Chunk {
  chunk_id: string;
  doc_id: string;
  title: string;
  version: string;
  status: string;
  text: string;
  score?: number;
  translated_text?: string;
}
export interface Document {
  doc_id: string;
  title: string;
  section: string;
  version: string;
  status: string;
  text: string;
  chunks: Chunk[];
}
export interface Trace {
  stage: string;
  [key: string]: unknown;
}
export interface Answer {
  quality?: Quality;
  usage?: Usage;
  provenance?: Record<string, unknown>;
  answer_sha256?: string;
  disposition?: string;
  clarification?: string[];
  retrieval_question?: string;
  language?: "en" | "sr";
  translation_review_status?: string | null;
  question: string;
  answer: string;
  refused: boolean;
  citations: Chunk[];
  retrieved: Chunk[];
  trace: Trace[];
  fallback: string | null;
  profile: Profile;
  seconds: number;
  created_at: string;
}
export interface Turn {
  jobId?: string;
  id: string;
  question: string;
  result?: Answer;
  error?: string;
}
export interface Conversation {
  id: string;
  title: string;
  turns: Turn[];
}
export interface Status {
  ollama: boolean;
  models: string[];
  required_models: string[];
  documents: number;
  current_documents: number;
}
export interface EvalRow {
  id: string;
  question?: string;
  pass: boolean;
  behaviour_correct: boolean;
  citation_precision: number | null;
  cited_chunk_ids: string[];
  [key: string]: unknown;
}
export interface EvalAnswer {
  question: string;
  answer: string;
  citations: string[];
  refused: boolean;
  fallback: string | null;
}
export interface EvalRun {
  status: string;
  error: { message: string } | null;
  summary: {
    passed: number;
    total: number;
    behaviour_accuracy: number;
    retrieval_hit_rate: number;
    mean_citation_precision: number;
  } | null;
  results: EvalRow[];
  answers: EvalAnswer[];
  fallback_count: number;
  seconds: number;
}
export interface Evaluation {
  origin: string;
  mode: string;
  created_at: string;
  revision: string;
  git_dirty?: boolean;
  source_sha256?: Record<string, string>;
  cache_sha256?: Record<string, string>;
  status: string;
  question_set_sha256: Record<string, string>;
  requests: Record<string, number>;
  runs: Record<string, EvalRun>;
}

export interface Job {
  id: string;
  status:
    "queued" | "running" | "cancelling" | "completed" | "cancelled" | "failed";
  progress: { stage: string; message: string };
  seconds: number;
  result: Answer | null;
  error: string | null;
  phases: { stage: string; seconds: number }[];
}
