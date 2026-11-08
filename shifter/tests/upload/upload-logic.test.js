import { describe, expect, it } from "vitest";

import {
  describeAddFileError,
  errorSource,
  expiryToIso,
  formatBytes,
  zipFileName,
} from "../../assets/js/upload/upload-logic.js";

describe("zipFileName", () => {
  it.each([
    ["holiday", "holiday.zip"],
    ["  holiday  ", "holiday.zip"],
    ["holiday.ZIP", "holiday.zip"],
    ["", "combined.zip"],
    [undefined, "combined.zip"],
  ])("%j -> %s", (input, expected) => {
    expect(zipFileName(input)).toBe(expected);
  });
});

describe("expiryToIso", () => {
  it("converts a local datetime-local value to UTC ISO", () => {
    // Tests run with TZ=UTC (see tests/setup.js).
    expect(expiryToIso(true, "2030-01-02T03:04")).toBe(
      "2030-01-02T03:04:00.000Z",
    );
  });

  it("returns null when expiry is disabled", () => {
    expect(expiryToIso(false, "2030-01-02T03:04")).toBeNull();
  });

  it("returns null for an empty or invalid value", () => {
    expect(expiryToIso(true, "")).toBeNull();
    expect(expiryToIso(true, "not a date")).toBeNull();
  });
});

describe("errorSource", () => {
  it.each([
    [{ expiry_datetime: ["x"] }, "expiry"],
    [{ size: ["x"] }, "file"],
    [{ filename: ["x"] }, "file"],
    [{ __all__: ["x"] }, "server"],
    [null, "server"],
  ])("%j -> %s", (errors, expected) => {
    expect(errorSource(errors)).toBe(expected);
  });
});

describe("describeAddFileError", () => {
  it.each([
    ["Too big", "Too big"],
    [{ main: "File is too large", sub: "Max 1MB" }, "File is too large"],
    [new Error("boom"), "boom"],
    [{}, "File could not be added."],
  ])("%j -> %s", (input, expected) => {
    expect(describeAddFileError(input)).toBe(expected);
  });
});

describe("formatBytes", () => {
  it.each([
    [0, "0 B"],
    [1023, "1023 B"],
    [1024, "1.0 KB"],
    [5 * 1024 * 1024 * 1024, "5.0 GB"],
  ])("%d -> %s", (input, expected) => {
    expect(formatBytes(input)).toBe(expected);
  });
});
