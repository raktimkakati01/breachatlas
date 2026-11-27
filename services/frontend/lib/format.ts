// Shared display helpers.

export const fmt = (n: number) => n.toLocaleString("en-US");

export const cleanOrg = (s: string) => s.replace(/\s*\(fictional\)/i, "");

export function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso + "T00:00:00");
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

const titleize = (s: string) =>
  s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export const confirmationLabel = titleize;
export const rootCauseLabel = titleize;
export const phaseLabel = titleize;

export function relationshipLabel(rel: string): string {
  switch (rel) {
    case "would_have_prevented":
      return "Would have prevented";
    case "would_have_limited":
      return "Would have limited impact";
    case "not_applicable":
      return "Not applicable";
    default:
      return titleize(rel);
  }
}
