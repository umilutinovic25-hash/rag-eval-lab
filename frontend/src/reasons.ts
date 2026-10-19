import type { Trace } from "./types";

/** Plain-language explanations of why the system refused or replaced a generated answer. */
const DECISIONS: Record<string, string> = {
  below_gray_zone: "Pitanje nije dovoljno slično nijednom odlomku priručnika.",
  below_refusal_threshold:
    "Pitanje nije dovoljno slično nijednom odlomku priručnika.",
  no_accepted_candidate:
    "Pronađeni odlomci govore o istoj temi, ali ne sadrže traženu informaciju.",
  untrusted_instruction:
    "Pitanje sadrži uputstvo upućeno sistemu, a ne pitanje o priručniku.",
  assistant_meta_request:
    "Pitanje se odnosi na sam sistem (njegove instrukcije, ulogu ili podešavanja), a ne na priručnik.",
  evidence_missing_subject:
    "Izvori ne potvrđuju traženi predmet, događaj ili okolnosti pitanja.",
  jev_insufficient_evidence:
    "Provera izvora nije našla dovoljno pouzdan dokaz za traženu informaciju.",
  jev_unavailable:
    "Provera izvora trenutno nije dostupna. Odgovor nije pripremljen jer izvori nisu provereni.",
  empty_question: "Pitanje je prazno.",
  ambiguous_request: "Pitanje je preširoko; izaberite o kojoj politici je reč.",
};

const FALLBACKS: Record<string, string> = {
  polarity_conflict:
    "Drugi model se nije složio sa odgovorom „da“ ili „ne“, pa su prikazani originalni odlomci.",
  language_mismatch:
    "Odgovor je bio napisan na drugom jeziku od pitanja, pa su prikazani originalni odlomci.",
  unsupported_number:
    "Odgovor je sadržao broj kojeg nema u izvoru, pa su prikazani originalni odlomci.",
  unsupported_quantity_unit:
    "Odgovor je sadržao količinu ili jedinicu kojih nema u izvoru, pa su prikazani originalni odlomci.",
  invalid_marker:
    "Odgovor nije ispravno naveo izvore, pa su prikazani originalni odlomci.",
  malformed_marker:
    "Odgovor nije ispravno naveo izvore, pa su prikazani originalni odlomci.",
  generated_source_line:
    "Odgovor je sam napisao red izvora, pa su prikazani originalni odlomci.",
  negation_conflict:
    "Odgovor je u sukobu sa izvorom oko negacije, pa su prikazani originalni odlomci.",
  scope_conflict:
    "Odgovor menja obuhvat pravila (osoba ili tim), pa su prikazani originalni odlomci.",
  bound_conflict:
    "Odgovor menja granicu iz izvora (najmanje ili najviše), pa su prikazani originalni odlomci.",
  modality_conflict:
    "Odgovor menja obaveznost pravila (mora, sme, nije obavezno), pa su prikazani originalni odlomci.",
  truncated_answer:
    "Model nije završio odgovor, pa su prikazani originalni odlomci.",
  empty_answer: "Model nije dao odgovor, pa su prikazani originalni odlomci.",
  generation_error:
    "Model nije bio dostupan, pa su prikazani originalni odlomci.",
};

export function decisionReason(trace: Trace[] | undefined): string | null {
  const step = [...(trace ?? [])]
    .reverse()
    .find((s) => s.stage === "decision" && typeof s.reason === "string");
  return step ? (DECISIONS[step.reason as string] ?? null) : null;
}

export function fallbackReason(code: string | null | undefined): string | null {
  if (!code) return null;
  return (
    FALLBACKS[code] ??
    "Generisani odgovor nije prošao proveru, pa su prikazani originalni odlomci."
  );
}

export function traceNote(step: Trace): string | null {
  if (step.stage !== "decision" || typeof step.reason !== "string") return null;
  return DECISIONS[step.reason] ?? null;
}
