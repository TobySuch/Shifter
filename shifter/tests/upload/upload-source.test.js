import JSZip from "jszip";
import { describe, expect, it } from "vitest";

import { buildUploadSource } from "../../assets/js/upload/upload-source.js";
import { readAll, streamableFile } from "./test-files.js";

const item = (content, name) => ({
  filename: name,
  file: streamableFile(content, name),
});

describe("buildUploadSource", () => {
  it("rejects an empty selection", () => {
    expect(() => buildUploadSource([], "x")).toThrow(/at least one/);
  });

  it("streams a single file as-is", async () => {
    const source = buildUploadSource([item("hello", "a.txt")], "ignored");

    expect(source.filename).toBe("a.txt");
    expect(source.size).toBe(5);
    expect(new TextDecoder().decode(await readAll(source.stream))).toBe(
      "hello",
    );
  });

  it("zips multiple files into a stream of exactly the predicted size", async () => {
    const source = buildUploadSource(
      [item("alpha", "a.txt"), item("bravo!", "b.txt")],
      "bundle",
    );

    expect(source.filename).toBe("bundle.zip");
    const bytes = await readAll(source.stream);
    expect(bytes.length).toBe(source.size);

    const zip = await JSZip.loadAsync(bytes);
    expect(Object.keys(zip.files).sort()).toEqual(["a.txt", "b.txt"]);
    expect(await zip.file("a.txt").async("string")).toBe("alpha");
    expect(await zip.file("b.txt").async("string")).toBe("bravo!");
  });
});
