// Framework-free pieces of the upload flow, kept separate from the React
// component so they can be unit tested directly.

import JSZip from "jszip";

import { flattenErrors } from "../react/api.js";

export const STAY_ON_PAGE_MESSAGE =
  "Stay on this page until upload is finished.";
export const GENERIC_UPLOAD_ERROR = "Error during upload.";
export const GENERIC_SERVER_ERROR = "Upload failed. Please try again.";
export const DEFAULT_ZIP_NAME = "combined";

export function zipFileName(name) {
  const trimmed = (name || "").trim().replace(/\.zip$/i, "");
  return `${trimmed || DEFAULT_ZIP_NAME}.zip`;
}

// If more than one file is queued, replace them with a single zip archive so
// the backend always receives one file.
export async function combineFiles(pond, zipName) {
  const files = pond.getFiles();

  if (files.length === 0) {
    throw new Error("Select at least one file to upload");
  }

  if (files.length === 1) {
    return;
  }

  const zip = new JSZip();
  files.forEach((item) => {
    zip.file(item.filename, item.file, { binary: true });
  });
  const blob = await zip.generateAsync({ type: "blob" });

  await pond.removeFiles();
  await pond.addFile(
    new File([blob], zipFileName(zipName), { type: "application/zip" }),
  );
}

// Adds the non-file form fields FileUploadForm expects to FilePond's request.
export function appendUploadFields(
  formData,
  { enableExpiry, expiryValue, csrfToken },
) {
  if (enableExpiry && expiryValue) {
    // expiryValue is a datetime-local value in the user's timezone; send it
    // to the server as an unambiguous UTC ISO string.
    const expiry = new Date(expiryValue);
    if (!Number.isNaN(expiry.getTime())) {
      formData.append("expiry_datetime", expiry.toISOString());
    }
  }

  formData.append("csrfmiddlewaretoken", csrfToken ?? "");
  formData.append("enable_expiry", enableExpiry ? "on" : "");
  return formData;
}

export function parseUploadResponse(responseText) {
  return JSON.parse(responseText).redirect_url;
}

// Turns FileUploadView's JSON error payload into alert messages, noting which
// input caused the error so it can be cleared when that input is fixed.
export function parseUploadError(responseText) {
  let data;
  try {
    data = JSON.parse(responseText);
  } catch {
    return { messages: [GENERIC_SERVER_ERROR], source: "server" };
  }

  const errors = data?.errors;
  const messages = flattenErrors(errors);
  if (messages.length === 0) {
    return { messages: [GENERIC_SERVER_ERROR], source: "server" };
  }

  let source = "server";
  if (errors.expiry_datetime) {
    source = "expiry";
  } else if (errors.file_content) {
    source = "file";
  }

  return { messages, source };
}

// FilePond reports add-file errors as a string or as {main, sub}.
export function describeAddFileError(error) {
  if (typeof error === "string") {
    return error;
  }
  return error?.main || error?.message || "File could not be added.";
}
