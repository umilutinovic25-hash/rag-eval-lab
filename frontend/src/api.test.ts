import { describe, expect, it, vi } from "vitest";
import { api } from "./api";

describe("local API error recovery", () => {
  it.each(["/chat", "/documents", "/status", "/evaluations"])(
    "rejects a structurally invalid successful %s response",
    async (path) => {
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue({
          ok: true,
          json: async () => ({ unexpected: "payload" }),
        }),
      );
      await expect(api(path)).rejects.toThrow("neispravn");
    },
  );
  it("explains a lost connection without exposing browser exception text", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Failed to fetch")),
    );
    await expect(api("/chat", { question: "test" })).rejects.toThrow(
      "start-web.command",
    );
  });

  it("explains an invalid server response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => {
          throw new SyntaxError("HTML instead of JSON");
        },
      }),
    );
    await expect(api("/documents")).rejects.toThrow(
      "Server je vratio neispravan odgovor",
    );
  });

  it("preserves an actionable model error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({ error: "Izaberite režim Bez modela." }),
      }),
    );
    await expect(api("/chat", {})).rejects.toThrow(
      "Izaberite režim Bez modela.",
    );
  });

  it("does not render an object as an error message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({ error: { internal: "details" } }),
      }),
    );
    await expect(api("/chat", {})).rejects.toThrow("Zahtev nije završen");
  });

  it("keeps reads as GET and returns the real JSON payload", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => ({ documents: [] }) });
    vi.stubGlobal("fetch", fetchMock);
    await expect(api("/documents")).resolves.toEqual({ documents: [] });
    expect(fetchMock).toHaveBeenCalledWith("/api/documents", {});
  });
});
