// Keep date/time formatting stable across machines.
process.env.TZ = "UTC";

// Adds DOM matchers such as toBeInTheDocument() to Vitest's expect.
import "@testing-library/jest-dom/vitest";
