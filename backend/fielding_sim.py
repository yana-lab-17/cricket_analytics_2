"""
fielding_sim.py
Dynamic Fielding Pursuit & Match Outcome Engine.
Simulates real-time sprint vectors for all 11 fielders, checks for catches/ground fielding,
and calculates the exact game outcome (Wicket, Four, Six, Dot Ball, Single).
"""

import math
from typing import Dict, List, Tuple, Any

class FieldingSimulationEngine:
    """Calculates fielder chase paths, reaction windows, and ball intercepts."""

    def __init__(self, boundary_radius: float = 68.0):
        self.boundary_radius = boundary_radius

    def simulate_pursuit(
        self,
        shot_info: Dict[str, Any],
        fielders: Dict[str, Dict[str, float]],
        is_bowled: bool = False
    ) -> Dict[str, Any]:
        """
        Simulate all fielders reacting and running towards the ball.
        Returns:
          - outcome: "WICKET_BOWLED", "WICKET_CAUGHT", "FOUR", "SIX", "DOT_BALL", "SINGLE", "TWO_RUNS"
          - outcome_headline: e.g. "OUT! Caught by Cover!"
          - fielder_runs: Dict mapping fielder_name -> [{x, z, t}] animation waypoints
          - primary_fielder: name of the closest fielder
          - catch_attempted: bool
        """
        if is_bowled or shot_info.get("shot_type") == "bowled":
            return {
                "outcome": "WICKET_BOWLED",
                "outcome_headline": "🎯 BOWLED HIM! Clean through the gate!",
                "runs_scored": 0,
                "primary_fielder": "Bowler",
                "catch_attempted": False,
                "fielder_runs": {},
                "intercept_point": {"x": 0.0, "y": 0.2, "z": 0.0, "t": 0.0}
            }

        traj = shot_info.get("trajectory", [])
        if not traj or len(traj) < 2:
            return {
                "outcome": "DOT_BALL",
                "outcome_headline": "Defensively blocked.",
                "runs_scored": 0,
                "primary_fielder": "Bowler",
                "catch_attempted": False,
                "fielder_runs": {},
                "intercept_point": {"x": 0.0, "y": 0.0, "z": 0.0, "t": 0.0}
            }

        # Role-based kinematics: (reaction_delay_s, max_accel_m_s2, max_speed_m_s, dive_reach_m)
        def _get_role_kinematics(name: str):
            if name == "WicketKeeper":
                return 0.18, 5.0, 6.2, 3.2
            elif "Slip" in name or name in ("Gully", "ShortLeg", "SillyPoint"):
                return 0.20, 4.6, 6.4, 3.0
            elif "Deep" in name or name in ("LongOff", "LongOn", "ThirdMan", "FineLeg"):
                return 0.32, 4.4, 8.8, 1.8
            elif name == "Bowler":
                return 0.38, 4.0, 7.5, 1.8
            else:  # Infield ring (Point, Cover, MidOff, MidOn, MidWicket, SquareLeg)
                return 0.26, 4.8, 8.0, 2.2

        intercepted = False
        intercept_time = 999.0
        intercepting_fielder = None
        is_catch = False
        intercept_pt = None

        # Check every point along ball trajectory against each fielder's reach
        for pt in traj:
            bx, by, bz, bt = pt["x"], pt["y"], pt["z"], pt["t"]
            dist_ball_from_origin = math.sqrt(bx * bx + bz * bz)

            # Check if ball already cleared boundary
            if dist_ball_from_origin >= self.boundary_radius:
                break

            for fname, fpos in fielders.items():
                fx, fz = fpos["x"], fpos["z"]
                tau, a_max, v_max, reach = _get_role_kinematics(fname)

                # Distance fielder needs to cover
                f_dist = math.sqrt((fx - bx) ** 2 + (fz - bz) ** 2)

                # Time fielder has been running
                t_run = bt - tau
                if t_run <= 0:
                    continue

                # Max distance fielder could have sprinted in t_run
                t_accel = v_max / a_max
                if t_run <= t_accel:
                    sprint_dist = 0.5 * a_max * (t_run ** 2)
                else:
                    sprint_dist = (0.5 * a_max * (t_accel ** 2)) + v_max * (t_run - t_accel)

                total_reach = sprint_dist + reach

                if f_dist <= total_reach:
                    # Intercepted!
                    intercepted = True
                    intercept_time = bt
                    intercepting_fielder = fname
                    intercept_pt = pt
                    # In the air with realistic catch height (0.2m to 2.4m)
                    if by >= 0.25 and by <= 2.4:
                        is_catch = True
                    break

            if intercepted:
                break

        # Calculate fielder running paths for 3D animation
        fielder_runs = {}
        for fname, fpos in fielders.items():
            fx, fz = fpos["x"], fpos["z"]
            tau, a_max, v_max, _ = _get_role_kinematics(fname)

            # Target is intercept point or closest ball landing point
            target_pt = intercept_pt if intercept_pt else traj[-1]
            tx, tz = target_pt["x"], target_pt["z"]

            # Unit vector towards target
            dx, dz = tx - fx, tz - fz
            dist_to_target = math.sqrt(dx * dx + dz * dz)
            if dist_to_target > 0.1:
                ux, uz = dx / dist_to_target, dz / dist_to_target
            else:
                ux, uz = 0.0, 0.0

            # Path waypoints
            run_pts = [{"x": round(fx, 2), "z": round(fz, 2), "t": 0.0}]
            step_time = 0.1
            cur_t = tau
            while cur_t <= (intercept_time if intercepted else traj[-1]["t"]):
                t_run = cur_t - tau
                t_accel = v_max / a_max
                if t_run <= t_accel:
                    d_run = 0.5 * a_max * (t_run ** 2)
                else:
                    d_run = (0.5 * a_max * (t_accel ** 2)) + v_max * (t_run - t_accel)

                d_run = min(d_run, dist_to_target)
                run_pts.append({
                    "x": round(fx + ux * d_run, 2),
                    "z": round(fz + uz * d_run, 2),
                    "t": round(cur_t, 2)
                })
                cur_t += step_time

            fielder_runs[fname] = run_pts

        # Determine Final Game Outcome
        last_pt = traj[-1]
        dist_last = math.sqrt(last_pt["x"] ** 2 + last_pt["z"] ** 2)

        if intercepted:
            if is_catch:
                outcome = "WICKET_CAUGHT"
                outcome_headline = f"☝️ OUT! Sensational catch by {intercepting_fielder}!"
                runs = 0
            else:
                # Ground interception
                f_dist_from_origin = math.sqrt(intercept_pt["x"] ** 2 + intercept_pt["z"] ** 2)
                if f_dist_from_origin <= 30.0:
                    outcome = "DOT_BALL"
                    outcome_headline = f"🛡️ DOT BALL! Clean fielding by {intercepting_fielder} inside the ring."
                    runs = 0
                elif f_dist_from_origin <= 50.0:
                    outcome = "SINGLE"
                    outcome_headline = f"🏃 1 RUN! Good stop by {intercepting_fielder} in the deep."
                    runs = 1
                else:
                    outcome = "TWO_RUNS"
                    outcome_headline = f"🏃🏃 2 RUNS! Chased down near the rope by {intercepting_fielder}."
                    runs = 2
        else:
            # Ball crossed boundary without fielder interception
            if dist_last >= self.boundary_radius - 1.0:
                if last_pt["y"] > 1.2:
                    outcome = "SIX"
                    outcome_headline = "💥 MASSIVE SIX! Clears the boundary rope into the crowd!"
                    runs = 6
                else:
                    outcome = "FOUR"
                    outcome_headline = "🏏 FOUR! Pierces the field and races across the boundary!"
                    runs = 4
            else:
                outcome = "TWO_RUNS"
                outcome_headline = "Ball plugged in the outfield; batters take 2 runs."
                runs = 2

        return {
            "outcome": outcome,
            "outcome_headline": outcome_headline,
            "runs_scored": runs,
            "primary_fielder": intercepting_fielder or "Deep Fielder",
            "catch_attempted": is_catch,
            "fielder_runs": fielder_runs,
            "intercept_point": intercept_pt
        }

