import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup();
  localStorage.clear();
});
Element.prototype.scrollIntoView = vi.fn();
// jsdom has no Web Locks; browser tests exercise real cross-tab locking.
Object.defineProperty(navigator, "locks", {
  configurable: true,
  value: {
    request: async (_name: string, callback: () => unknown) => callback(),
  },
});
