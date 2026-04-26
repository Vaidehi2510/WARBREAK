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
  const adversary = scenario.includes("NATO") ? "Russian forces" 
    : scenario.includes("Embassy") ? "local hostile forces" 
    : scenario.includes("Cyber") ? "state-backed cyber actor" 
    : "PLA";
  
  const payload = { 
    scenario, 
    adversary, 
    blue_assets: selectedAssets.map((a: any) => a.name || a) 
  };

  const res = await fetch(`${API_BASE}/intel`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  
  if (!res.ok) throw new Error(`Intel API error: ${res.status}`);
  return res.json();
}
