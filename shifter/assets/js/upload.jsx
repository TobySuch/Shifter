// Entry point for the upload page's React island.

import { mountIslands, onDocumentReady } from "./react/mount.jsx";
import UploadPage from "./upload/UploadPage.jsx";

onDocumentReady(() => mountIslands({ UploadPage }));
