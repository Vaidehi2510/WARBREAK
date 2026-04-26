"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { getAutopsy, getGame } from "../../lib/api";

type AnyRecord = Record<string, any>;

type AssumptionStatus = "untested" | "stressed" | "broken" | "validated";

type AssumptionRow = {
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
  source: "fogline" | "mission";
  rank?: number;
  rank_score?: number;
  rank_reason?: string;
  targeted_count?: number;
  broken_chain_count?: number;
  validation_move?: string;
};

type HistoryEntry = {
  turn: number;
  action: string;
  red: string;
  ghost: string;
};

type DamageReport = {
  id?: string;
  turn: number;
  action: string;
  target: string;
  resource: string;
  damage: number;
  residual: number;
  recovery: string;
  recoveryHours: number;
  confidence: number;
  severity: string;
  effect: string;
  aftershock: string;
  source?: string;
  redDelta?: number;
  blueCost?: number;
  metricDeltas?: Record<string, number>;
  evidence?: string[];
};

type OpponentAsset = {
  name?: string;
  category?: string;
  confidence?: number;
  threat_to_blue?: string;
  capability?: string;
  counter?: string;
};

type AutopsyView = {
  scenario: string;
  status: string;
  turns: number;
  final_metrics: Record<string, number>;
  assumptions: AssumptionRow[];
  usingMissionSignals: boolean;
  history: HistoryEntry[];
  damageReports: DamageReport[];
  opponentAssets: OpponentAsset[];
  redUsed: string[];
  root_causes: string[];
  assumptions_broken: number;
  assumptions_stressed: number;
  recommendation: string;
  lessons: string[];
  report: string;
  warning: string;
};

const DEFAULT_METRICS: Record<string, number> = {
  intl_opinion: 50,
  us_domestic: 72,
  red_domestic: 61,
  allied_confidence: 58,
  blue_strength: 100,
  red_strength: 100,
};

const METRICS = [
  { key: "intl_opinion", label: "Int'l Opinion", color: "#4d9fff", hostile: false },
  { key: "us_domestic", label: "US Support", color: "#4d9fff", hostile: false },
  { key: "red_domestic", label: "Red Support", color: "#ff3c3c", hostile: true },
  { key: "allied_confidence", label: "Allied Conf.", color: "#00e87a", hostile: false },
  { key: "blue_strength", label: "Blue Force", color: "#4d9fff", hostile: false },
  { key: "red_strength", label: "Red Force", color: "#ff3c3c", hostile: true },
];

const TABS = [
  "ASSUMPTION RANK",
  "DECISION LOG",
  "GHOST COUNCIL",
  "FAILURE CHAIN",
  "WHAT IF",
  "RECOMMENDATIONS",
];

function safeParse<T>(raw: string | null, fallback: T): T {
  if (!raw) return fallback;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function normalizeReport(raw: unknown): AnyRecord {
  if (typeof raw === "string") return { report: raw };
  if (raw && typeof raw === "object") return raw as AnyRecord;
  return {};
}

function firstArray(...values: unknown[]): AnyRecord[] {
  for (const value of values) {
    if (Array.isArray(value) && value.length) {
      return value.filter((item): item is AnyRecord => Boolean(item) && typeof item === "object");
    }
  }
  return [];
}

function toNumber(value: unknown, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function clamp(value: number, min = 0, max = 100) {
  return Math.max(min, Math.min(max, Math.round(value)));
}

function cleanText(value: unknown, fallback = "") {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

function short(value: string, max = 96) {
  return value.length > max ? `${value.slice(0, max - 1)}...` : value;
}

function metricLabel(key: string) {
  return METRICS.find((metric) => metric.key === key)?.label || key.replace(/_/g, " ");
}

function metricTone(key: string, value: number) {
  const config = METRICS.find((metric) => metric.key === key);
  if (config?.hostile) {
    if (value >= 70) return "#ff3c3c";
    if (value <= 35) return "#00e87a";
    return "#ffaa00";
  }
  if (value <= 35) return "#ff3c3c";
  if (value >= 70) return "#00e87a";
  return config?.color || "#4d9fff";
}

function metricDeltaTone(key: string, delta: number) {
  const config = METRICS.find((metric) => metric.key === key);
  if (delta === 0) return "rgba(255,255,255,0.42)";
  const favorable = config?.hostile ? delta < 0 : delta > 0;
  return favorable ? "#00e87a" : "#ff3c3c";
}

function assumptionStatusTone(status: AssumptionStatus) {
  if (status === "broken") return "#ff3c3c";
  if (status === "stressed") return "#ffaa00";
  if (status === "validated") return "#00e87a";
  return "rgba(255,255,255,0.48)";
}

function assumptionScoreTone(score: number) {
  if (score >= 82) return "#ff3c3c";
  if (score >= 65) return "#ffaa00";
  return "#00e87a";
}

function validationMove(category: string) {
  const value = category.toLowerCase();
  if (value.includes("logistics") || value.includes("resource") || value.includes("supply")) {
    return "Set the sustainment threshold, owner, and backup route.";
  }
  if (value.includes("alliance") || value.includes("partner") || value.includes("permission") || value.includes("access")) {
    return "Make external support a go/no-go gate.";
  }
  if (value.includes("communications") || value.includes("digital") || value.includes("cyber")) {
    return "Rehearse the backup comms and manual fallback.";
  }
  if (value.includes("intelligence") || value.includes("information")) {
    return "Define the signal that disproves the estimate.";
  }
  if (value.includes("timing") || value.includes("tempo")) {
    return "Add a branch for delay, closure, or missed handoff.";
  }
  if (value.includes("civil") || value.includes("public")) {
    return "Validate movement and messaging through a trusted channel.";
  }
  return "Assign an owner, validation signal, and branch plan.";
}

function assumptionRankScore(item: AssumptionRow, targetedCount: number, brokenCount: number) {
  const statusBonus = item.status === "broken" ? 28 : item.status === "stressed" ? 18 : item.status === "validated" ? -8 : 8;
  const dependencyBonus = Math.min(14, item.dependencies.length * 4);
  const score =
    item.fragility * 0.58 +
    item.criticality * 0.24 +
    statusBonus +
    dependencyBonus +
    Math.min(18, targetedCount * 9) +
    Math.min(12, brokenCount * 6);
  return clamp(score);
}

function assumptionRankReason(item: AssumptionRow, targetedCount: number, brokenCount: number) {
  const pieces: string[] = [];
  if (item.status === "broken") pieces.push("broke during execution");
  else if (item.status === "stressed") pieces.push("was pressured by the opponent");
  else if (item.status === "validated") pieces.push("held under the recorded pressure");
  else pieces.push("is still unvalidated");
  if (targetedCount) pieces.push(`targeted ${targetedCount} time${targetedCount === 1 ? "" : "s"}`);
  if (brokenCount) pieces.push(`appeared in ${brokenCount} broken chain event${brokenCount === 1 ? "" : "s"}`);
  if (item.dependencies.length) pieces.push(`${item.dependencies.length} linked assumption${item.dependencies.length === 1 ? "" : "s"}`);
  return `${pieces.join("; ")}.`;
}

function rankAssumptionRows(rows: AssumptionRow[], events: AnyRecord[]) {
  const targeted = new Map<string, number>();
  const broken = new Map<string, number>();
  const brokenTurns = new Map<string, number>();

  events.forEach((event) => {
    const target = cleanText(event.targeted_assumption_id);
    if (target) targeted.set(target, (targeted.get(target) || 0) + 1);
    if (Array.isArray(event.broken_chain)) {
      event.broken_chain.forEach((id: unknown) => {
        const key = String(id);
        broken.set(key, (broken.get(key) || 0) + 1);
        if (!brokenTurns.has(key)) brokenTurns.set(key, toNumber(event.turn, 0));
      });
    }
  });

  return rows
    .map((item, index) => {
      const targetedCount = Math.max(toNumber(item.targeted_count, 0), targeted.get(item.id) || 0);
      const brokenCount = Math.max(toNumber(item.broken_chain_count, 0), broken.get(item.id) || 0);
      const status: AssumptionStatus =
        brokenCount > 0 ? "broken" :
        targetedCount > 0 && item.status === "untested" ? "stressed" :
        item.status;
      const rankedItem = {
        ...item,
        status,
        targeted_count: targetedCount,
        broken_chain_count: brokenCount,
        turn_broken: status === "broken" ? item.turn_broken ?? brokenTurns.get(item.id) ?? null : item.turn_broken ?? null,
      };
      const computedScore = assumptionRankScore(rankedItem, targetedCount, brokenCount);
      return {
        ...rankedItem,
        rank_score: item.rank_score === undefined ? computedScore : clamp(toNumber(item.rank_score, computedScore)),
        rank_reason: item.rank_reason || assumptionRankReason(rankedItem, targetedCount, brokenCount),
        validation_move: item.validation_move || validationMove(item.category),
        rank: item.rank || index + 1,
      };
    })
    .sort((a, b) => (b.rank_score || 0) - (a.rank_score || 0) || b.fragility - a.fragility || a.id.localeCompare(b.id))
    .map((item, index) => ({ ...item, rank: index + 1 }));
}

function normalizeMetrics(...sources: unknown[]): Record<string, number> {
  const metrics = { ...DEFAULT_METRICS };
  for (const source of sources) {
    if (!source || typeof source !== "object") continue;
    for (const [key, value] of Object.entries(source as AnyRecord)) {
      if (key in DEFAULT_METRICS) metrics[key] = clamp(toNumber(value, metrics[key]));
    }
  }
  return metrics;
}

function metricDelta(value: unknown) {
  const n = Number(value);
  return Number.isFinite(n) ? Math.round(n) : 0;
}

function isDefaultMetricSet(metrics: Record<string, number>) {
  return Object.entries(DEFAULT_METRICS).every(([key, value]) => metrics[key] === value);
}

function eventDeltas(events: AnyRecord[]) {
  return events
    .map((event) => event.metric_deltas)
    .filter((item): item is AnyRecord => Boolean(item) && typeof item === "object");
}

function damageDeltas(damageReports: DamageReport[]) {
  return [...damageReports]
    .sort((a, b) => a.turn - b.turn)
    .map((report) => report.metricDeltas)
    .filter((item): item is Record<string, number> => Boolean(item) && typeof item === "object");
}

function applyMetricDeltas(base: Record<string, number>, deltas: Array<Record<string, unknown>>) {
  const metrics = { ...base };
  deltas.forEach((deltaSet) => {
    Object.entries(deltaSet).forEach(([key, value]) => {
      if (key in DEFAULT_METRICS) metrics[key] = clamp(metrics[key] + metricDelta(value));
    });
  });
  return metrics;
}

function deriveTruthMetrics(args: {
  sourceMetrics: Record<string, number>;
  events: AnyRecord[];
  damageReports: DamageReport[];
}) {
  const reportDeltas = damageDeltas(args.damageReports);
  const deltaSets = reportDeltas.length ? reportDeltas : eventDeltas(args.events);
  const replayed = deltaSets.length ? applyMetricDeltas(DEFAULT_METRICS, deltaSets) : null;
  const metrics = replayed || { ...args.sourceMetrics };

  if (!replayed && isDefaultMetricSet(metrics) && args.damageReports.length) {
    const latest = [...args.damageReports].sort((a, b) => b.turn - a.turn)[0];
    if (latest) {
      metrics.red_strength = latest.residual;
      if (latest.blueCost !== undefined) metrics.blue_strength = clamp(DEFAULT_METRICS.blue_strength - latest.blueCost);
    }
  }

  if (args.damageReports.length) {
    const latest = [...args.damageReports].sort((a, b) => b.turn - a.turn)[0];
    if (latest?.residual !== undefined) metrics.red_strength = latest.residual;
  }

  return metrics;
}

function parseOpponentAssets(raw: string | null): OpponentAsset[] {
  const parsed = safeParse<unknown>(raw, null);
  if (Array.isArray(parsed)) return parsed.filter((item): item is OpponentAsset => Boolean(item) && typeof item === "object");
  if (parsed && typeof parsed === "object") {
    const payload = parsed as AnyRecord;
    if (Array.isArray(payload.predicted_assets)) {
      return payload.predicted_assets.filter((item: unknown): item is OpponentAsset => Boolean(item) && typeof item === "object");
    }
  }
  return [];
}

function normalizeAssumptions(...sources: unknown[]): AssumptionRow[] {
  return firstArray(...sources).map((item, index) => {
    const rawStatus = cleanText(item.status, "untested").toLowerCase();
    const status: AssumptionStatus =
      rawStatus === "broken" || rawStatus === "stressed" || rawStatus === "validated" ? rawStatus : "untested";
    const confidenceRaw = toNumber(item.confidence, 0);
    const criticalityRaw = toNumber(item.criticality, 0);
    return {
      id: cleanText(item.id, `a${index + 1}`),
      text: cleanText(item.text, cleanText(item.description, "Unnamed planning assumption")),
      category: cleanText(item.category, "operational"),
      confidence: confidenceRaw <= 1 ? Math.round(confidenceRaw * 100) : clamp(confidenceRaw),
      criticality: criticalityRaw <= 1 ? Math.round(criticalityRaw * 100) : clamp(criticalityRaw),
      fragility: clamp(toNumber(item.fragility, item.fragility_score ?? 0)),
      basis: cleanText(item.basis),
      doctrine_ref: cleanText(item.doctrine_ref),
      dependencies: Array.isArray(item.dependencies) ? item.dependencies.map(String) : [],
      cascade_effect: cleanText(item.cascade_effect),
      status,
      turn_broken: item.turn_broken === null || item.turn_broken === undefined ? null : toNumber(item.turn_broken, 0),
      source: "fogline",
      rank: item.rank === undefined ? undefined : toNumber(item.rank, index + 1),
      rank_score: item.rank_score === undefined ? undefined : clamp(toNumber(item.rank_score, 0)),
      rank_reason: cleanText(item.rank_reason),
      targeted_count: item.targeted_count === undefined ? undefined : toNumber(item.targeted_count, 0),
      broken_chain_count: item.broken_chain_count === undefined ? undefined : toNumber(item.broken_chain_count, 0),
      validation_move: cleanText(item.validation_move),
    };
  });
}

function normalizeEvents(...sources: unknown[]): AnyRecord[] {
  return firstArray(...sources).map((item, index) => ({
    ...item,
    turn: toNumber(item.turn, index + 1),
  }));
}

function normalizeHistory(localHistory: unknown, events: AnyRecord[]): HistoryEntry[] {
  const stored = Array.isArray(localHistory) ? localHistory : [];
  const fromStorage = stored
    .filter((item): item is AnyRecord => Boolean(item) && typeof item === "object")
    .map((item, index) => ({
      turn: toNumber(item.turn, index + 1),
      action: cleanText(item.action, cleanText(item.blue_move, cleanText(item.title, "Blue action"))),
      red: cleanText(item.red, cleanText(item.red_move, "Opponent response")),
      ghost: cleanText(item.ghost, cleanText(item.ghost_reasoning, cleanText(item.ghost_state_text))),
    }));

  if (fromStorage.length) return fromStorage;

  return events.map((item, index) => ({
    turn: toNumber(item.turn, index + 1),
    action: cleanText(item.blue_move, cleanText(item.title, "Blue action")),
    red: cleanText(item.red_move, "Opponent response"),
    ghost: cleanText(item.ghost_reasoning, cleanText(item.ghost_state_text)),
  }));
}

function normalizeDamageReports(raw: unknown): DamageReport[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .filter((item): item is AnyRecord => Boolean(item) && typeof item === "object")
    .map((item, index) => ({
      id: cleanText(item.id, `damage-${index + 1}`),
      turn: toNumber(item.turn, index + 1),
      action: cleanText(item.action, "Executed package"),
      target: cleanText(item.target, "Opponent asset"),
      resource: cleanText(item.resource, "Opponent resource"),
      damage: clamp(toNumber(item.damage, 0)),
      residual: clamp(toNumber(item.residual, 100)),
      recovery: cleanText(item.recovery, "unknown"),
      recoveryHours: Math.max(0, toNumber(item.recoveryHours, 0)),
      confidence: clamp(toNumber(item.confidence, 0)),
      severity: cleanText(item.severity, "UNKNOWN"),
      effect: cleanText(item.effect),
      aftershock: cleanText(item.aftershock),
      source: cleanText(item.source),
      redDelta: item.redDelta === undefined ? undefined : metricDelta(item.redDelta),
      blueCost: item.blueCost === undefined ? undefined : clamp(toNumber(item.blueCost, 0)),
      metricDeltas: item.metricDeltas && typeof item.metricDeltas === "object"
        ? Object.fromEntries(
          Object.entries(item.metricDeltas as AnyRecord)
            .filter(([key]) => key in DEFAULT_METRICS)
            .map(([key, value]) => [key, metricDelta(value)])
        )
        : undefined,
      evidence: Array.isArray(item.evidence) ? item.evidence.map(String).filter(Boolean) : [],
    }));
}

function mergeAssumptionSignals(assumptions: AssumptionRow[], missionSignals: AssumptionRow[]) {
  const seen = new Set<string>();
  return [...assumptions, ...missionSignals].filter((item) => {
    const key = `${item.source}-${item.id}-${item.text}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function deriveAssumptionSignals(
  history: HistoryEntry[],
  damageReports: DamageReport[],
  opponentAssets: OpponentAsset[],
): AssumptionRow[] {
  const rows: AssumptionRow[] = history.map((entry, index) => {
    const report = damageReports.find((item) => item.turn === entry.turn) || damageReports[index];
    const damage = report?.damage ?? 0;
    const status: AssumptionStatus = damage >= 60 ? "broken" : damage >= 30 ? "stressed" : "validated";
    const target = report?.resource || entry.red || "the opponent response window";
    return {
      id: `signal-${entry.turn}`,
      text: `${entry.action} depended on changing ${target} before the opponent could recover or re-route.`,
      category: report?.resource || "mission pressure",
      confidence: report?.confidence || (entry.ghost ? 70 : 55),
      criticality: clamp(Math.max(damage, report?.residual ?? 0)),
      fragility: clamp((report?.residual ?? 45) + (report ? Math.min(35, report.recoveryHours / 3) : 0)),
      basis: report
        ? `Live BDA: ${report.damage}% damage, ${report.residual}% residual, recovery ${report.recovery}.`
        : `Recorded turn ${entry.turn}: Blue used ${entry.action}; opponent responded with ${entry.red}.`,
      doctrine_ref: "",
      dependencies: [],
      cascade_effect: report?.aftershock || entry.ghost,
      status,
      turn_broken: status === "broken" ? entry.turn : null,
      source: "mission",
    };
  });

  if (!rows.length && damageReports.length) {
    return damageReports.map((report) => ({
      id: `bda-${report.turn}`,
      text: `${report.action} created a live recovery race around ${report.resource}.`,
      category: report.resource,
      confidence: report.confidence,
      criticality: clamp(report.damage),
      fragility: clamp(report.residual + Math.min(35, report.recoveryHours / 3)),
      basis: `Live BDA against ${report.target}: ${report.damage}% damage and ${report.recovery} recovery.`,
      doctrine_ref: "",
      dependencies: [],
      cascade_effect: report.aftershock,
      status: report.damage >= 60 ? "broken" : report.damage >= 30 ? "stressed" : "validated",
      turn_broken: report.damage >= 60 ? report.turn : null,
      source: "mission",
    }));
  }

  if (!rows.length && opponentAssets.length) {
    return opponentAssets.slice(0, 3).map((asset, index) => ({
      id: `opp-${index + 1}`,
      text: `Likely opponent package includes ${cleanText(asset.name, "an unnamed asset")}; no executed turn has tested this risk yet.`,
      category: cleanText(asset.category, "opponent package"),
      confidence: clamp(toNumber(asset.confidence, 50)),
      criticality: clamp(toNumber(asset.confidence, 50)),
      fragility: clamp(toNumber(asset.confidence, 50)),
      basis: cleanText(asset.capability, cleanText(asset.threat_to_blue)),
      doctrine_ref: "",
      dependencies: [],
      cascade_effect: cleanText(asset.counter),
      status: "untested",
      turn_broken: null,
      source: "mission",
    }));
  }

  return rows;
}

function weakMetrics(metrics: Record<string, number>) {
  return Object.entries(metrics)
    .filter(([key, value]) => key in DEFAULT_METRICS && value < 50)
    .sort((a, b) => a[1] - b[1])
    .map(([key, value]) => `${metricLabel(key)} at ${value}`);
}

function uniqueRows(rows: string[]) {
  return rows.filter((row, index) => row.trim() && rows.indexOf(row) === index);
}

function deriveRootCauses(
  backendRoots: unknown,
  assumptions: AssumptionRow[],
  history: HistoryEntry[],
  damageReports: DamageReport[],
  redUsed: string[],
  metrics: Record<string, number>,
) {
  const fromBackend = Array.isArray(backendRoots) ? backendRoots.map(String).filter(Boolean) : [];
  if (fromBackend.length) return fromBackend;

  const roots: string[] = [];
  assumptions
    .filter((item) => item.status === "broken" || item.status === "stressed")
    .sort((a, b) => (b.rank_score || 0) - (a.rank_score || 0) || b.fragility - a.fragility)
    .forEach((item) => roots.push(`${item.status === "broken" ? "Broke" : "Stressed"}: ${item.text}`));

  damageReports
    .filter((report) => report.damage >= 30)
    .sort((a, b) => b.damage - a.damage)
    .forEach((report) => roots.push(`Turn ${report.turn}: ${report.resource} took ${report.damage}% damage; recovery estimate ${report.recovery}.`));

  redUsed.forEach((name) => roots.push(`Opponent package pressure appeared through ${name}.`));
  weakMetrics(metrics).forEach((item) => roots.push(`End-state pressure: ${item}.`));

  if (!roots.length && history.length) {
    roots.push(`No broken assumption was recorded, but ${history.length} executed turn${history.length === 1 ? "" : "s"} should be reviewed against the opponent responses.`);
  }

  return uniqueRows(roots).slice(0, 5);
}

function deriveLessons(
  backendLessons: unknown,
  backendRecommendation: unknown,
  assumptions: AssumptionRow[],
  damageReports: DamageReport[],
  history: HistoryEntry[],
  metrics: Record<string, number>,
  opponentAssets: OpponentAsset[],
) {
  const lessons = Array.isArray(backendLessons) ? backendLessons.map(String).filter(Boolean) : [];
  if (typeof backendRecommendation === "string" && backendRecommendation.trim()) lessons.push(backendRecommendation.trim());

  assumptions
    .filter((item) => item.text)
    .sort((a, b) => (b.rank_score || 0) - (a.rank_score || 0) || b.fragility - a.fragility)
    .slice(0, 2)
    .forEach((item) => lessons.push(`Validate or branch around: ${item.text}${item.validation_move ? ` (${item.validation_move})` : ""}`));

  damageReports
    .sort((a, b) => b.recoveryHours - a.recoveryHours)
    .slice(0, 2)
    .forEach((report) => lessons.push(`Exploit or reassess ${report.resource} before its ${report.recovery} recovery window closes.`));

  weakMetrics(metrics)
    .slice(0, 2)
    .forEach((item) => lessons.push(`Recover ${item} before committing another high-risk package.`));

  if (opponentAssets.length) {
    lessons.push(`Treat ${opponentAssets.slice(0, 3).map((asset) => cleanText(asset.name, "opponent asset")).join(", ")} as the next red-package planning input.`);
  }

  if (history.length) {
    const latest = history[history.length - 1];
    lessons.push(`Before repeating ${latest.action}, test why the opponent answer was ${latest.red}.`);
  }

  const unique = uniqueRows(lessons);
  return unique.length ? unique.slice(0, 5) : ["Run at least one mission turn to generate live recommendations from the recorded decisions."];
}

function deriveFailureChain(view: AutopsyView) {
  const rows: string[] = [];
  const damagesByTurn = new Map(view.damageReports.map((report) => [report.turn, report]));

  view.history.forEach((entry) => {
    const damage = damagesByTurn.get(entry.turn);
    const parts = [`T${entry.turn}: Blue used ${entry.action}`, `opponent answer was ${entry.red}`];
    if (damage) parts.push(`${damage.resource} registered ${damage.damage}% damage with ${damage.recovery} recovery`);
    const stressed = view.assumptions.find((item) => item.turn_broken === entry.turn || item.basis.includes(`turn ${entry.turn}`));
    if (stressed) parts.push(`${stressed.status} signal: ${short(stressed.text, 86)}`);
    rows.push(parts.join(" -> "));
  });

  if (!rows.length) rows.push(...view.root_causes);
  if (!rows.length) rows.push("No executed-turn chain was found in local storage or the backend autopsy response.");
  return rows.slice(0, 6);
}

function deriveWhatIf(view: AutopsyView) {
  const actual = view.history.length ? view.history.map((entry) => `T${entry.turn}: ${entry.action}`) : ["No executed moves were recorded."];
  const branches: string[] = [];
  const topAssumption = [...view.assumptions].sort((a, b) => (b.rank_score || 0) - (a.rank_score || 0) || b.fragility - a.fragility)[0];
  const latestDamage = view.damageReports[0];
  const weak = weakMetrics(view.final_metrics)[0];

  if (topAssumption) branches.push(`Gate the next move on: ${short(topAssumption.text, 96)}`);
  if (latestDamage) branches.push(`Follow the BDA clock: ${latestDamage.resource} has ${latestDamage.recovery} recovery and ${latestDamage.residual}% residual capability.`);
  if (weak) branches.push(`Stabilize ${weak} before increasing pressure.`);
  if (view.opponentAssets.length) branches.push(`Replay with the likely opponent package visible from turn one: ${view.opponentAssets.slice(0, 2).map((asset) => cleanText(asset.name, "opponent asset")).join(" + ")}.`);
  if (!branches.length) branches.push("Record a fresh mission turn, then compare the next branch against the actual opponent response.");

  const outcome = latestDamage
    ? `Projected improvement: fewer blind follow-up moves because recovery pressure is tied to ${latestDamage.resource}.`
    : weak
      ? `Projected improvement: decision timing changes around ${weak}.`
      : "Projected improvement: the next run gets a verifiable decision gate instead of an empty report.";

  return { actual, branches: branches.slice(0, 4), outcome };
}

function parseSections(reportText: string) {
  const sections: Record<string, string> = {};
  const parts = reportText.split(/^== (.+?) ==$/m).filter(Boolean);
  for (let index = 0; index < parts.length - 1; index += 2) {
    sections[parts[index].trim()] = parts[index + 1].trim();
  }
  return sections;
}

function AssumptionRankPanel({ assumptions }: { assumptions: AssumptionRow[] }) {
  const [selectedId, setSelectedId] = useState<string | null>(assumptions[0]?.id || null);
  const broken = assumptions.filter((item) => item.status === "broken").length;
  const stressed = assumptions.filter((item) => item.status === "stressed").length;
  const sourceLabel = assumptions.some((item) => item.source === "mission") ? "LIVE" : "FOGLINE";

  if (!assumptions.length) {
    return (
      <div style={{ opacity: 0.55, fontSize: 13, lineHeight: 1.7 }}>
        No assumptions or executed-turn signals were recorded for this mission. Start from the landing page, identify a package, execute at least one turn, then finish the run.
      </div>
    );
  }

  const selected = assumptions.find((item) => item.id === selectedId) || assumptions[0];
  const score = clamp(toNumber(selected?.rank_score, selected?.fragility || 0));
  const scoreColor = assumptionScoreTone(score);
  const statusColor = assumptionStatusTone(selected.status);

  return (
    <div className="assumption-rank-shell">
      <div className="assumption-rank-summary">
        {[
          ["TOP RISK", assumptions[0]?.id || "N/A", `${assumptions[0]?.rank_score ?? "--"} score`, assumptionScoreTone(toNumber(assumptions[0]?.rank_score, 0))],
          ["BROKEN", broken, "assumptions", "#ff3c3c"],
          ["STRESSED", stressed, "under pressure", "#ffaa00"],
          ["SOURCE", sourceLabel, "rank model", "#4d9fff"],
        ].map(([label, value, sub, color]) => (
          <div key={String(label)} className="assumption-rank-stat">
            <div style={{ fontSize: 9, opacity: 0.38, letterSpacing: "0.08em", marginBottom: 5 }}>{label}</div>
            <div style={{ fontSize: 22, fontWeight: 900, color: String(color), lineHeight: 1 }}>{value}</div>
            <div style={{ fontSize: 10, opacity: 0.42, marginTop: 5 }}>{sub}</div>
          </div>
        ))}
      </div>

      <div className="assumption-rank-grid">
        <section className="assumption-risk-list">
          <div className="assumption-section-head">
            <span>RISK QUEUE</span>
            <b>{assumptions.length} signals</b>
          </div>
          {assumptions.map((assumption) => {
            const rowScore = clamp(toNumber(assumption.rank_score, assumption.fragility));
            const rowColor = assumptionScoreTone(rowScore);
            const rowStatusColor = assumptionStatusTone(assumption.status);
            const isSelected = selected.id === assumption.id;
            const meta = [
              assumption.status.toUpperCase(),
              assumption.dependencies.length ? `${assumption.dependencies.length} links` : "",
              assumption.targeted_count ? `target x${assumption.targeted_count}` : "",
            ].filter(Boolean).join(" / ");

            return (
              <button
                key={`${assumption.source}-${assumption.id}-${assumption.rank}`}
                className={`assumption-risk-row ${isSelected ? "selected" : ""}`}
                onClick={() => setSelectedId(assumption.id)}
                style={{
                  borderColor: isSelected ? `${rowColor}80` : "rgba(255,255,255,0.08)",
                  background: isSelected ? `${rowColor}12` : undefined,
                }}
                type="button"
              >
                <span className="assumption-row-rank" style={{ color: rowColor }}>
                  {assumption.rank}
                  <small>{assumption.id}</small>
                </span>
                <span className="assumption-row-main">
                  <span className="assumption-row-title">{assumption.text}</span>
                  <span className="assumption-row-meta">
                    <i style={{ background: `${rowStatusColor}18`, borderColor: `${rowStatusColor}35`, color: rowStatusColor }}>{meta}</i>
                    <em>{assumption.category.replace(/_/g, " ")}</em>
                  </span>
                  <span className="assumption-row-meter">
                    <span style={{ width: `${rowScore}%`, background: rowColor }} />
                  </span>
                </span>
                <span className="assumption-row-score" style={{ color: rowColor }}>{rowScore}</span>
              </button>
            );
          })}
        </section>

        <aside className="assumption-detail">
          <div className="assumption-detail-top">
            <div>
              <div className="assumption-section-head" style={{ marginBottom: 8 }}>
                <span>SELECTED ASSUMPTION</span>
                <b>{selected.id}</b>
              </div>
              <h3>{selected.text}</h3>
            </div>
            <div className="assumption-collapse-score" style={{ color: scoreColor }}>
              <span>Collapse</span>
              <b>{score}</b>
            </div>
          </div>

          <div className="assumption-pill-row">
            <span style={{ background: `${statusColor}18`, borderColor: `${statusColor}35`, color: statusColor }}>
              {selected.status.toUpperCase()}{selected.turn_broken ? ` T${selected.turn_broken}` : ""}
            </span>
            <span>{selected.category.replace(/_/g, " ").toUpperCase()}</span>
            {selected.targeted_count ? <span style={{ color: "#ffaaa3", borderColor: "rgba(255,120,110,.22)", background: "rgba(255,60,60,.05)" }}>TARGET x{selected.targeted_count}</span> : null}
          </div>

          <div className="assumption-score-grid">
            {[
              ["Fragility", selected.fragility, assumptionScoreTone(selected.fragility)],
              ["Criticality", selected.criticality, assumptionScoreTone(selected.criticality)],
              ["Confidence", selected.confidence, "#4d9fff"],
            ].map(([label, value, color]) => (
              <div key={String(label)} className="assumption-score-card">
                <div><span>{label}</span><b style={{ color: String(color) }}>{value}</b></div>
                <i><em style={{ width: `${clamp(Number(value))}%`, background: String(color) }} /></i>
              </div>
            ))}
          </div>

          <div className="assumption-detail-block">
            <span>WHY IT RANKED HERE</span>
            <p>{selected.rank_reason || assumptionRankReason(selected, selected.targeted_count || 0, selected.broken_chain_count || 0)}</p>
          </div>
          <div className="assumption-detail-block green">
            <span>NEXT VALIDATION MOVE</span>
            <p>{selected.validation_move || validationMove(selected.category)}</p>
          </div>
          {selected.cascade_effect && (
            <div className="assumption-detail-block red">
              <span>CASCADE IF WRONG</span>
              <p>{selected.cascade_effect}</p>
            </div>
          )}
          {selected.dependencies.length > 0 && (
            <div className="assumption-dependency-row">
              <span>LINKED ASSUMPTIONS</span>
              <div>{selected.dependencies.map((dep) => <b key={dep}>{dep}</b>)}</div>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

function buildView(args: {
  scenario: string;
  localGame: AnyRecord;
  localHistory: unknown;
  localMetrics: unknown;
  localRedUsed: unknown;
  localDamageReports: unknown;
  localOpponentAssets: OpponentAsset[];
  backendReport: AnyRecord;
  backendGame: AnyRecord;
  warning: string;
}): AutopsyView {
  const assumptions = normalizeAssumptions(
    args.backendReport.assumptions,
    args.backendGame.assumptions,
    args.localGame.assumptions,
  );
  const events = normalizeEvents(args.backendReport.events, args.backendGame.events, args.localGame.events);
  const history = normalizeHistory(args.localHistory, events);
  const damageReports = normalizeDamageReports(args.localDamageReports);
  const missionSignals = deriveAssumptionSignals(history, damageReports, args.localOpponentAssets);
  const displayAssumptions = rankAssumptionRows(mergeAssumptionSignals(assumptions, missionSignals), events);
  const sourceMetrics = normalizeMetrics(
    args.localGame.metrics,
    args.localMetrics,
    args.backendGame.metrics,
    args.backendReport.final_metrics,
  );
  const metrics = deriveTruthMetrics({
    sourceMetrics,
    events,
    damageReports,
  });
  const redUsed = Array.isArray(args.localRedUsed) ? args.localRedUsed.map(String).filter(Boolean) : [];
  const turns = Math.max(
    toNumber(args.backendReport.turns, 0),
    toNumber(args.backendGame.turn, 0),
    toNumber(args.localGame.turn, 0),
    history.length,
    damageReports.length,
  );
  const broken = displayAssumptions.filter((item) => item.status === "broken").length;
  const stressed = displayAssumptions.filter((item) => item.status === "stressed").length;
  const root_causes = deriveRootCauses(args.backendReport.root_causes, displayAssumptions, history, damageReports, redUsed, metrics);
  const lessons = deriveLessons(
    args.backendReport.lessons,
    args.backendReport.recommendation,
    displayAssumptions,
    damageReports,
    history,
    metrics,
    args.localOpponentAssets,
  );

  return {
    scenario: args.scenario,
    status: cleanText(args.backendReport.status, cleanText(args.backendGame.status, cleanText(args.localGame.status, history.length ? "completed" : "incomplete"))),
    turns,
    final_metrics: metrics,
    assumptions: displayAssumptions,
    usingMissionSignals: missionSignals.length > 0,
    history,
    damageReports,
    opponentAssets: args.localOpponentAssets,
    redUsed,
    root_causes,
    assumptions_broken: broken,
    assumptions_stressed: stressed,
    recommendation: lessons[0],
    lessons,
    report: cleanText(args.backendReport.report),
    warning: args.warning,
  };
}

export default function AutopsyPage() {
  const router = useRouter();
  const [report, setReport] = useState<AutopsyView | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState(0);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let mounted = true;

    async function load() {
      const scenario = localStorage.getItem("warbreak_scenario") || "Taiwan Strait 2027";
      const localGame = safeParse<AnyRecord>(localStorage.getItem("warbreak_game"), {});
      const localHistory = safeParse<unknown[]>(localStorage.getItem("warbreak_history"), []);
      const localMetrics = safeParse<AnyRecord>(localStorage.getItem("warbreak_metrics"), {});
      const localRedUsed = safeParse<string[]>(localStorage.getItem("warbreak_red_used"), []);
      const localDamageReports = safeParse<DamageReport[]>(localStorage.getItem("warbreak_damage_reports"), []);
      const localOpponentAssets = parseOpponentAssets(localStorage.getItem("warbreak_opponent_assets"));
      const gameId = localStorage.getItem("warbreak_game_id") || "";

      let backendReport: AnyRecord = {};
      let backendGame: AnyRecord = {};
      let warning = "";

      if (gameId && gameId !== "local-demo") {
        try {
          backendReport = normalizeReport(await getAutopsy(gameId));
        } catch (error) {
          warning = error instanceof Error ? error.message : "Backend autopsy unavailable.";
          try {
            backendGame = normalizeReport(await getGame(gameId));
          } catch {
            backendGame = {};
          }
        }
      }

      const nextReport = buildView({
        scenario,
        localGame,
        localHistory,
        localMetrics,
        localRedUsed,
        localDamageReports,
        localOpponentAssets,
        backendReport,
        backendGame,
        warning,
      });

      if (mounted) {
        setReport(nextReport);
        setLoading(false);
      }
    }

    load();
    return () => {
      mounted = false;
    };
  }, []);

  const parsed = useMemo(() => parseSections(report?.report || ""), [report?.report]);
  const whatIf = useMemo(() => (report ? deriveWhatIf(report) : { actual: [], branches: [], outcome: "" }), [report]);
  const failureChain = useMemo(() => (report ? deriveFailureChain(report) : []), [report]);

  const copy = () => {
    if (!report) return;
    const lines = [
      `WARBREAK FAILURE AUTOPSY - ${report.scenario}`,
      `Status: ${report.status} | Turns: ${report.turns}`,
      `Broken signals: ${report.assumptions_broken} | Stressed signals: ${report.assumptions_stressed}`,
      "",
      "DECISION LOG:",
      ...(report.history.length ? report.history.map((h) => `T${h.turn}: Blue -> ${h.action} | Opponent -> ${h.red}`) : ["No executed moves recorded."]),
      "",
      "FAILURE CHAIN:",
      ...failureChain.map((row) => `- ${row}`),
      "",
      "RECOMMENDATIONS:",
      ...report.lessons.map((row) => `- ${row}`),
      "",
      report.report,
    ].join("\n");
    navigator.clipboard?.writeText(lines).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  if (loading) {
    return (
      <main style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 20 }}>
        <div style={{ width: 80, height: 80 }}><div className="radar-disc" style={{ width: "100%", height: "100%", opacity: 0.5 }} /></div>
        <div className="kicker">GENERATING AUTOPSY</div>
        {["Loading mission data", "Rebuilding failure chain", "Scoring recommendations"].map((message, index) => (
          <div key={index} style={{ fontSize: 11, opacity: 0.35, marginTop: -8 }}>{message}</div>
        ))}
      </main>
    );
  }

  if (!report) return null;

  const failed = report.status === "failed";
  const tabContent = [
    <div key="assumptions">
      {report.usingMissionSignals && (
        <div style={{ padding: "10px 12px", border: "1px solid rgba(255,170,0,0.18)", background: "rgba(255,170,0,0.05)", borderRadius: 8, marginBottom: 12, fontSize: 12, color: "rgba(255,225,170,0.78)", lineHeight: 1.55 }}>
          Live mission signals from executed turns, BDA, and opponent-package data are included in these counts.
        </div>
      )}
      <AssumptionRankPanel assumptions={report.assumptions} />
    </div>,

    <div key="log">
      {report.history.length === 0 ? (
        <div style={{ opacity: 0.55, fontSize: 13, lineHeight: 1.7 }}>No decision log was recorded in local storage or the backend game state.</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {report.history.map((entry) => (
            <div key={entry.turn} style={{ padding: "12px 14px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 9 }}>
              <div style={{ display: "flex", gap: 12 }}>
                <div style={{ width: 30, height: 30, borderRadius: "50%", background: "rgba(77,159,255,0.12)", border: "1px solid rgba(77,159,255,0.25)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  <span style={{ fontSize: 10, color: "#4d9fff", fontWeight: 800 }}>T{entry.turn}</span>
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 4 }}>Blue: {entry.action}</div>
                  <div style={{ fontSize: 12, opacity: 0.58 }}>Opponent: {entry.red}</div>
                  {entry.ghost && <div style={{ fontSize: 11, color: "rgba(255,200,200,0.72)", marginTop: 7, borderLeft: "2px solid rgba(255,60,60,0.25)", paddingLeft: 8, lineHeight: 1.6 }}>{short(entry.ghost, 190)}</div>}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>,

    <div key="ghost">
      <div style={{ padding: "12px 14px", background: "rgba(255,60,60,0.05)", border: "1px solid rgba(255,60,60,0.15)", borderRadius: 9, marginBottom: 14 }}>
        <div style={{ fontSize: 11, color: "#ff8888", marginBottom: 8, letterSpacing: "0.08em" }}>ADVERSARY PRESSURE MODEL</div>
        <div style={{ fontSize: 13, opacity: 0.78, lineHeight: 1.7 }}>
          {report.opponentAssets.length
            ? `This run's red model is anchored to the likely opponent package: ${report.opponentAssets.slice(0, 3).map((asset) => cleanText(asset.name, "opponent asset")).join(", ")}.`
            : "No likely opponent package was stored for this run, so the autopsy can only use recorded turn responses."}
        </div>
      </div>
      {report.history.some((entry) => entry.ghost) ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {report.history.filter((entry) => entry.ghost).map((entry) => (
            <div key={entry.turn} style={{ padding: "12px 14px", background: "rgba(255,60,60,0.04)", border: "1px solid rgba(255,60,60,0.12)", borderRadius: 9 }}>
              <div style={{ fontSize: 10, color: "#ff8888", marginBottom: 6 }}>TURN {entry.turn} RESPONSE</div>
              <div style={{ fontSize: 13, color: "rgba(255,200,200,0.85)", lineHeight: 1.7 }}>{entry.ghost}</div>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ opacity: 0.58, fontSize: 13, lineHeight: 1.7 }}>
          No Ghost Council response was saved. This usually means the mission ended from local fallback data before the backend returned a turn response.
        </div>
      )}
    </div>,

    <div key="chain">
      {report.root_causes.length > 0 && (
        <div style={{ padding: "14px 16px", background: "rgba(255,60,60,0.06)", border: "1px solid rgba(255,60,60,0.2)", borderRadius: 9, marginBottom: 16 }}>
          <div style={{ fontSize: 10, color: "#ff3c3c", letterSpacing: "0.1em", marginBottom: 8 }}>PRIMARY ROOT CAUSE</div>
          <div style={{ fontSize: 14, lineHeight: 1.7 }}>{report.root_causes[0]}</div>
        </div>
      )}
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {(parsed["FAILURE CHAIN"] ? [parsed["FAILURE CHAIN"]] : failureChain).map((row, index) => (
          <div key={index} style={{ display: "flex", gap: 12, alignItems: "flex-start", padding: "10px 12px", background: "rgba(255,60,60,0.04)", border: "1px solid rgba(255,60,60,0.12)", borderRadius: 8 }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#ff3c3c", marginTop: 6, flexShrink: 0 }} />
            <div style={{ fontSize: 13, opacity: 0.82, lineHeight: 1.65, whiteSpace: parsed["FAILURE CHAIN"] ? "pre-wrap" : "normal" }}>{row}</div>
          </div>
        ))}
      </div>
    </div>,

    <div key="whatif">
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <div style={{ background: failed ? "rgba(255,60,60,0.05)" : "rgba(0,232,122,0.05)", border: `1px solid ${failed ? "rgba(255,60,60,0.2)" : "rgba(0,232,122,0.2)"}`, borderRadius: 12, overflow: "hidden" }}>
          <div style={{ padding: "11px 14px", background: failed ? "rgba(255,60,60,0.1)" : "rgba(0,232,122,0.1)", borderBottom: `1px solid ${failed ? "rgba(255,60,60,0.15)" : "rgba(0,232,122,0.15)"}`, display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 7, height: 7, borderRadius: "50%", background: failed ? "#ff3c3c" : "#00e87a" }} />
            <div style={{ fontSize: 11, fontWeight: 800, color: failed ? "#ff3c3c" : "#00e87a", letterSpacing: "0.08em" }}>TIMELINE A - RECORDED PATH</div>
          </div>
          <div style={{ padding: 14, display: "flex", flexDirection: "column", gap: 8 }}>
            {whatIf.actual.map((row, index) => (
              <div key={index} style={{ fontSize: 12, opacity: 0.75, lineHeight: 1.55 }}>{row}</div>
            ))}
          </div>
        </div>
        <div style={{ background: "rgba(77,159,255,0.05)", border: "1px solid rgba(77,159,255,0.2)", borderRadius: 12, overflow: "hidden" }}>
          <div style={{ padding: "11px 14px", background: "rgba(77,159,255,0.1)", borderBottom: "1px solid rgba(77,159,255,0.15)", display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 7, height: 7, borderRadius: "50%", background: "#4d9fff" }} />
            <div style={{ fontSize: 11, fontWeight: 800, color: "#4d9fff", letterSpacing: "0.08em" }}>TIMELINE B - LIVE BRANCH</div>
          </div>
          <div style={{ padding: 14 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 12 }}>
              {whatIf.branches.map((row, index) => (
                <div key={index} style={{ display: "flex", gap: 8 }}>
                  <div style={{ fontSize: 10, color: "#4d9fff", flexShrink: 0, fontWeight: 800, paddingTop: 1 }}>{index + 1}</div>
                  <div style={{ fontSize: 12, opacity: 0.75, lineHeight: 1.55 }}>{row}</div>
                </div>
              ))}
            </div>
            <div style={{ padding: "8px 10px", background: "rgba(0,232,122,0.06)", border: "1px solid rgba(0,232,122,0.2)", borderRadius: 7 }}>
              <div style={{ fontSize: 10, color: "#00e87a", marginBottom: 3 }}>PROJECTED OUTCOME</div>
              <div style={{ fontSize: 11, opacity: 0.68, lineHeight: 1.55 }}>{whatIf.outcome}</div>
            </div>
          </div>
        </div>
      </div>
    </div>,

    <div key="recs">
      <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 14 }}>
        {(parsed["RESILIENT PLAN"] ? [parsed["RESILIENT PLAN"]] : report.lessons).map((lesson, index) => (
          <div key={index} style={{ display: "flex", gap: 12, padding: "12px 14px", background: "rgba(0,232,122,0.04)", border: "1px solid rgba(0,232,122,0.12)", borderRadius: 9 }}>
            <div style={{ width: 22, height: 22, borderRadius: "50%", background: "rgba(0,232,122,0.12)", border: "1px solid rgba(0,232,122,0.2)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
              <span style={{ fontSize: 10, color: "#00e87a", fontWeight: 800 }}>{index + 1}</span>
            </div>
            <div style={{ fontSize: 13, opacity: 0.78, lineHeight: 1.65, whiteSpace: parsed["RESILIENT PLAN"] ? "pre-wrap" : "normal" }}>{lesson}</div>
          </div>
        ))}
      </div>
      {report.recommendation && (
        <div style={{ padding: "14px 16px", background: "rgba(77,159,255,0.05)", border: "1px solid rgba(77,159,255,0.2)", borderRadius: 9 }}>
          <div style={{ fontSize: 10, color: "#4d9fff", letterSpacing: "0.1em", marginBottom: 7 }}>KEY TAKEAWAY</div>
          <div style={{ fontSize: 14, lineHeight: 1.75, color: "rgba(180,210,255,0.85)" }}>{report.recommendation}</div>
        </div>
      )}
    </div>,
  ];

  return (
    <main style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <div className="topbar" style={{ position: "sticky", top: 0, zIndex: 100, backdropFilter: "blur(12px)" }}>
        <div className="brand">
          <button className="btn ghost" onClick={() => router.push("/")}>← NEW MISSION</button>
          WARBREAK
          <span className="badge">{report.scenario}</span>
        </div>
        <button className="btn ghost" onClick={copy} style={{ fontSize: 11, opacity: copied ? 1 : 0.65 }}>
          {copied ? "✓ COPIED" : "COPY REPORT"}
        </button>
      </div>

      <div style={{ flex: 1, padding: "28px 36px", maxWidth: 1060, margin: "0 auto", width: "100%", boxSizing: "border-box" }}>
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div className="kicker" style={{ marginBottom: 10, fontSize: 10 }}>FAILURE AUTOPSY - {report.scenario.toUpperCase()}</div>
          <h1 style={{ fontSize: "clamp(36px,5.5vw,64px)", margin: "0 0 8px", color: failed ? "#ff3c3c" : "#00e87a", textShadow: `0 0 40px ${failed ? "rgba(255,60,60,0.3)" : "rgba(0,232,122,0.3)"}` }}>
            {failed ? "▼ PLAN COLLAPSED" : "▲ MISSION COMPLETE"}
          </h1>
          <div style={{ fontSize: 13, opacity: 0.48 }}>
            {report.turns} turn{report.turns === 1 ? "" : "s"} · {report.assumptions_broken} broken signal{report.assumptions_broken === 1 ? "" : "s"} · {report.assumptions_stressed} stressed
          </div>
          {report.warning && <div style={{ marginTop: 10, fontSize: 11, color: "#ffaa00", opacity: 0.72 }}>Backend autopsy unavailable; rebuilt from saved mission data: {report.warning}</div>}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(6,1fr)", gap: 8, marginBottom: 28 }}>
          {METRICS.map(({ key, label }) => {
            const value = report.final_metrics[key] ?? 50;
            const baseline = DEFAULT_METRICS[key] ?? 50;
            const delta = value - baseline;
            const c = metricTone(key, value);
            const deltaColor = metricDeltaTone(key, delta);
            return (
              <div key={key} style={{ padding: "11px 10px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 9, textAlign: "center" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6, marginBottom: 5, minHeight: 12 }}>
                  <span style={{ fontSize: 9, opacity: 0.45, letterSpacing: "0.06em" }}>{label.toUpperCase()}</span>
                  <span style={{ fontSize: 8, fontWeight: 900, color: deltaColor, opacity: delta === 0 ? 0.38 : 0.9 }}>
                    {delta === 0 ? "0" : delta > 0 ? `+${delta}` : delta}
                  </span>
                </div>
                <div style={{ fontSize: 28, fontWeight: 900, color: c, lineHeight: 1, marginBottom: 6 }}>{value}</div>
                <div style={{ height: 2, background: "rgba(255,255,255,0.07)", borderRadius: 1, overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${clamp(value)}%`, background: c, borderRadius: 1 }} />
                </div>
                <div style={{ marginTop: 5, fontSize: 8, opacity: 0.28 }}>BASE {baseline}</div>
              </div>
            );
          })}
        </div>

        {report.root_causes.length > 0 && (
          <div style={{ padding: "13px 16px", background: "rgba(255,60,60,0.06)", border: "1px solid rgba(255,60,60,0.2)", borderRadius: 9, marginBottom: 22, display: "flex", gap: 12, alignItems: "flex-start" }}>
            <div style={{ fontSize: 18, flexShrink: 0, marginTop: 1 }}>!</div>
            <div>
              <div style={{ fontSize: 10, color: "#ff3c3c", letterSpacing: "0.1em", marginBottom: 5 }}>ROOT CAUSE</div>
              <div style={{ fontSize: 14, lineHeight: 1.6 }}>{report.root_causes[0]}</div>
            </div>
          </div>
        )}

        <div style={{ display: "flex", gap: 3, marginBottom: 16, overflowX: "auto", paddingBottom: 2 }}>
          {TABS.map((label, index) => (
            <button
              key={label}
              onClick={() => setTab(index)}
              style={{
                padding: "7px 13px",
                borderRadius: 6,
                fontSize: 10,
                fontWeight: 800,
                whiteSpace: "nowrap",
                cursor: "pointer",
                transition: "all 0.15s",
                background: tab === index ? "rgba(77,159,255,0.15)" : "rgba(255,255,255,0.04)",
                border: `1px solid ${tab === index ? "rgba(77,159,255,0.4)" : "rgba(255,255,255,0.08)"}`,
                color: tab === index ? "#4d9fff" : "rgba(255,255,255,0.44)",
                letterSpacing: "0.06em",
              }}
            >
              {label}
            </button>
          ))}
        </div>

        <div style={{ padding: "18px 20px", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 10, marginBottom: 24, minHeight: 200 }}>
          {tabContent[tab]}
        </div>

        <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
          <button className="btn primary" onClick={() => router.push("/")} style={{ fontSize: 13, padding: "11px 28px" }}>
            RUN NEW MISSION →
          </button>
          <button className="btn ghost" onClick={copy} style={{ fontSize: 13, padding: "11px 28px" }}>
            {copied ? "✓ COPIED" : "COPY REPORT"}
          </button>
        </div>
      </div>
    </main>
  );
}
