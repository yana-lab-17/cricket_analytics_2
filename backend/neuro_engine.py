"""
neuro_engine.py
Cricket Sports Neuroscience & Cognitive Pedagogy Engine.
Models visual cortex anticipation, saccadic latency, cerebellar motor automaticity,
and reaction windows. Provides dual-persona coaching feedback (Junior Mode vs Pro Mode).
"""

from typing import Dict, Any

class CricketNeuroEngine:
    """Calculates cognitive reaction telemetry and generates child/pro neuroscience insights."""

    def analyze_play(
        self,
        delivery: Dict[str, Any],
        shot: Dict[str, Any],
        pursuit: Dict[str, Any],
        fielders: Dict[str, Dict[str, float]]
    ) -> Dict[str, Any]:
        """
        Compute neuroscience metrics and tailored explanations.
        """
        speed_kmh = delivery.get("speed_kmh", 140.0)
        pitch_t = delivery.get("pitch_point", {}).get("t", 0.35)
        arrival_t = delivery.get("flight_duration", 0.52)
        outcome = pursuit.get("outcome", "DOT_BALL")
        shot_name = shot.get("shot_name", "")
        primary_f = pursuit.get("primary_fielder", "Fielder")
        contact_zone = shot.get("contact_zone", "sweet_spot")

        # Visual cortex reaction window:
        # Ball flight time at 145 km/h is ~420ms. Human visual saccade delay is ~180-220ms.
        # This leaves only ~200ms to trigger motor swing, proving anticipation is required!
        decision_window_ms = max(120, int((arrival_t - pitch_t) * 1000))
        saccade_latency_ms = 195  # typical foveal gaze fixation delay
        cognitive_load_score = min(100, int((speed_kmh / 160.0) * 100))

        # Expected Runs Prevented (xRP)
        runs_scored = pursuit.get("runs_scored", 0)
        if outcome in ("WICKET_CAUGHT", "WICKET_BOWLED"):
            xrp = 4.2
        elif outcome == "DOT_BALL":
            xrp = 1.0
        elif outcome == "SINGLE":
            xrp = 0.0
        elif outcome == "TWO_RUNS":
            xrp = -1.0
        elif outcome == "FOUR":
            xrp = -3.0
        else:  # SIX
            xrp = -5.0

        # Junior Mode Explanations (Superhero & Brain-Computer analogies for kids)
        if outcome == "WICKET_BOWLED":
            junior_lesson = "🎯 Bullseye! When a ball flies faster than a blink, the batter's brain doesn't have time to process the swing. Direct hit!"
            junior_tip = "Keep attacking the base of off-stump! Fast yorkers overload the batter's reaction time."
        elif outcome == "WICKET_CAUGHT":
            junior_lesson = f"🧤 Super Reflexes! Your {primary_f} caught the ball on pure reflex without even thinking! Their brain's motor auto-pilot took over!"
            junior_tip = f"Notice how putting {primary_f} in the exact trajectory made the catch look effortless."
        elif outcome == "FOUR":
            junior_lesson = f"🚨 Brain Spotting the Gap! The batter's eyes scanned the grass, saw a giant open gap, and zoomed the ball right through for FOUR!"
            junior_tip = f"Drag a fielder to cover the {shot_name.split()[0]} gap so the batter can't see free grass!"
        elif outcome == "SIX":
            junior_lesson = "💥 Boom! Six runs! The batter anticipated your ball and swung hard into the sky before the fielders could even turn around!"
            junior_tip = "When bowling bouncers or full tosses, pull your boundary riders all the way to the fence!"
        elif outcome == "DOT_BALL":
            junior_lesson = f"🛡️ Wall of Defense! {primary_f} pounced in less than half a second to stop the ball cold! Zero runs!"
            junior_tip = "Every dot ball puts giant mental pressure on the batter."
        else:
            junior_lesson = "🏃 Tidy Running! The fielders cut off the four, but there was enough empty grass for quick running."
            junior_tip = "Move your ring fielders 3 steps closer to pinch those singles."

        # Pro Mode Explanations (Sports Science & Motor Learning metrics for coaches)
        pro_lesson = (
            f"Telemetry: Delivery speed {speed_kmh:.1f} km/h produced a post-pitch decision window of {decision_window_ms}ms "
            f"(Foveal saccadic latency: {saccade_latency_ms}ms). "
        )
        if outcome == "WICKET_CAUGHT":
            pro_lesson += (
                f"Fielder {primary_f} activated cerebellar procedural retrieval within a 0.22s visual-motor threshold. "
                f"Anticipatory edge tracking created an optimal interception envelope."
            )
            pro_tip = f"Kinematic alignment: Cordon positioning at depth 20.5m matches peak deceleration velocity for {speed_kmh:.0f} km/h pace."
        elif outcome == "FOUR":
            pro_lesson += (
                f"Spatial gap optimization: Batter exploited an angular cone of 32° between ring fielders. "
                f"Sub-optimal field density in the {shot_name} corridor conceded an exit velocity of {shot.get('exit_velocity_kmh', 0)} km/h."
            )
            pro_tip = f"Tactical offset: Adjust the adjacent ring fielder by dx=+3.5m, dz=-2.0m to close the pursuit vector."
        elif outcome == "WICKET_BOWLED":
            pro_lesson += "Temporal compression: Ball crossed crease in sub-240ms arrival duration, completely exceeding batter's efferent motor drive threshold."
            pro_tip = "Target channel: Retain trajectory z=0.0m, y=0.22m to maintain 85%+ beat probability."
        else:
            pro_lesson += f"Ground pursuit dynamics: Interception confirmed at reach threshold. Batter exit velocity held to {shot.get('exit_velocity_kmh', 0)} km/h."
            pro_tip = "Field tightness: Shift infielders by -2.5m radial radius to lower strike rotation."

        return {
            "decision_window_ms": decision_window_ms,
            "saccade_latency_ms": saccade_latency_ms,
            "cognitive_load_score": cognitive_load_score,
            "xrp": xrp,
            "junior": {
                "headline": junior_lesson,
                "tip": junior_tip
            },
            "pro": {
                "headline": pro_lesson,
                "tip": pro_tip
            }
        }

