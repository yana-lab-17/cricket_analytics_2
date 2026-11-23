"""
neuro_agent.py
--------------
NeuroSport bridge for the Cricket Fielding Analytics application.

When the user asks a neuroscience question (fatigue, reaction time, cognitive
load, motor learning, sleep, psychology, brain science), this module builds a
rich context-aware prompt and calls the NeuroSport LLM API.

While NeuroSport is still training, it falls back to a rule-based expert
knowledge base that covers the most common sports neuroscience topics relevant
to cricket fielding.

Usage:
    from backend.neuro_agent import NeuroAgent
    agent = NeuroAgent()
    answer = await agent.answer(question, field_context)
"""

import os
import re
import json
import logging
import asyncio
from typing import Dict, Any

logger = logging.getLogger("NeuroAgent")

# ── NeuroSport API config (set in environment once model is trained) ──────────
NEUROSPORT_URL = os.getenv("NEUROSPORT_URL", "http://localhost:8000")
NEUROSPORT_API_KEY = os.getenv("NEUROSPORT_API_KEY", "")

# ── Keywords that trigger neuroscience routing ────────────────────────────────
NEURO_KEYWORDS = [
    # Physiology & fatigue
    "fatigue", "tired", "exhausted", "energy", "stamina", "endurance",
    "lactic acid", "aerobic", "anaerobic", "vo2", "heart rate", "breathing",
    # Brain & cognition
    "brain", "cognitive", "cognition", "mental", "focus", "concentration",
    "attention", "decision", "reaction time", "reflex", "neural", "neuroscience",
    "neuro", "cortex", "dopamine", "serotonin", "adrenaline", "cortisol",
    "bdnf", "hippocampus", "motor learning", "motor cortex", "cerebellum",
    # Injury & recovery
    "concussion", "head injury", "tbi", "cte", "injury", "recover",
    "rehabilitation", "rehab", "sleep", "rest", "recovery",
    # Psychology & performance
    "anxiety", "pressure", "stress", "confidence", "fear", "psychology",
    "psychophysiology", "arousal", "flow state", "choking", "yips",
    "visualization", "mental training", "mindfulness",
    # Physical performance
    "speed", "agility", "acceleration", "explosive", "sprint", "muscle",
    "proprioception", "balance", "coordination", "spatial awareness",
    "depth perception", "peripheral vision", "eye tracking",
]


def is_neuro_question(text: str) -> bool:
    """Return True if the question is about neuroscience / sports science."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in NEURO_KEYWORDS)


# ── Fallback expert knowledge base (used when NeuroSport API is unavailable) ──
NEURO_KNOWLEDGE = {
    "reaction_time": """
A fielder's reaction time in cricket is typically 180-250ms for visual stimuli.
Neurologically, this involves the visual cortex detecting the ball, signals
travelling via the dorsal stream to the motor cortex, and the cerebellum
coordinating the movement. Elite fielders show lower reaction times due to
superior predictive processing — their brains anticipate ball trajectory based
on the bowler's action before the ball leaves the hand. Fatigue increases
reaction time by 15-30ms because neural conduction slows and dopaminergic
signalling in the prefrontal cortex is impaired. Placing your sharpest reflexes
at slip or gully is therefore most valuable in the first 10-15 overs before
fatigue sets in.
""",
    "fatigue": """
Fielding fatigue has two components: physical (muscular lactate buildup,
glycogen depletion) and cognitive (mental fatigue from sustained attention).
Cognitively, extended focus depletes the prefrontal cortex's capacity for
executive function. After 3-4 hours of Test match fielding, decision-making
accuracy drops measurably. This is why close catching positions like slip and
gully should be rotated — you want the most mentally fresh fielders in those
positions. In T20s, the shorter duration means cognitive fatigue is less
relevant than physical explosive capability.
""",
    "motor_learning": """
Motor learning for fielding relies on the cerebellum and basal ganglia forming
procedural memory through repetition. A fielder needs roughly 3,000-5,000
repetitions of a catching action before it becomes automatic — handled by
implicit memory rather than conscious attention. During the early learning
phase, the prefrontal cortex is heavily involved (slow, deliberate). As the
skill becomes automatic, it shifts to cerebellar circuits (fast, unconscious).
This is why experienced fielders react faster under pressure — they bypass
conscious decision-making entirely.
""",
    "spatial_awareness": """
Spatial awareness in fielding is governed by the parietal lobe, which integrates
visual, proprioceptive, and vestibular signals into a real-time spatial map.
Elite fielders show larger activation in this region. The key metric is
'spatial anticipation' — the brain's ability to predict where a ball will land
1-2 seconds before it gets there. This is trainable through deliberate practice
that specifically challenges spatial prediction (e.g. fielding with randomised
ball release angles). Voronoi territory awareness — knowing intuitively how
much ground you cover — is a learnable spatial skill.
""",
    "concussion": """
Sports concussion in cricket most commonly affects wicket keepers and close-in
fielders. A concussion is a traumatic brain injury caused by biomechanical
forces that temporarily disrupts normal brain function. Neurologically, it
causes diffuse axonal stress, glutamate excitotoxicity, and ionic flux
(potassium/calcium imbalance). Key symptoms: headache, cognitive slowing,
balance disruption. For fielding: do NOT return to fielding until fully
symptom-free. The return-to-play protocol (6 stages: rest → light aerobic →
sport-specific → non-contact drills → full practice → match play) exists
because a second concussion before the first heals risks Second Impact Syndrome
— potentially catastrophic brain swelling. Biomarkers like GFAP and S100B can
confirm brain tissue involvement.
""",
    "sleep": """
Sleep is the single most powerful recovery tool for a cricketer's brain. During
deep sleep (slow-wave sleep), the brain consolidates motor skills practiced
during the day — this is when fielding technique literally 'downloads' into
long-term memory. REM sleep processes tactical decision-making and emotional
regulation. Sleep deprivation of even 1-2 hours reduces reaction time, impairs
peripheral vision, and lowers catch probability significantly. For Test cricket,
sleep quality between days matters enormously. Elite teams now use melatonin
timing, light therapy, and temperature regulation to optimise sleep quality on
tour.
""",
    "pressure": """
Performance under pressure is governed by the interplay between the prefrontal
cortex (executive control) and the amygdala (threat detection). When pressure
spikes, the amygdala can hijack motor programs — this is the neurological
mechanism behind 'the yips' and choking. Cortisol (stress hormone) at high
levels impairs working memory and fine motor control. Conversely, moderate
arousal (the Yerkes-Dodson optimal zone) enhances performance. Elite fielders
use pre-performance routines to regulate this arousal: controlled breathing
activates the parasympathetic nervous system, slowing heart rate and cortisol
release, allowing the prefrontal cortex to maintain control. Placing nervous
fielders away from high-pressure close catching positions is sound neuroscience.
""",
    "proprioception": """
Proprioception — the body's sense of its own position in space — is critical
for fielding footwork. Mechanoreceptors in joints, tendons and muscles feed
signals continuously to the cerebellum, which coordinates balance and movement
without conscious attention. Ankle proprioception is especially important for
fielders making sudden direction changes. Weak proprioception (common after
ankle sprains) leads to slower lateral movements and increased re-injury risk.
Fielders recovering from ankle injuries should be placed in lower-demand
positions (long-on, long-off) rather than at point or cover, where rapid
multi-directional movement is required.
""",
    "visualization": """
Mental visualisation (mental imagery) activates the same motor cortex pathways
as physical execution — functional MRI studies confirm this. For fielders,
5-10 minutes of vivid mental rehearsal before play activates cerebellar motor
programs, effectively 'pre-warming' the neural circuits needed for catching and
throwing. The key is kinaesthetic imagery (feeling the movement) rather than
just watching it visually. Elite fielders like Jonty Rhodes attributed
extraordinary spatial positioning to pre-match visualisation routines. Building
a visualisation habit can shorten the time needed to enter automatic processing
during high-pressure moments.
""",
}


def _get_fallback_answer(question: str, field_context: Dict[str, Any]) -> str:
    """
    Rule-based fallback when NeuroSport API is unavailable.
    Matches the question to the most relevant knowledge entry.
    """
    q_lower = question.lower()

    # Score each topic by keyword overlap
    topic_scores = {}
    topic_keys = {
        "reaction_time": ["reaction", "reflex", "response time", "react"],
        "fatigue":       ["fatigue", "tired", "exhausted", "stamina", "energy"],
        "motor_learning":["motor", "learn", "practice", "repetition", "automatic"],
        "spatial_awareness": ["spatial", "awareness", "position", "territory", "space"],
        "concussion":    ["concussion", "head", "brain injury", "tbi", "return to play"],
        "sleep":         ["sleep", "rest", "recovery", "overnight"],
        "pressure":      ["pressure", "anxiety", "stress", "yips", "choke", "confidence"],
        "proprioception":["proprioception", "balance", "ankle", "footwork", "coordination"],
        "visualization": ["visuali", "mental rehearsal", "imagery", "mental practice"],
    }

    for topic, keywords in topic_keys.items():
        score = sum(1 for kw in keywords if kw in q_lower)
        if score > 0:
            topic_scores[topic] = score

    if not topic_scores:
        # Generic fallback
        return (
            "That's a great sports neuroscience question! The NeuroSport LLM is "
            "currently being trained on sports neuroscience literature. Once it's "
            "deployed, it will give you evidence-based answers grounded in peer-reviewed "
            "research. For now: in general, elite fielding performance depends on "
            "reaction time (180-250ms), spatial anticipation (parietal lobe), and "
            "fatigue management (cognitive load peaks after 3+ hours of fielding). "
            "Your best fielders belong in the positions where those qualities matter most."
        )

    best_topic = max(topic_scores, key=topic_scores.get)
    knowledge = NEURO_KNOWLEDGE[best_topic].strip()

    # Personalise with current field context if available
    context_note = ""
    if field_context:
        coverage = field_context.get("coverage_score", 0)
        preset = field_context.get("preset", "")
        primary = field_context.get("pursuit", {}).get("primary_fielder", "")
        if coverage and preset:
            context_note = (
                f"\n\nIn your current {preset} setup (coverage: {coverage}%), "
            )
            if primary:
                context_note += (
                    f"{primary} is your primary interceptor — neuroscience suggests "
                    f"placing your sharpest and least fatigued athlete here."
                )

    return f"**Sports Neuroscience Insight:**\n\n{knowledge}{context_note}"


async def _call_neurosport_api(question: str, field_context: Dict[str, Any]) -> str | None:
    """
    Call the NeuroSport LLM API if it's running.
    Returns the response text, or None if unavailable.
    """
    try:
        import urllib.request
        import urllib.error

        # Build a context-enriched prompt
        context_block = ""
        if field_context:
            coverage = field_context.get("coverage_score", "unknown")
            preset   = field_context.get("preset", "unknown")
            outcome  = field_context.get("pursuit", {}).get("tactical_outcome", "")
            context_block = (
                f"\n\nCurrent match context: {preset} field, "
                f"{coverage}% coverage score, tactical outcome: {outcome}."
            )

        payload = json.dumps({
            "messages": [
                {
                    "role": "user",
                    "content": question + context_block
                }
            ],
            "use_graph_context": True,
            "max_new_tokens": 400,
        }).encode("utf-8")

        headers = {"Content-Type": "application/json"}
        if NEUROSPORT_API_KEY:
            headers["Authorization"] = f"Bearer {NEUROSPORT_API_KEY}"

        req = urllib.request.Request(
            f"{NEUROSPORT_URL}/chat",
            data=payload,
            headers=headers,
            method="POST",
        )

        loop = asyncio.get_event_loop()
        def _do_request():
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))

        result = await loop.run_in_executor(None, _do_request)
        return result.get("message", {}).get("content", None)

    except Exception as exc:
        logger.debug("NeuroSport API unavailable: %s", exc)
        return None


class NeuroAgent:
    """
    Sports neuroscience expert for the cricket fielding application.
    Tries the NeuroSport LLM API first; falls back to rule-based knowledge.
    """

    async def answer(self, question: str, field_context: Dict[str, Any] = None) -> str:
        """Answer a neuroscience question with optional fielding context."""
        context = field_context or {}

        # Try live NeuroSport API first
        api_answer = await _call_neurosport_api(question, context)
        if api_answer and len(api_answer.strip()) > 30:
            logger.info("NeuroSport API answered the question")
            return api_answer

        # Fallback to built-in knowledge base
        logger.info("Using fallback neuro knowledge base")
        return _get_fallback_answer(question, context)
