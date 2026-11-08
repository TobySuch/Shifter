import { vi } from "vitest";

// Minimal stand-in for a FilePond instance, enough to drive UploadPage.
export function createFakePond() {
  const handlers = {};
  const pond = {
    options: null,
    element: document.createElement("div"),
    files: [],
    getFiles: () => pond.files,
    on: (event, handler) => {
      (handlers[event] ||= []).push(handler);
    },
    emit: (event, ...args) => handlers[event]?.forEach((h) => h(...args)),
    removeFiles: vi.fn(async () => {
      pond.files = [];
      pond.emit("removefile");
      pond.emit("updatefiles");
    }),
    addFile: vi.fn(async (file) => {
      pond.files.push({ filename: file.name, file });
      pond.emit("addfile", null);
      pond.emit("updatefiles");
    }),
    setOptions: vi.fn(),
    destroy: vi.fn(),
    // Test helpers
    simulateAdd(file, error = null) {
      if (!error) {
        pond.files.push({ filename: file.name, file });
      }
      pond.emit("addfile", error);
      pond.emit("updatefiles");
    },
    simulateRemoveAll() {
      pond.files = [];
      pond.emit("removefile");
      pond.emit("updatefiles");
    },
  };
  const factory = vi.fn((options) => {
    pond.options = options;
    return pond;
  });
  return { pond, factory };
}
