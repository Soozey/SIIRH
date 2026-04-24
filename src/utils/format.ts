const integerFormatter = new Intl.NumberFormat("fr-FR", {
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
  useGrouping: true,
});

const decimalFormatter = new Intl.NumberFormat("fr-FR", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
  useGrouping: true,
});

function normalizeSpaces(value: string): string {
  return value.replace(/\u202f/g, " ").replace(/\u00a0/g, " ");
}

export function formatNumber(value: number | string | null | undefined, digits = 2): string {
  const numericValue = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numericValue)) return "-";
  const formatter = digits === 0 ? integerFormatter : decimalFormatter;
  return normalizeSpaces(formatter.format(numericValue));
}

export function formatCount(value: number | string | null | undefined): string {
  return formatNumber(value, 0);
}

