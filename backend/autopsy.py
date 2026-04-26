from game_state import GameState
try:
    from llm_client import call_llm
except Exception:
    call_llm = None

PROMPT = """You are writing a WARBREAK mission debrief for a non-technical commander.
Use plain English. Avoid jargon. No long doctrine paragraphs. No coded headings like A1/A2 except when necessary.

Write exactly 5 short sections:
1. Bottom line — one sentence.
2. What broke — 3 bullets, simple wording.
3. Why it mattered — 3 bullets, simple cause and effect.
4. Real-world echo — name a comparable historical pattern, but do not overclaim it is identical.
5. Better next plan — 3 concrete changes.

Original plan: {plan}
History: {history}
Assumptions: {assumptions}
Final status: Blue strength {blue}, international opinion {intl}, US support {us}, allied confidence {allied}
"""

def generate_autopsy(state: GameState) -> str:
    history = getattr(state, 'move_history', [])
    assumptions = []
    for a in getattr(state, 'assumptions', []):
        assumptions.append({
            'text': getattr(a,'text',''),
            'status': getattr(a,'status', 'broken' if getattr(a,'broken',False) else 'untested'),
            'turn_broken': getattr(a,'turn_broken',None),
            'fragility': getattr(a,'fragility',None)
        })
    if call_llm:
        try:
            return call_llm(PROMPT.format(plan=getattr(state,'plan_text',''), history=history, assumptions=assumptions, blue=round(getattr(state,'blue_strength',0),1), intl=round(getattr(state,'intl_opinion',0),1), us=round(getattr(state,'us_domestic',0),1), allied=round(getattr(state,'allied_confidence',0),1)), max_tokens=900, temperature=0.25)
        except Exception:
            pass
    return """Bottom line — The mission failed because a hidden assumption broke before the team had a backup plan.

What broke
- The plan depended on one route, partner, or time window staying available.
- The opponent pressured that weak point instead of fighting where Blue felt strongest.
- Once it broke, other parts of the plan slowed down.

Why it mattered
- Blue lost time.
- Public or allied confidence dropped.
- Recovery options became more expensive than prevention.

Real-world echo
- Many historical operations show this same pattern: access, logistics, timing, or public support fails earlier than expected.

Better next plan
- Identify the top two assumptions before the first move.
- Build a backup route and backup communication plan.
- Delay risky escalation until the fragile assumption is protected."""
