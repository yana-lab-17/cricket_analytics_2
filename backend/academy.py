"""
academy.py
Captain's Academy Progression & Challenge Scenarios.
Structured career and training mode guiding children and athletes through progressive
tactical challenges from basic boundary prevention to elite match traps.
"""

from typing import Dict, List, Any

ACADEMY_LEVELS = [
    {
        "id": "level_1",
        "title": "Level 1: The Leaking Bucket",
        "subtitle": "Plug the Cover Gap against Fast Outswing",
        "objective": "Prevent the batter from hitting a boundary through the off-side. Concede 2 runs or less!",
        "target_runs_max": 2,
        "balls_allowed": 3,
        "default_bowling": {
            "bowling_type": "fast",
            "speed_kmh": 142.0,
            "line": "outside_off",
            "length": "full",
            "variation": "outswing"
        },
        "default_field": "Powerplay Attack (Slips + Gully)",
        "hint": "The batter loves driving through cover. Drag your Cover and Extra Cover fielders into the driving corridor!"
    },
    {
        "id": "level_2",
        "title": "Level 2: The Bouncer Trap",
        "subtitle": "Set the Hook & Pull Catching Trap",
        "objective": "Take a WICKET by catching a mistimed pull/hook shot!",
        "target_wickets_min": 1,
        "balls_allowed": 3,
        "default_bowling": {
            "bowling_type": "fast",
            "speed_kmh": 146.0,
            "line": "middle_stump",
            "length": "bouncer",
            "variation": "standard"
        },
        "default_field": "Powerplay Attack (Slips + Gully)",
        "hint": "When bowling bouncers, batters hook into the air! Drag fielders back to Deep Square Leg and Fine Leg!"
    },
    {
        "id": "level_3",
        "title": "Level 3: Spinner's Web",
        "subtitle": "Choke the Batter with Close Catchers",
        "objective": "Bowl 2 consecutive DOT BALLS or take a WICKET using spin!",
        "target_dots_min": 2,
        "balls_allowed": 4,
        "default_bowling": {
            "bowling_type": "off_spin",
            "speed_kmh": 86.0,
            "line": "off_stump",
            "length": "good_length",
            "variation": "standard"
        },
        "default_field": "Spin Trap (Close Catchers + Boundary Traps)",
        "hint": "Spinners need pressure inside the 30-yard circle! Keep Short Leg and Slip close to catch bat-pad deflections."
    },
    {
        "id": "level_4",
        "title": "Level 4: T20 Death Over Defense",
        "subtitle": "Defend the Boundary with Yorkers",
        "objective": "Concede less than 6 runs in 3 balls using pinpoint yorkers!",
        "target_runs_max": 5,
        "balls_allowed": 3,
        "default_bowling": {
            "bowling_type": "fast",
            "speed_kmh": 145.0,
            "line": "middle_stump",
            "length": "yorker",
            "variation": "reverse_swing"
        },
        "default_field": "T20 Death Yorker Lock (5 on Boundary)",
        "hint": "Put all 5 outer boundary fielders on the fence (Deep Cover, Long-Off, Long-On, Deep Mid-Wicket) and nail the yorker!"
    },
    {
        "id": "level_5",
        "title": "Level 5: Grandmaster Captaincy",
        "subtitle": "Complete Tactical Domination",
        "objective": "Take a wicket OR achieve 3 dot balls on a Day 5 dusty turner!",
        "target_dots_min": 3,
        "balls_allowed": 5,
        "default_bowling": {
            "bowling_type": "leg_spin",
            "speed_kmh": 84.0,
            "line": "off_stump",
            "length": "good_length",
            "variation": "googly"
        },
        "default_field": "Spin Trap (Close Catchers + Boundary Traps)",
        "hint": "Use the googly turning into the right-hander while keeping a tight catching ring."
    }
]

class AcademyManager:
    """Tracks player progress across Captain's Academy levels."""

    def __init__(self):
        self.active_level_id = "level_1"
        self.balls_in_level = 0
        self.runs_in_level = 0
        self.wickets_in_level = 0
        self.dots_in_level = 0
        self.completed_levels = set()

    def get_current_level(self) -> Dict[str, Any]:
        for lvl in ACADEMY_LEVELS:
            if lvl["id"] == self.active_level_id:
                return lvl
        return ACADEMY_LEVELS[0]

    def start_level(self, level_id: str) -> Dict[str, Any]:
        for lvl in ACADEMY_LEVELS:
            if lvl["id"] == level_id:
                self.active_level_id = level_id
                self.balls_in_level = 0
                self.runs_in_level = 0
                self.wickets_in_level = 0
                self.dots_in_level = 0
                return lvl
        return ACADEMY_LEVELS[0]

    def record_play(self, outcome: str, runs: int) -> Dict[str, Any]:
        lvl = self.get_current_level()
        self.balls_in_level += 1
        self.runs_in_level += runs
        if "WICKET" in outcome:
            self.wickets_in_level += 1
        if runs == 0:
            self.dots_in_level += 1

        # Check success/failure
        status = "in_progress"
        message = ""

        if lvl["id"] == "level_1":
            if self.runs_in_level > lvl["target_runs_max"]:
                status = "failed"
                message = "Boundary conceded! The gap was exploited."
            elif self.balls_in_level >= lvl["balls_allowed"]:
                status = "passed"
                message = "Level 1 Complete! Excellent field placement."

        elif lvl["id"] == "level_2":
            if self.wickets_in_level >= lvl["target_wickets_min"]:
                status = "passed"
                message = "Level 2 Complete! The bouncer trap was sprung!"
            elif self.balls_in_level >= lvl["balls_allowed"]:
                status = "failed"
                message = "Batters survived the bouncers without giving a catch."

        elif lvl["id"] == "level_3":
            if self.dots_in_level >= lvl["target_dots_min"] or self.wickets_in_level > 0:
                status = "passed"
                message = "Level 3 Complete! Spin choke achieved."
            elif self.balls_in_level >= lvl["balls_allowed"]:
                status = "failed"
                message = "Too many singles were given away."

        elif lvl["id"] == "level_4":
            if self.runs_in_level > lvl["target_runs_max"]:
                status = "failed"
                message = "More than 5 runs conceded in the death overs!"
            elif self.balls_in_level >= lvl["balls_allowed"]:
                status = "passed"
                message = "Level 4 Complete! Death overs locked down."

        elif lvl["id"] == "level_5":
            if self.wickets_in_level > 0 or self.dots_in_level >= lvl["target_dots_min"]:
                status = "passed"
                message = "Level 5 Complete! You are a Grandmaster Captain!"
            elif self.balls_in_level >= lvl["balls_allowed"]:
                status = "failed"
                message = "Challenge incomplete; try again."

        if status == "passed":
            self.completed_levels.add(lvl["id"])

        return {
            "level_id": lvl["id"],
            "status": status,
            "message": message,
            "balls_played": self.balls_in_level,
            "balls_max": lvl["balls_allowed"],
            "runs": self.runs_in_level,
            "wickets": self.wickets_in_level,
            "dots": self.dots_in_level,
            "completed_levels": list(self.completed_levels)
        }

