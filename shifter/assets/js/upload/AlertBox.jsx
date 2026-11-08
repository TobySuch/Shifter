const KIND_CLASSES = {
  info: "info-box",
  error: "error-box",
};

export default function AlertBox({ kind, messages }) {
  return (
    <div
      id={`${kind}-box`}
      className={`flex ${KIND_CLASSES[kind]}`}
      role="alert"
    >
      <svg
        aria-hidden="true"
        className="shrink-0 w-5 h-5"
        fill="currentColor"
        viewBox="0 0 20 20"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          fillRule="evenodd"
          d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
          clipRule="evenodd"
        />
      </svg>
      <span className="sr-only">{kind === "error" ? "Error" : "Info"}</span>
      <div
        id={`${kind}-box-message`}
        className="ml-3 text-sm font-medium text-center"
      >
        {messages.map((message, index) => (
          <div key={index}>{message}</div>
        ))}
      </div>
    </div>
  );
}
