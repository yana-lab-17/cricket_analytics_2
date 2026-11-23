"""
ai_coach.py
-----------
Unified AI Agent for the Cricket Fielding Analytics Engine.

Architecture:
  - Intent classifier  → decides: tactical vs neuroscience vs general
  - Tactical branch    → uses the cricket knowledge base + function tools
                         to set fields, move fielders, explain positions
  - Neuro branch       → routes to NeuroAgent (NeuroSport LLM or fallback KB)
  - Gemini optional    → used only if GEMINI_API_KEY is set; otherwise the
                         rule-based tactical engine handles everything

Field placement works WITHOUT Gemini — every bowling scenario maps to
a specific field via TACTICAL_FIELD_PLANS, which also supports fine-tuned
individual fielder positions beyond the 6 presets.
"""

import re
import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Tuple

from backend.cricket_knowledge import (
    FIELDING_POSITIONS, BOWLING_TYPES, BOWLING_TIPS,
    PHASE_FIELD_MAP, MATCH_PHASES, DELIVERY_MATRIX,
)
# Compatibility shims so rest of ai_coach.py keeps working
BOWLING_STRATEGY_MATRIX = {k: {"description": v["description"], "label": v["label"]}
                            for k, v in BOWLING_TYPES.items()}
POWERPLAY_RULES = MATCH_PHASES
COACHING_TIPS   = BOWLING_TIPS
from backend.neuro_agent import NeuroAgent, is_neuro_question

logger = logging.getLogger("AICoach")

# ── Optional Gemini ───────────────────────────────────────────────────────────
try:
    from google import genai
    from google.genai import types
    _gemini_client = genai.Client()
    HAS_GEMINI = True
    logger.info("Gemini available")
except Exception:
    HAS_GEMINI = False
    logger.info("Gemini not available — using rule-based tactical engine")


# ─────────────────────────────────────────────────────────────────────────────
# TACTICAL FIELD PLANS
# Fine-grained field recipes for specific bowling scenarios.
# Each entry maps a natural-language intent to:
#   - preset  : name of the closest base preset to apply first
#   - moves   : list of (fielder_name, x, z) individual tweaks on top
#   - explanation: what to say to the user
# ─────────────────────────────────────────────────────────────────────────────
TACTICAL_FIELD_PLANS: Dict[str, Dict] = {

    # ── Short-pitched / bouncer plan ─────────────────────────────────────────
    "short_pitched": {
        "preset": "Pace - Attacking",
        "moves": [
            ("FineLeg",        -32.0, -42.0),   # fine leg boundary for hook
            ("DeepSquareLeg",  -54.0,  -8.0),   # deep square leg for pull
            ("Gully",           14.0,  -8.0),   # gully for top edge
            ("Point",           24.0,   2.0),   # point for thick edge
            ("MidOn",          -10.0,  24.0),   # midOn for straight bat
            ("MidOff",          10.0,  24.0),   # midOff
            ("DeepMidWicket",  -50.0,  26.0),   # cow corner for miscued pull
        ],
        "explanation": (
            "For short-pitched bowling I've set a bouncer trap: "
            "Fine Leg and Deep Square Leg guard the hook/pull boundaries, "
            "Gully catches the top edge, and Deep Mid-Wicket covers the cow corner. "
            "The idea is to force the batter to play the short ball and mis-hit into "
            "one of these catchers. Make sure your bouncer hits throat height — "
            "anything lower just becomes a free pull shot."
        ),
        "keywords": [
            "short", "bouncer", "short pitch", "short length", "pull", "hook",
            "short ball", "bumper", "throat", "body line",
        ],
    },

    # ── Full / yorker plan ────────────────────────────────────────────────────
    "full_yorker": {
        "preset": "Death Overs",
        "moves": [
            ("WicketKeeper",    0.0, -12.0),
            ("ShortThird",     16.0, -12.0),
            ("Point",          24.0,   4.0),
            ("ExtraCover",     20.0,  16.0),
            ("MidWicket",     -20.0,  12.0),
            ("Bowler",          0.0,  19.0),
            ("FineLeg",       -30.0, -40.0),   # fine leg for glance off yorker
            ("DeepCover",      50.0,  26.0),   # straight hit protection
            ("LongOff",        16.0,  58.0),
            ("LongOn",        -16.0,  58.0),
            ("DeepSquareLeg", -52.0,  -8.0),
        ],
        "explanation": (
            "Full/yorker length — the aim is to cramp the batter and force "
            "the ball into fielders at the death. Fine Leg and Deep Square Leg "
            "protect the leg-side glance, Long-Off and Long-On seal the straight "
            "boundaries, and Deep Cover stops the lofted drive. Keep the yorker "
            "targeting the toe of the bat — a full toss goes to Long-On."
        ),
        "keywords": [
            "full", "yorker", "toe", "full length", "bowl full", "blockhole",
            "full toss", "low full",
        ],
    },

    # ── Outswing plan ─────────────────────────────────────────────────────────
    "outswing": {
        "preset": "Pace - Attacking",
        "moves": [
            ("WicketKeeper",  0.0, -21.0),
            ("Slip_1",        3.2, -22.0),
            ("Slip_2",        6.2, -21.2),
            ("Slip_3",        9.2, -20.0),
            ("Gully",        14.0, -10.5),
            ("Point",        24.0,   1.0),
            ("Cover",        22.0,  11.0),
            ("MidOff",       11.0,  24.0),
            ("MidOn",       -11.0,  24.0),
            ("Bowler",        0.0,  18.0),
            ("FineLeg",     -28.0, -44.0),
        ],
        "explanation": (
            "Classic outswing cordon: three slips, gully, and cover to catch "
            "the outside edge or mistimed drive. The ball is moving away from "
            "the bat, so everything behind the wicket on the off side needs "
            "to be covered. Keep Fine Leg for the rare leg-side delivery. "
            "Bowl just outside off stump, let the ball do the work."
        ),
        "keywords": [
            "outswing", "swing out", "away swing", "move away", "outside edge",
            "new ball outswing", "out-swing",
        ],
    },

    # ── Inswing plan ─────────────────────────────────────────────────────────
    "inswing": {
        "preset": "Powerplay",
        "moves": [
            ("WicketKeeper",   0.0, -15.0),
            ("Slip_1",         3.0, -15.5),
            ("Gully",         13.0,  -8.0),
            ("Point",         23.0,   2.0),
            ("Cover",         25.0,   8.0),
            ("MidOff",        12.0,  22.0),
            ("MidOn",        -12.0,  22.0),
            ("MidWicket",    -22.0,  10.0),
            ("Bowler",         0.0,  18.0),
            ("FineLeg",      -30.0, -40.0),   # catches leg-side glance
            ("ShortLeg",      -7.0,   3.0),   # bat-pad for inswingers
        ],
        "explanation": (
            "Inswing field: Short Leg and Fine Leg protect the leg side trap. "
            "The ball is swinging into the right-hander, so LBW and pad-bat catches "
            "are your primary wicket-taking modes. One slip stays for the false drive "
            "off the outside. Bowl full and straight — half volley on off stump is perfect."
        ),
        "keywords": [
            "inswing", "swing in", "into the batter", "into the body",
            "in-swing", "lbw", "pad",
        ],
    },

    # ── Off spin plan ─────────────────────────────────────────────────────────
    "off_spin": {
        "preset": "Spin - Off Spin Ring",
        "moves": [
            ("WicketKeeper",       0.0,  -4.0),
            ("Slip_1",             2.5,  -6.0),
            ("ShortLeg",          -5.5,   3.5),
            ("CatchingMidWicket", -14.0,  11.0),
            ("SquareLeg",        -22.0,   0.0),
            ("Bowler",             0.0,  16.0),
            ("Point",             23.0,   2.0),
            ("Cover",             21.0,  10.0),
            ("LongOn",           -18.0,  58.0),
            ("DeepMidWicket",    -52.0,  22.0),
            ("DeepBackwardSquare",-48.0, -26.0),
        ],
        "explanation": (
            "Off-spin ring: Short Leg and Catching Mid-Wicket are your main "
            "wicket-takers — the spin turns into the batter and they flick it "
            "straight to these catchers. Slip catches the thick outside edge. "
            "Long-On and Deep Mid-Wicket protect the slog-sweep boundary. "
            "Toss it up and invite the drive — you want the edge or the miscued sweep."
        ),
        "keywords": [
            "off spin", "off-spin", "offspin", "turn into", "turn from off",
            "doosra", "off break",
        ],
    },

    # ── Leg spin plan ─────────────────────────────────────────────────────────
    "leg_spin": {
        "preset": "Spin - Leg Spin Trap",
        "moves": [
            ("WicketKeeper",   0.0,  -4.5),
            ("Slip_1",         2.8,  -6.5),
            ("BackwardPoint",  18.0,  -4.0),
            ("Cover",         22.0,  10.0),
            ("MidWicket",    -18.0,  12.0),
            ("Bowler",         0.0,  16.0),
            ("DeepPoint",     54.0,  -2.0),
            ("DeepCover",     50.0,  28.0),
            ("LongOff",       18.0,  58.0),
            ("LongOn",       -18.0,  58.0),
            ("DeepMidWicket", -50.0,  22.0),
        ],
        "explanation": (
            "Leg-spin trap: the ball turns away from the right-hander, so slips "
            "and deep off-side cover catch the edge or mistimed drive. "
            "Deep Point, Deep Cover, and Long-Off guard the boundary for the "
            "batter who tries to hit over the top. Bowl the googly into the pads "
            "for an LBW — Mid-Wicket stays inside for that inside edge."
        ),
        "keywords": [
            "leg spin", "leg-spin", "legspin", "wrist spin", "googly",
            "turn away", "turn from leg", "flipper",
        ],
    },

    # ── Slow left arm ─────────────────────────────────────────────────────────
    "slow_left_arm": {
        "preset": "Spin - Off Spin Ring",
        "moves": [
            ("WicketKeeper",   0.0,  -4.2),
            ("Slip_1",         2.5,  -6.2),
            ("ShortLeg",      -5.5,   3.5),
            ("Cover",         21.0,  10.0),
            ("Point",         23.0,   1.0),
            ("Bowler",         0.0,  16.0),
            ("MidWicket",    -20.0,  10.0),
            ("LongOn",       -18.0,  58.0),
            ("LongOff",       18.0,  58.0),
            ("DeepMidWicket", -52.0,  22.0),
            ("SquareLeg",    -22.0,  -1.0),
        ],
        "explanation": (
            "Slow left arm (orthodox): for a right-hander this acts like off-spin — "
            "the ball turns in. Pack the leg side: Short Leg, Mid-Wicket, and "
            "Square Leg form the catching ring. One slip for the outside edge. "
            "Bowl over/around the wicket to vary the angle and create the "
            "bat-pad dismissal opportunity."
        ),
        "keywords": [
            "slow left arm", "left arm spin", "orthodox", "left arm orthodox",
            "sla", "left-arm spin",
        ],
    },

    # ── T20 powerplay attacking ──────────────────────────────────────────────
    "powerplay_attack": {
        "preset": "Powerplay",
        "moves": [
            ("WicketKeeper",  0.0, -18.0),
            ("Slip_1",        3.2, -18.5),
            ("Slip_2",        6.2, -17.8),
            ("Gully",        13.5,  -8.0),
            ("Point",        24.0,   1.0),
            ("Cover",        22.0,  11.0),
            ("MidOff",       11.0,  24.0),
            ("MidOn",       -11.0,  24.0),
            ("MidWicket",   -21.0,  10.0),
            ("Bowler",        0.0,  18.0),
            ("FineLeg",     -28.0, -42.0),
        ],
        "explanation": (
            "Powerplay attacking field: two slips and gully for edge catches, "
            "everything else inside the 30-yard circle. Only one boundary fielder "
            "allowed in the powerplay (T20 rules: max 2 outside the circle). "
            "This field dares the batter to drive — every gap behind the wicket "
            "has a catcher. Swing the ball or bowl tight on off stump."
        ),
        "keywords": [
            "powerplay", "power play", "pp", "first 6 overs", "new ball attack",
            "attacking powerplay", "pp attack",
        ],
    },

    # ── Death overs containment ──────────────────────────────────────────────
    "death_overs": {
        "preset": "Death Overs",
        "moves": [
            ("WicketKeeper",   0.0, -14.0),
            ("ShortThird",    16.0, -14.0),
            ("Point",         24.0,   4.0),
            ("ExtraCover",    20.0,  16.0),
            ("MidWicket",    -20.0,  12.0),
            ("Bowler",         0.0,  19.0),
            ("DeepPoint",     52.0,  -6.0),
            ("DeepCover",     48.0,  30.0),
            ("LongOff",       16.0,  58.0),
            ("LongOn",       -16.0,  58.0),
            ("DeepSquareLeg", -52.0, -10.0),
        ],
        "explanation": (
            "Death overs field: five boundary fielders covering all major hitting "
            "zones — Deep Point (square cut), Deep Cover (drive), Long-Off and "
            "Long-On (straight hits), Deep Square Leg (pull/sweep). "
            "Short Third Man cuts off the glance/reverse sweep. "
            "Bowl yorkers and slower balls — variations are key at the death."
        ),
        "keywords": [
            "death", "death overs", "last overs", "last 5", "slog",
            "final overs", "16-20", "44-50",
        ],
    },

    # ── Middle overs containment ─────────────────────────────────────────────
    "middle_overs": {
        "preset": "Middle Overs",
        "moves": [
            ("WicketKeeper",   0.0, -12.0),
            ("ShortThird",    15.0, -12.0),
            ("Point",         24.0,   2.0),
            ("Cover",         22.0,  12.0),
            ("ExtraCover",    14.0,  22.0),
            ("MidWicket",    -20.0,  12.0),
            ("Bowler",         0.0,  18.0),
            ("DeepCover",     50.0,  20.0),
            ("LongOff",       18.0,  54.0),
            ("LongOn",       -18.0,  54.0),
            ("DeepMidWicket", -50.0,  24.0),
        ],
        "explanation": (
            "Middle overs containment: four boundary fielders protect the main "
            "hitting zones, a packed off-side ring restricts singles, and Short Third "
            "cuts off the dab behind square. The aim is dot balls and singles, "
            "forcing the batter to take risks. Bowl wide of off stump with "
            "consistency — tie them down and let wickets come."
        ),
        "keywords": [
            "middle overs", "middle", "7-15", "11-40", "contain", "dot balls",
            "restrict", "dry up", "build pressure",
        ],
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# INTENT CLASSIFIER
# ─────────────────────────────────────────────────────────────────────────────

def classify_intent(text: str) -> str:
    """
    Returns one of:
      "neuro"      — sports neuroscience question
      "tactical"   — field placement, bowling plan, cricket tactics
      "general"    — general cricket explanation
    """
    if is_neuro_question(text):
        return "neuro"

    tactical_keywords = [
        "field", "fielder", "position", "place", "set", "bowl", "bowling",
        "attack", "defend", "preset", "cover", "slip", "gully", "mid",
        "boundary", "powerplay", "death", "spin", "pace", "swing", "short",
        "yorker", "full", "bouncer", "seam", "wicket", "over", "inswing",
        "outswing", "leg spin", "off spin",
    ]
    text_lower = text.lower()
    if any(kw in text_lower for kw in tactical_keywords):
        return "tactical"

    return "general"


def match_tactical_plan(text: str) -> Tuple[str | None, Dict | None]:
    """
    Match a user message to the best TACTICAL_FIELD_PLAN.
    Returns (plan_key, plan_dict) or (None, None).
    """
    text_lower = text.lower()
    best_key   = None
    best_score = 0

    for key, plan in TACTICAL_FIELD_PLANS.items():
        score = sum(1 for kw in plan["keywords"] if kw in text_lower)
        if score > best_score:
            best_score = score
            best_key   = key

    if best_key and best_score > 0:
        return best_key, TACTICAL_FIELD_PLANS[best_key]
    return None, None


# ─────────────────────────────────────────────────────────────────────────────
# GEMINI TOOL DEFINITIONS (used only when HAS_GEMINI)
# ─────────────────────────────────────────────────────────────────────────────

def _build_gemini_tools():
    from google.genai import types as gt
    return [
        gt.FunctionDeclaration(
            name="set_fielding_preset",
            description="Apply a predefined fielding configuration to the 3D field.",
            parameters=gt.Schema(
                type=gt.Type.OBJECT,
                properties={
                    "preset_name": gt.Schema(
                        type=gt.Type.STRING,
                        enum=["Powerplay", "Middle Overs", "Death Overs",
                              "Pace - Attacking", "Spin - Off Spin Ring", "Spin - Leg Spin Trap"]
                    ),
                    "explanation": gt.Schema(type=gt.Type.STRING),
                },
                required=["preset_name", "explanation"]
            )
        ),
        gt.FunctionDeclaration(
            name="move_fielder",
            description="Move a specific fielder to a new x/z position on the field.",
            parameters=gt.Schema(
                type=gt.Type.OBJECT,
                properties={
                    "fielder_name": gt.Schema(type=gt.Type.STRING),
                    "new_x":        gt.Schema(type=gt.Type.NUMBER),
                    "new_z":        gt.Schema(type=gt.Type.NUMBER),
                    "explanation":  gt.Schema(type=gt.Type.STRING),
                },
                required=["fielder_name", "new_x", "new_z", "explanation"]
            )
        ),
        gt.FunctionDeclaration(
            name="highlight_position",
            description="Pulse/highlight a fielder on the 3D field.",
            parameters=gt.Schema(
                type=gt.Type.OBJECT,
                properties={
                    "position_name":    gt.Schema(type=gt.Type.STRING),
                    "duration_seconds": gt.Schema(type=gt.Type.NUMBER),
                },
                required=["position_name"]
            )
        ),
        gt.FunctionDeclaration(
            name="simulate_shot",
            description="Trigger a ball trajectory simulation on the 3D field.",
            parameters=gt.Schema(
                type=gt.Type.OBJECT,
                properties={
                    "shot_type": gt.Schema(
                        type=gt.Type.STRING,
                        enum=["Cover Drive", "Lofted Straight Drive", "Square Cut",
                              "Pull Shot", "Sweep Shot", "Ramp Shot", "Slog Sweep"]
                    ),
                    "explanation": gt.Schema(type=gt.Type.STRING),
                },
                required=["shot_type", "explanation"]
            )
        ),
        gt.FunctionDeclaration(
            name="set_batter_handedness",
            description="Switch batter between RHB and LHB.",
            parameters=gt.Schema(
                type=gt.Type.OBJECT,
                properties={
                    "handedness": gt.Schema(type=gt.Type.STRING, enum=["RHB", "LHB"])
                },
                required=["handedness"]
            )
        ),
    ]


GEMINI_SYSTEM_PROMPT = """
You are the NeuroSport Cricket Coach — an expert AI agent that combines
deep cricket tactics with sports neuroscience.

FIELD PLACEMENT:
- When asked about bowling plans, ALWAYS apply a field using set_fielding_preset
  and fine-tune individual positions with move_fielder.
- After setting the field, explain WHY each key position is placed there.
- Highlight the 2-3 most important fielders using highlight_position.

NEUROSCIENCE:
- If asked about fatigue, reaction time, brain injuries, motor learning,
  sleep, pressure, or other neuroscience topics, give evidence-based answers.
- Connect neuroscience insights to specific fielding decisions (e.g.
  "place your fastest reactor at slip in the first 15 overs before fatigue sets in").

STYLE:
- Concise, expert, confident. 3-5 sentences unless detail is requested.
- Always link field positions to actual wicket-taking or run-saving outcomes.
- No filler phrases. Get to the point.
"""


# ─────────────────────────────────────────────────────────────────────────────
# MAIN COACH SESSION CLASS
# ─────────────────────────────────────────────────────────────────────────────

class CricketCoachSession:
    """
    Unified AI coaching agent.
    Handles: field placement requests, tactical questions, neuroscience questions.
    Works with or without Gemini API key.
    """

    def __init__(self, websocket_server=None):
        self.websocket_server = websocket_server
        self.neuro_agent = NeuroAgent()
        self.chat = None

        if HAS_GEMINI:
            from google.genai import types as gt
            tools = _build_gemini_tools()
            self.chat = _gemini_client.chats.create(
                model="gemini-2.5-flash",
                config=gt.GenerateContentConfig(
                    system_instruction=GEMINI_SYSTEM_PROMPT,
                    tools=[gt.Tool(function_declarations=tools)],
                    temperature=0.6,
                    max_output_tokens=800,
                )
            )

    # ── Public entry point ────────────────────────────────────────────────────

    async def send_message(self, text: str) -> Dict[str, Any]:
        """
        Route a user message to the correct handler.
        Returns: {"action": "coach_response", "text": str, "tool_actions": list}
        """
        if text == "__INIT_GREETING__":
            return {
                "action": "coach_response",
                "text": (
                    "Hi! I'm your NeuroSport Cricket Coach — I combine tactical "
                    "fielding expertise with sports neuroscience. Ask me to set a "
                    "field for any bowling plan (e.g. 'short pitched bowling', "
                    "'outswing attack', 'death overs'), or ask me anything about "
                    "the science behind cricket performance!"
                ),
                "tool_actions": []
            }

        intent = classify_intent(text)
        logger.info("Intent: %s | Message: %s", intent, text[:60])

        if intent == "neuro":
            return await self._handle_neuro(text)

        if intent == "tactical":
            return await self._handle_tactical(text)

        return await self._handle_general(text)

    # ── Neuroscience handler ──────────────────────────────────────────────────

    async def _handle_neuro(self, text: str) -> Dict[str, Any]:
        """Route to NeuroSport LLM or fallback knowledge base."""
        field_context = {}
        if self.websocket_server:
            try:
                payload = self.websocket_server.build_state_payload()
                field_context = {
                    "preset":         payload.get("preset", ""),
                    "coverage_score": payload.get("coverage_score", 0),
                    "pursuit":        payload.get("pursuit", {}),
                }
            except Exception:
                pass

        answer = await self.neuro_agent.answer(text, field_context)
        return {
            "action":       "coach_response",
            "text":         answer,
            "tool_actions": [],
        }

    # ── Tactical handler ──────────────────────────────────────────────────────

    async def _handle_tactical(self, text: str) -> Dict[str, Any]:
        """
        Try rule-based TACTICAL_FIELD_PLANS first.
        If no match and Gemini is available, fall through to Gemini.
        """
        plan_key, plan = match_tactical_plan(text)

        if plan:
            # Apply the field via server + collect tool_actions
            tool_actions = await self._apply_plan(plan)

            # Build explanation text, appending any compliance corrections
            explanation = plan["explanation"]
            for ta in tool_actions:
                if ta.get("tool") == "_compliance_correction":
                    phase = ta.get("phase_label", "this phase")
                    max_out = ta.get("max_outside", 5)
                    moved = [c["fielder"] for c in ta.get("changes", [])]
                    explanation += (
                        f"\n\n⚖️ ICC Rule applied: {phase} allows max {max_out} fielder(s) "
                        f"outside the 30-yard circle. "
                        f"{', '.join(moved)} moved infield automatically to stay compliant."
                    )

            return {
                "action":       "coach_response",
                "text":         explanation,
                "tool_actions": tool_actions,
            }

        # No local plan match — try Gemini if available
        if HAS_GEMINI and self.chat:
            return await self._handle_via_gemini(text)

        # Pure fallback — explain without setting field
        return {
            "action": "coach_response",
            "text": (
                "I can set specific fields for: short-pitched bowling, yorkers, "
                "outswing, inswing, off-spin, leg-spin, slow left arm, powerplay "
                "attack, middle overs containment, and death overs. "
                "Could you describe your bowling plan in those terms?"
            ),
            "tool_actions": [],
        }

    # ── General handler ───────────────────────────────────────────────────────

    async def _handle_general(self, text: str) -> Dict[str, Any]:
        if HAS_GEMINI and self.chat:
            return await self._handle_via_gemini(text)

        # Rule-based general answer
        answer = self._rule_based_general(text)
        return {
            "action":       "coach_response",
            "text":         answer,
            "tool_actions": [],
        }

    # ── Apply a tactical plan ─────────────────────────────────────────────────

    async def _apply_plan(self, plan: Dict) -> List[Dict]:
        """
        Apply a TACTICAL_FIELD_PLAN: set preset, fine-tune positions, then
        run a final ICC compliance pass so the resulting field always satisfies
        the current phase's fielding restriction rules.
        """
        tool_actions = []
        srv = self.websocket_server

        if not srv:
            return tool_actions

        # 1. Set base preset (compliance is run inside set_preset)
        preset = plan.get("preset")
        if preset:
            await srv.set_preset(preset)
            tool_actions.append({"tool": "set_fielding_preset", "args": {"preset_name": preset}})

        # 2. Fine-tune individual positions
        for (name, x, z) in plan.get("moves", []):
            await srv.update_fielder(name, x, z)
            tool_actions.append({
                "tool": "move_fielder",
                "args": {"fielder_name": name, "new_x": x, "new_z": z}
            })

        # 3. Final compliance pass on the fully assembled field
        corrected, compliance = await srv._apply_compliance(srv.fielders)
        if compliance.get("changes"):
            srv.fielders = corrected
            srv.last_compliance = compliance
            await srv.broadcast_state()
            tool_actions.append({
                "tool": "_compliance_correction",
                "changes": compliance["changes"],
                "phase_label": compliance.get("phase_label", ""),
                "max_outside": compliance.get("max_outside", 5),
            })

        return tool_actions

    # ── Gemini path ───────────────────────────────────────────────────────────

    async def _handle_via_gemini(self, text: str) -> Dict[str, Any]:
        """Send message to Gemini and execute any tool calls it returns."""
        try:
            response     = self.chat.send_message(text)
            tool_actions = []
            final_text   = ""

            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.text:
                        final_text += part.text

                    if part.function_call:
                        action = await self._execute_tool_call(part.function_call)
                        if action:
                            tool_actions.append(action)

                        from google.genai import types as gt
                        fn_resp = gt.Part(
                            function_response=gt.FunctionResponse(
                                name=part.function_call.name,
                                response={"status": "success"}
                            )
                        )
                        follow = self.chat.send_message(fn_resp)
                        if follow.candidates and follow.candidates[0].content.parts:
                            for fp in follow.candidates[0].content.parts:
                                if fp.text:
                                    final_text += " " + fp.text

            return {
                "action":       "coach_response",
                "text":         final_text.strip(),
                "tool_actions": tool_actions,
            }

        except Exception as exc:
            logger.error("Gemini error: %s", exc)
            return {
                "action": "coach_response",
                "text":   f"I encountered an error processing that: {exc}",
                "tool_actions": [],
            }

    async def _execute_tool_call(self, function_call) -> Dict | None:
        name = function_call.name
        args = function_call.args
        srv  = self.websocket_server

        if not srv:
            return {"tool": name, "args": args}

        if name == "set_fielding_preset":
            await srv.set_preset(args["preset_name"])

        elif name == "move_fielder":
            await srv.update_fielder(args["fielder_name"], args["new_x"], args["new_z"])

        elif name == "highlight_position":
            await srv.broadcast_command({
                "action":   "highlight_fielder",
                "name":     args["position_name"],
                "duration": args.get("duration_seconds", 3.0),
            })

        elif name == "simulate_shot":
            await srv.simulate_shot(args["shot_type"])

        elif name == "set_batter_handedness":
            await srv.set_handedness(args["handedness"])

        return {"tool": name, "args": args}

    # ── Rule-based general knowledge ──────────────────────────────────────────

    def _rule_based_general(self, text: str) -> str:
        """Answer basic cricket questions without any AI API."""
        text_lower = text.lower()

        if "slip" in text_lower:
            return (
                "Slips are close catching positions behind the wicket on the off side. "
                "First Slip stands just outside the keeper, Second Slip slightly wider, "
                "Third Slip wider still. They catch outside edges off pace and swing. "
                "Use slips with the new ball when the pitch offers movement — "
                "drop them in the middle overs when the ball stops swinging."
            )
        if "voronoi" in text_lower or "coverage" in text_lower or "territory" in text_lower:
            return (
                "The Voronoi diagram divides the field into territories — each fielder "
                "owns the region of the field closest to them. Smaller territory (green) "
                "means the fielder is in a concentrated defensive cluster. Larger territory "
                "(red, Critical Gap) means there's a big open zone the batter can target. "
                "Aim for balanced (cyan) territories with no red zones for solid coverage."
            )
        if "lhb" in text_lower or "left hand" in text_lower or "left-hand" in text_lower:
            return (
                "For a left-handed batter (LHB), the field mirrors: off-side becomes leg-side. "
                "Cover becomes Mid-Wicket, Slip cordons shift to the other side, "
                "Fine Leg moves to Third Man's position. Use the LHB toggle to auto-mirror "
                "the current field, or I can set a specific LHB field for your bowling plan."
            )

        # Catch-all
        return (
            "I can help with field placements for any bowling plan, explain fielding positions, "
            "or answer sports neuroscience questions. Try asking: "
            "'Set a field for short-pitched bowling', "
            "'What field for outswing?', or "
            "'How does fatigue affect a fielder's reaction time?'"
        )
