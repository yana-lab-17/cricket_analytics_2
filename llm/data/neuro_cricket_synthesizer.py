"""
neuro_cricket_synthesizer.py
Deterministic Neuro-Biomechanical Transduction Engine.
Translates raw match delivery coordinates (speed, line, length, outcome)
into deep sports-science text grounded in human ocular-motor physiology,
corticospinal conduction latencies, and cerebellar predictive internal models.
"""

import math
from typing import Dict, Any, Generator

class NeuroCricketTransducer:
    """Computes exact biophysical and ocular-motor metrics for any delivery."""
    PITCH_LENGTH_METERS = 20.12
    RELEASE_OFFSET_METERS = 1.82 # Distance in front of bowling stumps
    BATTER_CREASE_METERS = 1.22  # Popping crease to batting stumps
    EFFECTIVE_DISTANCE = PITCH_LENGTH_METERS - RELEASE_OFFSET_METERS # ~18.3 meters

    # Human Ocular & Neuromuscular Constants
    RETINAL_TRANSDUCTION_MS = 30.0
    LGN_TO_V1_MS = 50.0
    SACCADIC_LATENCY_MS = 195.0
    SACCADIC_SUPPRESSION_MS = 40.0
    NEUROMUSCULAR_CONDUCTION_MS = 190.0

    @classmethod
    def compute_telemetry(cls, speed_kmh: float, length_type: str, line_type: str) -> Dict[str, Any]:
        """Calculates precise physical and neurological flight parameters."""
        v_ms = max(15.0, speed_kmh / 3.6)
        total_flight_time_ms = (cls.EFFECTIVE_DISTANCE / v_ms) * 1000.0

        # Bounce point estimation based on bowling length
        length_pitch_ratios = {
            "yorker": 0.88,        # pitches very full (~2-3m from batter)
            "full": 0.72,          # pitches ~4-5m from batter
            "good_length": 0.60,   # pitches ~6-8m from batter
            "short_of_length": 0.50,
            "bouncer": 0.38        # pitches ~10-12m from batter
        }
        pitch_ratio = length_pitch_ratios.get(length_type, 0.60)
        time_to_pitch_ms = total_flight_time_ms * pitch_ratio
        post_pitch_decision_window_ms = total_flight_time_ms - time_to_pitch_ms

        # Vulnerability to late movement:
        # If post-pitch window < (Saccade latency + Suppression), deviation happens in blind spot
        saccade_blind_threshold = cls.SACCADIC_LATENCY_MS + cls.SACCADIC_SUPPRESSION_MS
        is_in_saccadic_blind_zone = post_pitch_decision_window_ms <= saccade_blind_threshold

        # Cognitive Load Index (0 - 100 scale)
        cognitive_load = min(100.0, max(10.0, (speed_kmh / 155.0) * 100.0 * (1.0 + (1.0 - pitch_ratio) * 0.3)))

        return {
            "speed_kmh": round(speed_kmh, 1),
            "velocity_ms": round(v_ms, 2),
            "total_flight_ms": round(total_flight_time_ms, 1),
            "time_to_pitch_ms": round(time_to_pitch_ms, 1),
            "post_pitch_decision_window_ms": round(post_pitch_decision_window_ms, 1),
            "saccadic_latency_ms": cls.SACCADIC_LATENCY_MS,
            "saccadic_suppression_ms": cls.SACCADIC_SUPPRESSION_MS,
            "neuromuscular_conduction_ms": cls.NEUROMUSCULAR_CONDUCTION_MS,
            "is_in_saccadic_blind_zone": is_in_saccadic_blind_zone,
            "cognitive_load_score": round(cognitive_load, 1)
        }

    @classmethod
    def synthesize_narrative(
        cls,
        format_type: str,
        bowler: str,
        batter: str,
        speed_kmh: float,
        length: str,
        line: str,
        outcome: str,
        runs: int
    ) -> str:
        """Translates a real ball delivery into deeply grounded sports-neuroscience reasoning."""
        t = cls.compute_telemetry(speed_kmh, length, line)

        narrative = [
            f"<|think|>",
            f"1. Kinematic Vector: {bowler} deliveries to {batter} at {t['speed_kmh']} km/h ({t['velocity_ms']} m/s). Line: {line}, Length: {length}.",
            f"2. Temporal Budget: Total flight duration = {t['total_flight_ms']} ms. Ball pitches at t = {t['time_to_pitch_ms']} ms.",
            f"3. Ocular Latency: Post-pitch decision window = {t['post_pitch_decision_window_ms']} ms against a saccadic latency threshold of {t['saccadic_latency_ms']} ms.",
        ]

        if t["is_in_saccadic_blind_zone"]:
            narrative.append(
                f"4. Biophysical Conflict: Post-pitch window ({t['post_pitch_decision_window_ms']} ms) is less than the saccadic latency + suppression envelope ({t['saccadic_latency_ms'] + t['saccadic_suppression_ms']} ms). "
                f"The batter cannot visually track late trajectory changes off the seam. Motor plan MUST rely on anticipatory forward models from release kinematics."
            )
        else:
            narrative.append(
                f"4. Biophysical Accommodation: Post-pitch window ({t['post_pitch_decision_window_ms']} ms) grants sufficient foveal fixation time for motor adjustment, favoring back-foot stroke play."
            )

        narrative.append(f"5. Cognitive Load Index: {t['cognitive_load_score']}/100. Format: {format_type}. Outcome: {outcome} ({runs} runs).")
        narrative.append(f"</think>")
        narrative.append(f"<|biomechanical_breakdown|>")

        if "WICKET" in outcome or "OUT" in outcome:
            narrative.append(
                f"DISMISSAL ANALYSIS: {bowler} exploited the batter's neuromuscular conduction ceiling. "
                f"At {t['speed_kmh']} km/h, the ball arrived at the popping crease in {t['total_flight_ms']} ms. "
                f"Because the post-pitch decision window ({t['post_pitch_decision_window_ms']} ms) fell inside the batter's 195 ms foveal saccade window, "
                f"the batter's motor cortex was forced into an automated efference copy prediction. Subtle seam movement induced a cerebellar forward model error, "
                f"resulting in a mistimed contact ({outcome})."
            )
        elif runs >= 4:
            narrative.append(
                f"BOUNDARY BREAKDOWN: {batter} successfully anticipated the trajectory during the first 120 ms of ball flight. "
                f"By pre-emptively uncoiling the pelvic-thoracic kinetic chain before the ball pitched at {t['time_to_pitch_ms']} ms, "
                f"the batter bypassed post-pitch saccadic latency entirely, accelerating the bat face cleanly through the hitting arc for a boundary."
            )
        else:
            narrative.append(
                f"TACTICAL STROKE: {batter} executed a controlled defensive block. "
                f"Under a cognitive load score of {t['cognitive_load_score']}/100, the corticospinal motor pathway prioritized central sweet-spot bat alignment over bat speed, "
                f"nullifying the bowler's seam deviation."
            )

        narrative.append("<|endoftext|>\n")
        return "\n".join(narrative)

