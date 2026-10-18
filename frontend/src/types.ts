export type Profile = "current" | "offline";
export type Page = "chat" | "documents" | "evaluation";
export interface Chunk {
  chunk_id: string;
  doc_id: string;
  title: string;
  version: string;
  status: string;
  text: string;
  score?: number;
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
  citation_precision: number;
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
