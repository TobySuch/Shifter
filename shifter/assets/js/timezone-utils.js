let dtFormat = new Intl.DateTimeFormat(undefined, {
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
});

function convertToLocalTime(element) {
  const isoTime = new Date(element.getAttribute("data-iso-time"));
  const localTime = dtFormat.format(isoTime);
  element.textContent = localTime;
}

document.addEventListener("DOMContentLoaded", function () {
  document
    .querySelectorAll(".localized-time[data-iso-time]")
    .forEach(function (element) {
      convertToLocalTime(element);
    });
});
