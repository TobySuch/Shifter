// Turns the files queued in FilePond into one stream to upload. Several files
// are zipped on the fly with client-zip, so the archive is never held in
// memory as a whole.

import { makeZip, predictLength } from "client-zip";

import { zipFileName } from "./upload-logic.js";

// items: FilePond file items ({ filename, file }).
export function buildUploadSource(items, zipName) {
  if (items.length === 0) {
    throw new Error("Select at least one file to upload");
  }

  if (items.length === 1) {
    const [{ filename, file }] = items;
    return { filename, size: file.size, stream: file.stream() };
  }

  const entries = items.map(({ filename, file }) => ({
    name: filename,
    size: file.size,
    lastModified: new Date(file.lastModified),
  }));

  return {
    filename: zipFileName(zipName),
    // The server needs the final size before the first byte is sent.
    // client-zip stores files uncompressed, so this is exact.
    size: Number(predictLength(entries)),
    stream: makeZip(
      entries.map((entry, index) => ({
        ...entry,
        input: items[index].file.stream(),
      })),
    ),
  };
}
