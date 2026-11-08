import { formatBytes } from "./upload-logic.js";

export default function UploadProgress({ sent, total }) {
  const percent = total > 0 ? Math.floor((sent / total) * 100) : 100;

  return (
    <div className="flex flex-col gap-1 py-2">
      <div
        className="w-full h-2.5 bg-gray-200 rounded-full overflow-hidden"
        role="progressbar"
        aria-label="Upload progress"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
      >
        <div
          className="h-full bg-primary rounded-full transition-[width]"
          style={{ width: `${percent}%` }}
        />
      </div>
      <div className="text-sm text-gray-700 text-center">
        {percent}% · {formatBytes(sent)} of {formatBytes(total)}
      </div>
    </div>
  );
}
