import { Blob as NodeBlob } from "node:buffer";

// jsdom's File has no working stream(); give test files one backed by
// Node's Blob so streaming code sees real bytes.
export function streamableFile(content, name, lastModified = Date.UTC(2026, 0, 1)) {
  const file = new File([content], name, { lastModified });
  Object.defineProperty(file, "stream", {
    value: () => new NodeBlob([content]).stream(),
  });
  return file;
}

export async function readAll(stream) {
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

export function streamOf(...parts) {
  return new ReadableStream({
    start(controller) {
      parts.forEach((part) => controller.enqueue(new Uint8Array(part)));
      controller.close();
    },
  });
}
