import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App, { AnswerText } from "./App";
import type { Answer } from "./types";

const answer: Answer = {
  question: "Remote work?",
  answer:
    'Up to 3 days per week. [hb-03-chunk-0]\nSource [hb-03-chunk-0]: "original"',
  refused: false,
  citations: [
    {
      chunk_id: "hb-03-chunk-0",
      doc_id: "hb-03",
      title: "Remote work policy",
      version: "2026",
      status: "current",
      text: "3 days per week.",
    },
  ],
  retrieved: [],
  trace: [],
  profile: "current",
  fallback: null,
  seconds: 0.1,
  created_at: "2026-10-18",
};

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => ({
      ok: true,
      json: async () =>
        url.endsWith("/status")
          ? { ollama: false, models: [], required_models: [] }
          : url.endsWith("/documents")
            ? { documents: [] }
            : answer,
    })),
  );
});

describe("real UI contracts", () => {
  it("opens verified citations without rendering arbitrary answer HTML", () => {
    const onSource = vi.fn();
    render(
      <AnswerText
        result={{
          ...answer,
          answer: "<script>bad()</script> [hb-03-chunk-0] [unknown]",
        }}
        onSource={onSource}
      />,
    );
    fireEvent.click(screen.getByLabelText("Otvori izvor hb-03-chunk-0"));
    expect(onSource).toHaveBeenCalledWith("hb-03-chunk-0");
    expect(screen.getByText(/<script>/)).toBeInTheDocument();
    expect(document.querySelector("script")).toBeNull();
    expect(screen.getAllByRole("button")).toHaveLength(1);
  });

  it("sends the exact cached English sample and displays its source", async () => {
    render(<App />);
    fireEvent.click(
      screen.getByRole("button", {
        name: "Koliko dana mogu da radim od kuće?",
      }),
    );
    await screen.findByText("Up to 3 days per week.");
    expect(fetch).toHaveBeenCalledWith(
      "/api/chat",
      expect.objectContaining({
        body: JSON.stringify({
          question: "How many days per week can I work remotely?",
          profile: "current",
        }),
      }),
    );
    expect(screen.getByText("3 days per week.")).toBeInTheDocument();
    expect(localStorage.getItem("izvor.conversations.v1")).toContain(
      "Remote work policy",
    );
  });

  it("preserves an actionable error and lets the user retry in offline mode", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation(
      async (url) =>
        ({
          ok: !String(url).endsWith("/chat"),
          json: async () =>
            String(url).endsWith("/chat")
              ? { error: "Pokrenite Ollama ili izaberite režim Bez modela." }
              : String(url).endsWith("/documents")
                ? { documents: [] }
                : { ollama: false, models: [], required_models: [] },
        }) as Response,
    );
    render(<App />);
    fireEvent.change(screen.getByLabelText("Pitanje o priručniku"), {
      target: { value: "A new question" },
    });
    fireEvent.click(screen.getByLabelText("Pošalji pitanje"));
    await screen.findByRole("alert");
    expect(screen.queryByText("Odgovor sa izvorima")).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("Vrati pitanje u unos"));
    fireEvent.change(screen.getByLabelText("Režim pretrage"), {
      target: { value: "offline" },
    });
    expect(screen.getByLabelText("Pitanje o priručniku")).toHaveValue(
      "A new question",
    );
    await waitFor(() =>
      expect(screen.getByLabelText("Pošalji pitanje")).toBeEnabled(),
    );
  });

  it("recovers safely from corrupt browser storage", () => {
    localStorage.setItem("izvor.conversations.v1", "{bad");
    render(<App />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "Odgovori počinju izvorom.",
    );
  });

  it("marks an interrupted saved request for retry instead of spinning forever", () => {
    localStorage.setItem(
      "izvor.conversations.v1",
      JSON.stringify([
        {
          id: "old",
          title: "Interrupted question",
          turns: [{ id: "turn", question: "Interrupted question" }],
        },
      ]),
    );
    render(<App />);
    fireEvent.click(
      screen.getByRole("button", { name: "Interrupted question" }),
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Prethodna obrada nije završena",
    );
    expect(screen.queryByText("Proveravam dokumente…")).not.toBeInTheDocument();
  });
});
