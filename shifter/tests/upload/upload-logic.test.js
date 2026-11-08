import JSZip from "jszip";
import { describe, expect, it } from "vitest";

import {
  appendUploadFields,
  combineFiles,
  describeAddFileError,
  GENERIC_SERVER_ERROR,
  parseUploadError,
  parseUploadResponse,
  zipFileName,
} from "../../assets/js/upload/upload-logic.js";
import { createFakePond } from "./fake-pond.js";

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

describe("combineFiles", () => {
  it("rejects when there are no files", async () => {
    const { pond } = createFakePond();
    await expect(combineFiles(pond, "x")).rejects.toThrow(/at least one/);
  });

  it("leaves a single file untouched", async () => {
    const { pond } = createFakePond();
    pond.files = [{ filename: "a.txt", file: new File(["a"], "a.txt") }];

    await combineFiles(pond, "x");

    expect(pond.removeFiles).not.toHaveBeenCalled();
    expect(pond.addFile).not.toHaveBeenCalled();
  });

  it("replaces multiple files with a single named zip", async () => {
    const { pond } = createFakePond();
    pond.files = [
      { filename: "a.txt", file: new File(["alpha"], "a.txt") },
      { filename: "b.txt", file: new File(["bravo"], "b.txt") },
    ];

    await combineFiles(pond, "bundle");

    expect(pond.removeFiles).toHaveBeenCalledOnce();
    const zipFile = pond.addFile.mock.calls[0][0];
    expect(zipFile.name).toBe("bundle.zip");
    expect(zipFile.type).toBe("application/zip");

    const zip = await JSZip.loadAsync(await zipFile.arrayBuffer());
    expect(Object.keys(zip.files).sort()).toEqual(["a.txt", "b.txt"]);
    expect(await zip.file("b.txt").async("string")).toBe("bravo");
  });
});

describe("appendUploadFields", () => {
  it("sends expiry as UTC ISO when enabled", () => {
    const formData = appendUploadFields(new FormData(), {
      enableExpiry: true,
      expiryValue: "2030-01-02T03:04",
      csrfToken: "tok",
    });

    // Tests run with TZ=UTC (see tests/setup.js).
    expect(formData.get("expiry_datetime")).toBe("2030-01-02T03:04:00.000Z");
    expect(formData.get("enable_expiry")).toBe("on");
    expect(formData.get("csrfmiddlewaretoken")).toBe("tok");
  });

  it("omits expiry when disabled", () => {
    const formData = appendUploadFields(new FormData(), {
      enableExpiry: false,
      expiryValue: "2030-01-02T03:04",
      csrfToken: "tok",
    });

    expect(formData.has("expiry_datetime")).toBe(false);
    expect(formData.get("enable_expiry")).toBe("");
  });

  it("omits an unparseable expiry", () => {
    const formData = appendUploadFields(new FormData(), {
      enableExpiry: true,
      expiryValue: "not a date",
      csrfToken: "tok",
    });

    expect(formData.has("expiry_datetime")).toBe(false);
  });
});

describe("parseUploadResponse", () => {
  it("returns the redirect url", () => {
    expect(parseUploadResponse('{"redirect_url": "/files/abc"}')).toBe(
      "/files/abc",
    );
  });
});

describe("parseUploadError", () => {
  it("attributes expiry errors to the expiry input", () => {
    expect(
      parseUploadError('{"errors": {"expiry_datetime": ["Too far"]}}'),
    ).toEqual({ messages: ["Too far"], source: "expiry" });
  });

  it("attributes file errors to the file input", () => {
    expect(
      parseUploadError('{"errors": {"file_content": ["Too big"]}}'),
    ).toEqual({ messages: ["Too big"], source: "file" });
  });

  it("treats other errors as server errors", () => {
    expect(parseUploadError('{"errors": {"__all__": ["Nope"]}}')).toEqual({
      messages: ["Nope"],
      source: "server",
    });
  });

  it("falls back to a generic message for non-JSON responses", () => {
    expect(parseUploadError("<html>502 Bad Gateway</html>")).toEqual({
      messages: [GENERIC_SERVER_ERROR],
      source: "server",
    });
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
