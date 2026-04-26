export type AssumptionStatus = "untested" | "stressed" | "broken" | "validated";

export type Assumption = {
  id: string;
  text: string;
  category: string;
  confidence: number;
  criticality: number;
  fragility: number;
  basis: string;
  doctrine_ref: string;
  dependencies: string[];
  cascade_effect: string;
  status: AssumptionStatus;
  turn_broken?: number | null;
};

export type GameEvent = {
  turn: number;
  title: string;
  description: string;
  blue_move: string;
  red_move: string;
  ghost_reasoning: string;
  ghost_state_text: string;
  targeted_assumption_id: string;
  broken_chain: string[];
  metric_deltas: Record<string, number>;
  options: string[];
};

export type GameState = {
  id: string;
  created_at: string;
  plan: string;
  assumptions: Assumption[];
  turn: number;
  max_turns: number;
  metrics: Record<string, number>;
  events: GameEvent[];
  status: "active" | "failed" | "completed";
  ghost_loss_aversion: number;
  ghost_escalation_threshold: number;
};

export type AutopsyReport = {
  status: string;
  turns: number;
  assumptions_broken: number;
  assumptions_stressed: number;
  final_metrics: Record<string, number>;
  assumptions: Assumption[];
  events?: GameEvent[];
  root_causes: string[];
  lessons?: string[];
  recommendation: string;
  report: string;
};

export const API_BASE = (
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  "/api"
).replace(/\/$/, "");

async function safeJson(res: Response) {
  const contentType = res.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");

  if (!res.ok) {
    const text = await res.text();
    if (isJson) try {
      const data = JSON.parse(text);
      const detail = data.detail;
      if (typeof detail === "string") throw new Error(detail);
      if (Array.isArray(detail)) {
        throw new Error(detail.map((item) => item.msg || JSON.stringify(item)).join(" "));
      }
    } catch (e) {
      if (e instanceof Error && e.message !== text) throw e;
    }
    if (contentType.includes("text/html")) {
      throw new Error(`API returned HTML instead of JSON from ${res.url}. Check frontend API proxy/backend URL.`);
    }
    throw new Error(text || `API request failed with status ${res.status}`);
  }

  if (!isJson) {
    throw new Error(`API returned ${contentType || "unknown content"} instead of JSON from ${res.url}.`);
  }

  return res.json();
}

export async function createGame(plan: string) {
  const res = await fetch(`${API_BASE}/games`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ plan }),
  });
  return safeJson(res);
}

export async function playTurn(gameId: string, action: string) {
  const res = await fetch(`${API_BASE}/turn`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ game_id: gameId, player_action: action }),
  });
  return safeJson(res);
}

export async function getGame(gameId: string) {
  const res = await fetch(`${API_BASE}/games/${gameId}`);
  return safeJson(res);
}

export async function getAutopsy(gameId: string) {
  const res = await fetch(`${API_BASE}/autopsy/${gameId}`);
  return safeJson(res);
}

function assetName(asset: unknown) {
  if (typeof asset === "string") return asset;
  if (asset && typeof asset === "object") {
    const candidate = asset as { name?: unknown; id?: unknown };
    if (typeof candidate.name === "string") return candidate.name;
    if (typeof candidate.id === "string") return candidate.id;
  }
  return "";
}

export async function identifyOpponentAssets(scenario: string, selectedAssets: unknown[]) {
  const payload = {
    scenario,
    adversary: scenario.includes("NATO")
      ? "Russian forces"
      : scenario.includes("Embassy")
        ? "local hostile forces"
        : scenario.includes("Cyber")
          ? "state-backed cyber actor"
          : "PLA",
    blue_assets: selectedAssets.map(assetName).filter(Boolean),
  };
  const res = await fetch(`${API_BASE}/intel`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return safeJson(res);
}
