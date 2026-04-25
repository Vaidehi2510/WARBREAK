const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export type Assumption = {
  id: string; text: string; category: string;
  confidence: number; criticality: number; fragility: number;
  basis: string; doctrine_ref: string; dependencies: string[];
  cascade_effect: string;
  status: 'untested' | 'stressed' | 'broken' | 'validated';
  turn_broken?: number;
};

export type GameEvent = {
  turn: number; title: string; description: string;
  blue_move: string; red_move: string;
  ghost_reasoning: string; ghost_state_text: string;
  targeted_assumption_id: string; broken_chain: string[];
  metric_deltas: Record<string, number>; options: string[];
};

export type GameState = {
  id: string; plan: string; turn: number; max_turns: number;
  status: 'active' | 'failed' | 'completed';
  metrics: Record<string, number>;
  assumptions: Assumption[]; events: GameEvent[];
};

export type AutopsyReport = {
  game_id: string; status: string; turns: number;
  final_metrics: Record<string, number>; report: string;
  root_causes: string[]; assumptions_broken: number;
  assumptions_stressed: number;
  escalation_gates: Record<string, boolean>;
  lessons: string[]; recommendation: string;
};

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const r = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json' }, ...options,
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || 'Request failed');
  }
  return r.json();
}

export const createGame = (plan: string) =>
  req<GameState>('/games', { method: 'POST', body: JSON.stringify({ plan }) });
export const getGame = (id: string) => req<GameState>(`/games/${id}`);
export const playTurn = (game_id: string, player_action: string) =>
  req<GameState>('/turn', { method: 'POST', body: JSON.stringify({ game_id, player_action }) });
export const getAutopsy = (id: string) => req<AutopsyReport>(`/autopsy/${id}`);
