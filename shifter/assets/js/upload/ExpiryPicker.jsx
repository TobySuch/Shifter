import { useRelativeBounds } from "./useRelativeBounds.js";

export default function ExpiryPicker({
  allowOptionalExpiry,
  enableExpiry,
  onEnableExpiryChange,
  value,
  onValueChange,
  minIso,
  maxIso,
}) {
  const bounds = useRelativeBounds(minIso, maxIso);

  return (
    <div className="flex flex-col gap-2 w-full xl:w-auto">
      {allowOptionalExpiry && (
        <div className="flex items-center">
          <label
            htmlFor="id_enable_expiry"
            className="mr-2 font-medium text-gray-900"
          >
            Set file expiry:
          </label>
          <input
            type="checkbox"
            name="enable_expiry"
            id="id_enable_expiry"
            className="w-6 h-6 my-2.5 text-primary bg-sky-100 border-sky-200 rounded focus:ring-primary focus:ring-2 cursor-pointer"
            checked={enableExpiry}
            onChange={(event) => onEnableExpiryChange(event.target.checked)}
          />
        </div>
      )}

      {enableExpiry && (
        <div className="flex items-center w-full xl:w-auto">
          <label htmlFor="id_expiry_datetime" className="font-medium mr-2">
            Expiry:
          </label>
          <input
            type="datetime-local"
            name="expiry_datetime"
            id="id_expiry_datetime"
            className="input-primary flex-grow"
            value={value}
            min={bounds.min}
            max={bounds.max}
            onChange={(event) =>
              onValueChange(event.target.value, event.target)
            }
          />
        </div>
      )}
    </div>
  );
}
