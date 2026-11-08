import { act } from "react";
import { afterEach, describe, expect, it } from "vitest";

import { mountIslands, readIslandProps } from "../../assets/js/react/mount.jsx";

function Greeting({ name }) {
  return <p>Hello {name}</p>;
}

let roots = [];

afterEach(() => {
  act(() => roots.forEach((root) => root.unmount()));
  roots = [];
  document.body.innerHTML = "";
});

describe("readIslandProps", () => {
  it("parses props from the referenced json_script block", () => {
    document.body.innerHTML = `
      <script id="p" type="application/json">{"name": "<b>Shifter</b>"}</script>
      <div data-react-island="Greeting" data-props-id="p"></div>`;
    const el = document.querySelector("[data-react-island]");
    expect(readIslandProps(el)).toEqual({ name: "<b>Shifter</b>" });
  });

  it("returns empty props when no props id is given", () => {
    document.body.innerHTML = `<div data-react-island="Greeting"></div>`;
    const el = document.querySelector("[data-react-island]");
    expect(readIslandProps(el)).toEqual({});
  });

  it("throws when the props script is missing", () => {
    document.body.innerHTML = `<div data-react-island="Greeting" data-props-id="nope"></div>`;
    const el = document.querySelector("[data-react-island]");
    expect(() => readIslandProps(el)).toThrow(/nope/);
  });
});

describe("mountIslands", () => {
  it("renders registered components with their props", () => {
    document.body.innerHTML = `
      <script id="p" type="application/json">{"name": "World"}</script>
      <div data-react-island="Greeting" data-props-id="p"></div>`;

    act(() => {
      roots = mountIslands({ Greeting });
    });

    expect(document.body.textContent).toContain("Hello World");
    expect(roots).toHaveLength(1);
  });

  it("ignores islands not in the registry and never mounts twice", () => {
    document.body.innerHTML = `
      <div data-react-island="Greeting"></div>
      <div data-react-island="SomethingElse"></div>`;

    act(() => {
      roots = mountIslands({ Greeting });
    });
    let second;
    act(() => {
      second = mountIslands({ Greeting });
    });

    expect(roots).toHaveLength(1);
    expect(second).toHaveLength(0);
    expect(
      document.querySelector('[data-react-island="SomethingElse"]').innerHTML,
    ).toBe("");
  });
});
