import { describe, expect, it } from "vitest";

import {
  convertDateTimeLocalFormElementToLocalTime,
  convertTextElementToLocalTime,
} from "../assets/js/shifter.js";

function buildLocalFormFieldValue(date) {
  const pad = (value) => String(value).padStart(2, "0");
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

const toLocalInputValue = (date) => {
  // datetime-local inputs normalize values to use "T" when read back.
  return buildLocalFormFieldValue(date).replace(" ", "T");
};

const toLocalAttributeValue = (date) => buildLocalFormFieldValue(date);

describe("convertTextElementToLocalTime", () => {
  it("formats ISO timestamps to localized text", () => {
    const isoString = "2024-05-10T12:34:00Z";
    const element = document.createElement("span");
    element.setAttribute("data-iso-time", isoString);

    convertTextElementToLocalTime(element);

    const expected = new Intl.DateTimeFormat(undefined, {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(isoString));

    expect(element.textContent).toBe(expected);
  });
});

describe("convertDateTimeLocalFormElementToLocalTime", () => {
  it("populates value, min, and max attributes from ISO sources", () => {
    const input = document.createElement("input");
    input.type = "datetime-local";
    input.setAttribute("data-initial-iso", "2024-06-15T09:45:00Z");
    input.setAttribute("data-min-iso", "2024-06-01T00:00:00Z");
    input.setAttribute("data-max-iso", "2024-06-30T23:59:00Z");

    convertDateTimeLocalFormElementToLocalTime(input);

    expect(input.value).toBe(
      toLocalInputValue(new Date("2024-06-15T09:45:00Z")),
    );
    expect(input.min).toBe(
      toLocalAttributeValue(new Date("2024-06-01T00:00:00Z")),
    );
    expect(input.max).toBe(
      toLocalAttributeValue(new Date("2024-06-30T23:59:00Z")),
    );
  });

  it("leaves max unset when no limit is provided", () => {
    const input = document.createElement("input");
    input.type = "datetime-local";
    input.setAttribute("data-initial-iso", "2024-01-02T03:04:00Z");
    input.setAttribute("data-min-iso", "2024-01-01T00:00:00Z");

    convertDateTimeLocalFormElementToLocalTime(input);

    expect(input.value).toBe(
      toLocalInputValue(new Date("2024-01-02T03:04:00Z")),
    );
    expect(input.min).toBe(
      toLocalAttributeValue(new Date("2024-01-01T00:00:00Z")),
    );
    expect(input.max).toBe("");
  });
});
