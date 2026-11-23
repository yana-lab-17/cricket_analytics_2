"""
pedagogy.py
Educational Coaching & Tactical Concept Explainer.
Generates instant, child-friendly insights explaining WHY a shot occurred
based on the bowling line/length and where fielders were placed.
"""

from typing import Dict, Any

class TacticalExplainer:
    """Explains fielding concepts intuitively for young players and professionals."""

    def explain_play(
        self,
        delivery: Dict[str, Any],
        shot: Dict[str, Any],
        pursuit: Dict[str, Any],
        fielders: Dict[str, Dict[str, float]]
    ) -> Dict[str, str]:
        """
        Generate contextual coaching explanation.
        Returns:
          - concept_title: e.g. "Protecting the Off-Side Corridor"
          - lesson: Educational explanation of why that happened
          - tactical_tip: What to adjust next
        """
        outcome = pursuit.get("outcome", "DOT_BALL")
        shot_name = shot.get("shot_name", "")
        line = delivery.get("line", "")
        length = delivery.get("length", "")
        primary_f = pursuit.get("primary_fielder", "")

        if outcome == "WICKET_BOWLED":
            return {
                "concept_title": "🎯 The Stumps Target Principle",
                "lesson": "Fast, accurate bowling directly at the base of off/middle stump leaves the batter no room to swing. Even without fielders, a lethal yorker wins the battle!",
                "tactical_tip": "Notice how targeting the stumps directly forces the batter into a panicked defensive shot."
            }

        elif outcome == "WICKET_CAUGHT":
            return {
                "concept_title": f"🧤 The Trap Worked: Catch at {primary_f}!",
                "lesson": f"Brilliant tactical setup! When you bowled {line.replace('_', ' ')} with {length.replace('_', ' ')}, the batter was forced to hit in the direction of {primary_f}. Because you positioned your fielder in the exact landing zone, it resulted in an easy catch!",
                "tactical_tip": f"Keep {primary_f} alert. When you tempt a batter into their favorite zone with a catcher waiting, wickets tumble."
            }

        elif outcome == "FOUR":
            return {
                "concept_title": f"🚨 Boundary Gap Exploited: {shot_name}",
                "lesson": f"Why did the batter hit a FOUR? You bowled {line.replace('_', ' ')} ({length.replace('_', ' ')}), but left a massive open pocket in the field! The batter spotted the open space and played a {shot_name} straight through it.",
                "tactical_tip": f"Look at your field: Drag a fielder into the {shot_name.split()[0]} area or bowl closer to the batter's body to deny that shot!"
            }

        elif outcome == "SIX":
            return {
                "concept_title": "💥 Aerial Power over the Boundary",
                "lesson": f"The batter took an aerial gamble with a {shot_name}! Without deep fielders stationed on the boundary rope, lofted shots carry all the way for six runs.",
                "tactical_tip": "If you're going to bowl full or short balls that encourage big hits, make sure you drag boundary riders back to Long-On, Long-Off, or Deep Mid-Wicket."
            }

        elif outcome == "DOT_BALL":
            return {
                "concept_title": f"🛡️ Ring Pressure: Fielded by {primary_f}",
                "lesson": f"Great field placement! The batter played a {shot_name}, but your fielder at {primary_f} was positioned perfectly inside the 30-yard ring to stop the single.",
                "tactical_tip": "Dot balls build immense pressure on the batter, forcing them to take risky shots on the next delivery."
            }

        else:  # Singles / Two runs
            return {
                "concept_title": "🏃 Rotating the Strike",
                "lesson": f"A tidy push into the gap for runs. Your fielders reacted quickly to prevent the boundary, but there was enough space for quick singles.",
                "tactical_tip": "To prevent singles, pull your ring fielders 3 to 5 meters tighter towards the pitch."
            }

