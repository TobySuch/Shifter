// Global JS for Shifter required by all pages.

import "../css/style.css";
import "flowbite";
import Alpine from "alpinejs";

window.Alpine = Alpine;

Alpine.data("clipboardNotification", (downloadUrl, filename = null) => ({
  downloadUrl,
  filename,
  showNotification: false,
  showQRCode: false,
  qrCodeDataUrl: null,
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
      },
    );
  },
  async generateQRCode() {
    if (!this.qrCodeDataUrl) {
      try {
        const QRCode = (await import("qrcode")).default;
        this.qrCodeDataUrl = await QRCode.toDataURL(this.downloadUrl, {
          width: 256,
          margin: 2,
          color: {
            dark: "#000000",
            light: "#FFFFFF",
          },
        });
      } catch (err) {
        console.error("Could not generate QR code: ", err);
        return;
      }
    }
    this.showQRCode = !this.showQRCode;
  },
  downloadQRCodeImage() {
    if (!this.qrCodeDataUrl) return;
    const link = document.createElement("a");
    const downloadName = this.filename
      ? `${this.filename}-qrcode.png`
      : "qrcode.png";
    link.download = downloadName;
    link.href = this.qrCodeDataUrl;
    link.click();
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
  minOffsetMs: null,
  maxOffsetMs: null,
  intervalId: null,
  init() {
    const now = Date.now();
    if (minIso) {
      this.minOffsetMs = new Date(minIso).getTime() - now;
    }
    if (maxIso) {
      this.maxOffsetMs = new Date(maxIso).getTime() - now;
    }

    convertDateTimeLocalFormElementToLocalTime(this.$el, {
      initialIso,
      minIso,
      maxIso,
    });

    this.updateRelativeBounds();
    this.intervalId = setInterval(() => {
      this.updateRelativeBounds();
    }, 1000);
    this.$el.addEventListener(
      "alpine:destroy",
      () => {
        if (this.intervalId) {
          clearInterval(this.intervalId);
        }
      },
      { once: true },
    );
  },
  updateRelativeBounds() {
    if (this.minOffsetMs !== null) {
      const minTime = new Date(Date.now() + this.minOffsetMs);
      this.$el.min = convertDateToFormFieldFormat(minTime);
    }
    if (this.maxOffsetMs !== null) {
      const maxTime = new Date(Date.now() + this.maxOffsetMs);
      this.$el.max = convertDateToFormFieldFormat(maxTime);
    }
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
  { initialIso, minIso, maxIso } = {},
) {
  const initialValue = initialIso || input.getAttribute("data-initial-iso");
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
