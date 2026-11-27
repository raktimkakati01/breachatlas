// Thin client for the BreachAtlas read-only public API.
export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export type Stats = {
  breaches_tracked: number;
  records_exposed: number;
  countries: number;
  organizations: number;
  most_common_missing_control: string | null;
  pct_undisclosed_root_cause: number;
};

export type BreachSummary = {
  slug: string;
  organization: string;
  country: string;
  sector: string;
  date_disclosed: string;
  records_affected: number | null;
  confirmation_status: string;
  root_cause_status: string;
};

export type Technique = { technique_id: string; name: string; tactic: string | null };
export type AttackStep = { step_order: number; phase: string; description: string; techniques: Technique[] };
export type ControlLink = {
  relationship_type: string;
  control: { slug: string; name: string; cis_control_id: string | null; cis_safeguard: string | null };
};
export type BreachDetail = BreachSummary & {
  summary: string | null;
  attack_steps: AttackStep[];
  controls: ControlLink[];
  data_types: { slug: string; name: string }[];
};

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.json() as Promise<T>;
}

export const getStats = () => getJSON<Stats>("/stats");
export const listBreaches = () =>
  getJSON<{ total: number; items: BreachSummary[] }>("/breaches?limit=100");
export const getBreach = (slug: string) => getJSON<BreachDetail>(`/breaches/${slug}`);
