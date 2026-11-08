// Small framework-free helpers for the upload page.

export const STAY_ON_PAGE_MESSAGE =
  "Stay on this page until upload is finished.";
export const GENERIC_UPLOAD_ERROR = "Error during upload.";
export const DEFAULT_ZIP_NAME = "combined";

export function zipFileName(name) {
  const trimmed = (name || "").trim().replace(/\.zip$/i, "");
  return `${trimmed || DEFAULT_ZIP_NAME}.zip`;
}

// expiryValue is a datetime-local value in the user's timezone; the server
// gets an unambiguous UTC ISO string, or null when there is no expiry.
export function expiryToIso(enableExpiry, expiryValue) {
  if (!enableExpiry || !expiryValue) {
    return null;
  }
  const expiry = new Date(expiryValue);
  return Number.isNaN(expiry.getTime()) ? null : expiry.toISOString();
}

// Which input a server-side validation error belongs to, so the alert can be
// cleared once the user fixes that input.
export function errorSource(errors) {
  if (errors?.expiry_datetime) {
    return "expiry";
  }
  if (errors?.size || errors?.filename) {
    return "file";
  }
  return "server";
}

// FilePond reports add-file errors as a string or as {main, sub}.
export function describeAddFileError(error) {
  if (typeof error === "string") {
    return error;
  }
  return error?.main || error?.message || "File could not be added.";
}

export function formatBytes(bytes) {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${unit === 0 ? value : value.toFixed(1)} ${units[unit]}`;
}
