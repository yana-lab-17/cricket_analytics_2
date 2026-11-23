"""
batter_ai.py
Reactive Batter AI with Bat-Ball Collision Physics & Cognitive Latency Modeling.
Simulates bat sweet-spot physics, edge deflections, check-swings, gap-seeking
spatial intelligence, and authentic human reaction errors.
"""

import math
from typing import Dict, List, Tuple, Any

class BatterAI:
    """Intelligent Batter that reacts dynamically to ballistics, pitch wear, and field placement."""

    def __init__(self, g: float = 9.81, air_drag: float = 0.005):
        self.g = g
        self.k = air_drag

    def evaluate_and_play_shot(
        self,
        delivery_info: Dict[str, Any],
        fielders: Dict[str, Dict[str, float]],
        is_lhb: bool = False
    ) -> Dict[str, Any]:
        """
        Evaluate bowling delivery + field gaps and calculate the shot.
        Incorporates bat sweet spot vs edge collision mechanics.
        """
        line = delivery_info.get("line", "outside_off")
        length = delivery_info.get("length", "good_length")
        speed_kmh = delivery_info.get("speed_kmh", 140.0)
        variation = delivery_info.get("variation", "outswing")
        hitting_stumps = delivery_info.get("hitting_stumps", False)
        pitch_cond = delivery_info.get("pitch_condition", "day_3_flat")
        arr = delivery_info.get("arrival_point", {"x": 0.4, "y": 0.7, "z": 0.0})

        arr_x = arr.get("x", 0.4)
        arr_y = arr.get("y", 0.7)

        # ── 1. Determine Candidate Shots Based on Line, Length & Pitch Condition ──
        candidate_shots = []

        if length == "yorker":
            if hitting_stumps and speed_kmh >= 138 and variation in ("reverse_swing", "inswing"):
                candidate_shots.append({
                    "name": "Clean Bowled / Beaten for Pace",
                    "type": "bowled",
                    "contact_zone": "miss",
                    "phi": 0.0, "theta": 0.0, "v0": 0.0,
                    "desc": "Lethal yorker beats the inside edge and shatters off-stump!"
                })
            else:
                candidate_shots.append({
                    "name": "Defensive Dig-Out to Point",
                    "type": "ground",
                    "contact_zone": "toe",
                    "phi": 58.0 if not is_lhb else -58.0, "theta": 1.2, "v0": 17.0,
                    "desc": "Jams the bat toe-end down in the nick of time."
                })
                candidate_shots.append({
                    "name": "Squirted past Mid-On",
                    "type": "ground",
                    "contact_zone": "inner_half",
                    "phi": -24.0 if not is_lhb else 24.0, "theta": 1.2, "v0": 15.0,
                    "desc": "Defensively squeezed past the bowler towards mid-on."
                })

        elif length == "full":
            if "off" in line or arr_x > 0.15:
                candidate_shots.append({
                    "name": "Cover Drive",
                    "type": "drive",
                    "contact_zone": "sweet_spot",
                    "phi": 48.0 if not is_lhb else -48.0, "theta": 3.8, "v0": 36.0,
                    "desc": "High elbow classical cover drive right out of the middle of the bat."
                })
                candidate_shots.append({
                    "name": "Square Drive through Point",
                    "type": "drive",
                    "contact_zone": "sweet_spot",
                    "phi": 72.0 if not is_lhb else -72.0, "theta": 3.0, "v0": 34.0,
                    "desc": "Crisp punch piercing the cover-point pocket."
                })
                candidate_shots.append({
                    "name": "Lofted Extra Cover Drive",
                    "type": "lofted",
                    "contact_zone": "sweet_spot",
                    "phi": 38.0 if not is_lhb else -38.0, "theta": 24.0, "v0": 39.0,
                    "desc": "Aerial inside-out loft sailing over the 30-yard ring."
                })
                # Edge probability if moving away
                if variation in ("outswing", "seam_away", "leg_spin"):
                    candidate_shots.append({
                        "name": "Thick Outside Edge to Slips",
                        "type": "edge",
                        "contact_zone": "outside_edge",
                        "phi": 118.0 if not is_lhb else -118.0, "theta": 12.0, "v0": 30.0,
                        "desc": "Drives away from the body; thick outside edge flies toward the slip cordon!"
                    })
            else:
                candidate_shots.append({
                    "name": "Straight Drive",
                    "type": "drive",
                    "contact_zone": "sweet_spot",
                    "phi": 6.0 if not is_lhb else -6.0, "theta": 3.0, "v0": 37.0,
                    "desc": "Pure textbook straight drive back past the bowler's stumps."
                })
                candidate_shots.append({
                    "name": "On Drive",
                    "type": "drive",
                    "contact_zone": "sweet_spot",
                    "phi": -22.0 if not is_lhb else 22.0, "theta": 3.5, "v0": 34.0,
                    "desc": "Leaning into the on-drive towards long-on."
                })
                candidate_shots.append({
                    "name": "Flick off the Pads",
                    "type": "drive",
                    "contact_zone": "sweet_spot",
                    "phi": -56.0 if not is_lhb else 56.0, "theta": 6.0, "v0": 32.0,
                    "desc": "Wristy whip off the pads into the mid-wicket gap."
                })

        elif length in ("good_length", "back_of_length"):
            if "off" in line or arr_x > 0.15:
                candidate_shots.append({
                    "name": "Backfoot Punch to Cover",
                    "type": "drive",
                    "contact_zone": "sweet_spot",
                    "phi": 44.0 if not is_lhb else -44.0, "theta": 3.0, "v0": 30.0,
                    "desc": "Rises on toes and punches through the cover gap."
                })
                candidate_shots.append({
                    "name": "Square Cut",
                    "type": "cut",
                    "contact_zone": "sweet_spot",
                    "phi": 84.0 if not is_lhb else -84.0, "theta": 4.0, "v0": 34.0,
                    "desc": "Sharp square cut rolling the wrists behind point."
                })
                if variation in ("outswing", "seam_away") or pitch_cond == "day_1_green":
                    candidate_shots.append({
                        "name": "Nick to Cordon",
                        "type": "edge",
                        "contact_zone": "outside_edge",
                        "phi": 126.0 if not is_lhb else -126.0, "theta": 10.0, "v0": 28.0,
                        "desc": "Seam deviates away late; faint outside edge to slips/gully."
                    })
            else:
                candidate_shots.append({
                    "name": "Mid-Wicket Glance",
                    "type": "glance",
                    "contact_zone": "sweet_spot",
                    "phi": -42.0 if not is_lhb else 42.0, "theta": 3.0, "v0": 26.0,
                    "desc": "Worked softly off the hip into the mid-wicket pocket."
                })
                candidate_shots.append({
                    "name": "Fine Leg Glance",
                    "type": "glance",
                    "contact_zone": "sweet_spot",
                    "phi": -132.0 if not is_lhb else 132.0, "theta": 2.0, "v0": 25.0,
                    "desc": "Neat deflection past the keeper down to fine leg."
                })

        else:  # Bouncer / Short-pitched
            if "off" in line or arr_x > 0.2:
                candidate_shots.append({
                    "name": "Upper Cut over Cordon",
                    "type": "lofted",
                    "contact_zone": "sweet_spot",
                    "phi": 116.0 if not is_lhb else -116.0, "theta": 28.0, "v0": 36.0,
                    "desc": "Uses the bowler's steep bounce to glide over slips."
                })
                candidate_shots.append({
                    "name": "Backfoot Slash over Point",
                    "type": "cut",
                    "contact_zone": "sweet_spot",
                    "phi": 78.0 if not is_lhb else -78.0, "theta": 14.0, "v0": 34.0,
                    "desc": "Explosive backfoot slash over the point fielder."
                })
            else:
                candidate_shots.append({
                    "name": "Violent Pull Shot",
                    "type": "pull",
                    "contact_zone": "sweet_spot",
                    "phi": -76.0 if not is_lhb else 76.0, "theta": 12.0, "v0": 41.0,
                    "desc": "Swivels into a flat, ferocious pull toward deep mid-wicket."
                })
                candidate_shots.append({
                    "name": "Hook Shot into Stands",
                    "type": "hook",
                    "contact_zone": "sweet_spot",
                    "phi": -120.0 if not is_lhb else 120.0, "theta": 32.0, "v0": 43.0,
                    "desc": "Hooks high and handsome into the fine leg boundary crowd!"
                })

        if not candidate_shots:
            candidate_shots.append({
                "name": "Forward Defensive Push",
                "type": "ground",
                "contact_zone": "middle",
                "phi": 22.0, "theta": 1.0, "v0": 14.0,
                "desc": "Solid defensive block into the covers."
            })

        # ── 2. Scan User Fielders & Select Shot Exploiting the Largest Gap ──
        best_shot = None
        max_gap_score = -999.0

        for shot in candidate_shots:
            if shot["type"] == "bowled":
                gap_score = 0.0
            else:
                phi_rad = math.radians(shot["phi"])
                min_dist_to_line = 999.0
                for fname, fpos in fielders.items():
                    fx, fz = fpos["x"], fpos["z"]
                    f_dist = math.sqrt(fx * fx + fz * fz)
                    if f_dist < 1.0:
                        continue
                    f_phi = math.atan2(fx, fz)
                    angle_diff = abs(f_phi - phi_rad)
                    while angle_diff > math.pi:
                        angle_diff -= 2 * math.pi
                    angle_diff = abs(angle_diff)

                    lateral_dist = f_dist * math.sin(angle_diff)
                    if angle_diff < math.radians(45):
                        if lateral_dist < min_dist_to_line:
                            min_dist_to_line = lateral_dist

                gap_score = min_dist_to_line

                # Edge bonus if swinging away
                if shot["type"] == "edge" and variation in ("outswing", "seam_away"):
                    gap_score += 9.0

            if gap_score > max_gap_score:
                max_gap_score = gap_score
                best_shot = shot

        if best_shot is None:
            best_shot = candidate_shots[0]

        # ── 3. Calculate Full 3D Ballistic Trajectory of the Shot ──
        shot_traj = []
        if best_shot["type"] == "bowled":
            shot_traj = [{
                "x": round(float(arr_x), 3),
                "y": round(float(arr_y), 3),
                "z": 0.0,
                "t": 0.0
            }, {
                "x": round(float(arr_x * 1.1), 3),
                "y": 0.1,
                "z": -0.85,
                "t": 0.08
            }]
        else:
            phi_rad = math.radians(best_shot["phi"])
            theta_rad = math.radians(best_shot["theta"])
            v0 = best_shot["v0"]

            vx = v0 * math.cos(theta_rad) * math.sin(phi_rad)
            vy = v0 * math.sin(theta_rad)
            vz = v0 * math.cos(theta_rad) * math.cos(phi_rad)

            dt = 0.015
            t = 0.0
            x, y, z = 0.0, max(0.5, arr_y), 0.0

            while math.sqrt(x * x + z * z) < 70.0 and t < 6.0:
                shot_traj.append({
                    "x": round(float(x), 2),
                    "y": round(float(max(0.04, y)), 2),
                    "z": round(float(z), 2),
                    "t": round(float(t), 2)
                })

                speed = math.sqrt(vx * vx + vy * vy + vz * vz)
                drag = self.k * speed

                ax = -drag * vx
                ay = -self.g - drag * vy
                az = -drag * vz

                x += vx * dt
                y += vy * dt
                z += vz * dt
                vx += ax * dt
                vy += ay * dt
                vz += az * dt

                # Turf bounce and rolling friction
                if y <= 0.04:
                    y = 0.04
                    if vy < -1.5:
                        vy = -vy * 0.44  # turf restitution
                        vx *= 0.78
                        vz *= 0.78
                    else:
                        vy = 0.0
                        friction = 3.2
                        h_speed = math.sqrt(vx * vx + vz * vz)
                        if h_speed > 0.1:
                            vx -= (vx / h_speed) * friction * dt
                            vz -= (vz / h_speed) * friction * dt
                        else:
                            break

                t += dt

        return {
            "shot_name": best_shot["name"],
            "shot_type": best_shot["type"],
            "contact_zone": best_shot.get("contact_zone", "sweet_spot"),
            "shot_description": best_shot["desc"],
            "launch_angle": best_shot["theta"],
            "spray_azimuth": best_shot["phi"],
            "exit_velocity_kmh": round(best_shot["v0"] * 3.6, 1),
            "trajectory": shot_traj,
            "flight_duration": round(shot_traj[-1]["t"] if shot_traj else 0.0, 2)
        }
