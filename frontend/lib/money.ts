export function parseCents(value: string): number | null {
  const normalized = value.trim();
  if (!/^\d+(?:\.\d{0,2})?$/.test(normalized)) return null;

  const [whole, fraction = ""] = normalized.split(".");
  const cents = Number(whole) * 100 + Number(fraction.padEnd(2, "0"));
  return Number.isSafeInteger(cents) ? cents : null;
}

export function parseSignedCents(value: string): number | null {
  const normalized = value.trim();
  if (!/^-?\d+(?:\.\d{1,2})?$/.test(normalized)) return null;
  const negative = normalized.startsWith("-");
  const cents = parseCents(negative ? normalized.slice(1) : normalized);
  return cents === null ? null : negative ? -cents : cents;
}

export function formatCents(cents: number): string {
  return new Intl.NumberFormat("th-TH", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(cents / 100);
}

export function centsToDecimalString(cents: number): string {
  const sign = cents < 0 ? "-" : "";
  const absolute = Math.abs(cents);
  return `${sign}${Math.floor(absolute / 100)}.${String(absolute % 100).padStart(2, "0")}`;
}

export function splitEqualCents(totalCents: number, userIds: number[]): Map<number, number> {
  const result = new Map<number, number>();
  if (userIds.length === 0 || !Number.isSafeInteger(totalCents) || totalCents < 0) {
    return result;
  }

  const base = Math.floor(totalCents / userIds.length);
  const remainder = totalCents % userIds.length;
  userIds.forEach((userId, index) => {
    result.set(userId, base + (index < remainder ? 1 : 0));
  });
  return result;
}