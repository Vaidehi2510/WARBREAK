export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function safeJson(res: Response) {
  if (!res.ok) throw new Error(await res.text());
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
    body: JSON.stringify({ game_id: gameId, blue_action: action, action }),
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

export async function identifyOpponentAssets(scenario: string, selectedAssets: any[]) {
  const payload = { scenario, adversary: scenario.includes("NATO") ? "Russian forces" : scenario.includes("Embassy") ? "local hostile forces" : scenario.includes("Cyber") ? "state-backed cyber actor" : "PLA", blue_assets: selectedAssets };
  const paths = ["/intel", "/api/intel", "/opponent-assets"];
  for (const path of paths) {
    try {
      const res = await fetch(`${API_BASE}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (res.ok) return res.json();
    } catch (_) {}
  }
  return null;
}
