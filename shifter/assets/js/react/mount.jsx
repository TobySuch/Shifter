// Mounts React "islands" into server-rendered Django pages.
//
// A template opts in with a mount node and a json_script props block:
//
//   {{ props|json_script:"upload-props" }}
//   <div data-react-island="UploadPage" data-props-id="upload-props"></div>
//
// Each Vite entry passes a registry of the components it bundles, so a page
// only loads the islands it actually uses.

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

export function readIslandProps(element) {
  const propsId = element.dataset.propsId;
  if (!propsId) {
    return {};
  }

  const script = element.ownerDocument.getElementById(propsId);
  if (!script) {
    throw new Error(`React island props script "#${propsId}" not found.`);
  }

  return JSON.parse(script.textContent);
}

export function mountIslands(registry, root = document) {
  const mounted = [];

  root.querySelectorAll("[data-react-island]").forEach((element) => {
    const Component = registry[element.dataset.reactIsland];
    // Islands that belong to another entry point are left alone.
    if (!Component || element.dataset.reactMounted === "true") {
      return;
    }

    const props = readIslandProps(element);
    const reactRoot = createRoot(element);
    reactRoot.render(
      <StrictMode>
        <Component {...props} />
      </StrictMode>,
    );
    element.dataset.reactMounted = "true";
    mounted.push(reactRoot);
  });

  return mounted;
}

export function onDocumentReady(callback) {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", callback, { once: true });
  } else {
    callback();
  }
}
