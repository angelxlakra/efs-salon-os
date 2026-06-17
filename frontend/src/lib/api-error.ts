// Safely turn any API/axios error into a human string for toasts.
//
// FastAPI validation errors (422) return `detail` as an ARRAY of objects
// ({type, loc, msg, input, url}). Passing that straight to toast.error/React
// renders an object as a child → "Minified React error #31". Always funnel
// error details through here.

interface ValidationItem {
  msg?: string;
  loc?: (string | number)[];
}

export function getApiErrorMessage(error: unknown, fallback = "Something went wrong"): string {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;

  if (typeof detail === "string" && detail.trim()) return detail;

  if (Array.isArray(detail)) {
    const msgs = (detail as ValidationItem[])
      .map((d) => {
        if (typeof d === "string") return d;
        const field = Array.isArray(d?.loc) ? d.loc[d.loc.length - 1] : undefined;
        return d?.msg ? (field ? `${field}: ${d.msg}` : d.msg) : null;
      })
      .filter(Boolean);
    if (msgs.length) return msgs.join("; ");
  }

  if (detail && typeof detail === "object") {
    const msg = (detail as { msg?: unknown }).msg;
    if (typeof msg === "string") return msg;
  }

  const message = (error as { message?: unknown })?.message;
  if (typeof message === "string" && message.trim()) return message;

  return fallback;
}
