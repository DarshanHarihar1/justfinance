export function parseAmount(value: number | string): number {
  if (typeof value === "number") return value;
  return Number.parseFloat(value);
}

/** INR display — whole rupees by default. */
export function formatINR(amount: number | string, fractionDigits = 0): string {
  const n = parseAmount(amount);
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: fractionDigits,
    minimumFractionDigits: fractionDigits,
  }).format(n);
}

/** Exact paise on review rows. */
export function formatINRDetailed(amount: number | string): string {
  const n = parseAmount(amount);
  const hasPaise = Math.round(n * 100) % 100 !== 0;
  return formatINR(n, hasPaise ? 2 : 0);
}

export function formatDate(iso: string): string {
  const d = new Date(iso.includes("T") ? iso : `${iso}T00:00:00`);
  const now = new Date();
  const sameYear = d.getFullYear() === now.getFullYear();
  return d.toLocaleDateString("en-IN", {
    month: "short",
    day: "numeric",
    ...(sameYear ? {} : { year: "numeric" }),
  });
}

export function formatPeriod(start: string, end: string): string {
  return `${formatDate(start)} – ${formatDate(end)}`;
}

export function formatTime(time: string | null): string {
  if (!time) return "";
  const [h, m] = time.split(":");
  const d = new Date();
  d.setHours(Number.parseInt(h, 10), Number.parseInt(m, 10), 0);
  return d.toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" });
}

export function formatRelativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  const diff = Date.now() - then;
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 48) return `${hours} hr ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days} day${days === 1 ? "" : "s"} ago`;
  const months = Math.floor(days / 30);
  return `${months} mo ago`;
}
