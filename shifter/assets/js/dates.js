// Date helpers shared by the Alpine components and React islands.

const pad = (value) => String(value).padStart(2, "0");

// Formats a date as "YYYY-MM-DD HH:MM" in the user's local time. This is like
// an ISO format, but without a timezone, which is what Django's
// DATETIME_INPUT_FORMATS and datetime-local inputs expect.
export function convertDateToFormFieldFormat(date) {
  return (
    date.getFullYear() +
    "-" +
    pad(date.getMonth() + 1) +
    "-" +
    pad(date.getDate()) +
    " " +
    pad(date.getHours()) +
    ":" +
    pad(date.getMinutes())
  );
}

// Same as above but with the "T" separator, which is the canonical value
// format for a controlled <input type="datetime-local">.
export function toDateTimeLocalValue(date) {
  return convertDateToFormFieldFormat(date).replace(" ", "T");
}
