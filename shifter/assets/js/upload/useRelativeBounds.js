import { useEffect, useState } from "react";

import { toDateTimeLocalValue } from "../dates.js";

// The server sends min/max expiry as absolute times computed when the page
// was rendered. Keep them relative to "now" while the page stays open, so a
// tab left open for an hour still offers the same expiry window.
export function useRelativeBounds(minIso, maxIso, intervalMs = 1000) {
  const [offsets] = useState(() => {
    const now = Date.now();
    return {
      min: minIso ? new Date(minIso).getTime() - now : null,
      max: maxIso ? new Date(maxIso).getTime() - now : null,
    };
  });

  const compute = () => {
    const now = Date.now();
    return {
      min:
        offsets.min === null
          ? undefined
          : toDateTimeLocalValue(new Date(now + offsets.min)),
      max:
        offsets.max === null
          ? undefined
          : toDateTimeLocalValue(new Date(now + offsets.max)),
    };
  };

  const [bounds, setBounds] = useState(compute);

  useEffect(() => {
    const id = setInterval(() => {
      const next = compute();
      // Only re-render when the minute-resolution value actually changes.
      setBounds((prev) =>
        prev.min === next.min && prev.max === next.max ? prev : next,
      );
    }, intervalMs);
    return () => clearInterval(id);
    // offsets never change after mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs]);

  return bounds;
}
