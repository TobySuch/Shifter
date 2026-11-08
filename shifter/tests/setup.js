// Keep date/time formatting stable across machines.
process.env.TZ = "UTC";

// Adds DOM matchers such as toBeInTheDocument() to Vitest's expect.
import "@testing-library/jest-dom/vitest";

// Testing Library only auto-cleans when Vitest globals are enabled.
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => cleanup());
