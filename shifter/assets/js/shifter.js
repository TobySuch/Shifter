// Global JS for Shifter required by all pages.

import "../css/style.css";
import "flowbite";
import Alpine from "alpinejs";

window.Alpine = Alpine;

Alpine.data("clipboardNotification", (downloadUrl) => ({
  downloadUrl,
  showNotification: false,
  copyToClipboard() {
    navigator.clipboard.writeText(this.downloadUrl).then(
      () => {
        this.showNotification = true;
        setTimeout(() => {
          this.showNotification = false;
        }, 3000);
      },
      (err) => {
        console.error("Could not copy link to clipboard: ", err);
      }
    );
  },
}));

Alpine.data("localizedTime", (isoTime) => ({
  init() {
    if (isoTime) {
      this.$el.setAttribute("datetime", isoTime);
    }
    convertTextElementToLocalTime(this.$el);
  },
}));

Alpine.data("localizedDateTimeInput", (initialIso, minIso, maxIso) => ({
  init() {
    convertDateTimeLocalFormElementToLocalTime(this.$el, {
      initialIso,
      minIso,
      maxIso,
    });
  },
}));

let dtFormat = new Intl.DateTimeFormat(undefined, {
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
});

// This converts a date object to a string in the format "YYYY-MM-DD HH:MM"
// This is like an ISO format, but we don't want the timezone, we need it in the
// users local time.
function convertDateToFormFieldFormat(date) {
  return (
    date.getFullYear() +
    "-" +
    ("0" + (date.getMonth() + 1)).slice(-2) +
    "-" +
    ("0" + date.getDate()).slice(-2) +
    " " +
    ("0" + date.getHours()).slice(-2) +
    ":" +
    ("0" + date.getMinutes()).slice(-2)
  );
}

export function convertTextElementToLocalTime(element) {
  const isoValue =
    element.getAttribute("datetime") || element.getAttribute("data-iso-time");
  const isoTime = new Date(isoValue);
  const localTime = dtFormat.format(isoTime);
  element.textContent = localTime;
}

export function convertDateTimeLocalFormElementToLocalTime(
  input,
  { initialIso, minIso, maxIso } = {}
) {
  const initialValue =
    initialIso || input.getAttribute("data-initial-iso");
  const minValue = minIso || input.getAttribute("data-min-iso");
  const maxValue = maxIso || input.getAttribute("data-max-iso");

  if (!initialValue) {
    return;
  }

  const initialVal = new Date(initialValue);
  input.value = convertDateToFormFieldFormat(initialVal);

  if (minValue) {
    const minVal = new Date(minValue);
    input.min = convertDateToFormFieldFormat(minVal);
  }

  if (maxValue) {
    const maxVal = new Date(maxValue);
    input.max = convertDateToFormFieldFormat(maxVal);
  }
}

Alpine.start();
