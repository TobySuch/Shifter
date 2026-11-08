import * as FilePond from "filepond";
import FilePondPluginFileValidateSize from "filepond-plugin-file-validate-size";
import "filepond/dist/filepond.min.css";

FilePond.registerPlugin(FilePondPluginFileValidateSize);

// Creates a detached FilePond instance; the caller appends pond.element.
export function createFilePond(options) {
  return FilePond.create(options);
}
