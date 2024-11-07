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

function convertTextElementToLocalTime(element) {
  const isoTime = new Date(element.getAttribute("data-iso-time"));
  const localTime = dtFormat.format(isoTime);
  element.textContent = localTime;
}

function convertDateTimeLocalFormElementToLocalTime(input) {
  const initialVal = new Date(input.getAttribute("data-initial-iso"));
  input.value = convertDateToFormFieldFormat(initialVal);

  const minVal = new Date(input.getAttribute("data-min-iso"));
  input.min = convertDateToFormFieldFormat(minVal);

  const maxVal = new Date(input.getAttribute("data-max-iso"));
  input.max = convertDateToFormFieldFormat(maxVal);
}

document.addEventListener("DOMContentLoaded", function () {
  document
    .querySelectorAll(".localized-time[data-iso-time]")
    .forEach(function (element) {
      convertTextElementToLocalTime(element);
    });

  document
    .querySelectorAll("input.localized-time[type=datetime-local]")
    .forEach(function (input) {
      convertDateTimeLocalFormElementToLocalTime(input);
    });
});
