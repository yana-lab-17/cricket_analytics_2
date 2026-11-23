"""
bowling_engine.py
Advanced 3D Ballistics & Atmospheric Physics Engine for Cricket Deliveries.
Simulates aerodynamics, air density, humidity, wind vectors, seam presentation
(upright, wobble, scrambled, reverse swing), pitch degradation conditions
(Day 1 Green, Day 3 Flat, Day 5 Dusty), and 3D bounce dynamics.
"""

import math
from typing import Dict, List, Tuple, Any

class BowlingEngine:
    """Calculates realistic 3D trajectories with aerodynamics, pitch wear and atmospheric drag."""

    def __init__(self, g: float = 9.81):
        self.g = g

    def simulate_delivery(
        self,
        bowling_type: str = "fast",
        speed_kmh: float = 140.0,
        line: str = "outside_off",
        length: str = "good_length",
        variation: str = "outswing",
        pitch_condition: str = "day_3_flat",  # day_1_green, day_3_flat, day_5_dusty
        wind_speed_kmh: float = 0.0,
        wind_direction_deg: float = 0.0,
        humidity_pct: float = 55.0,
        is_lhb: bool = False
    ) -> Dict[str, Any]:
        """
        Simulate full 3D ball trajectory from release to batting crease.
        Factoring in pitch condition, atmospheric drag, seam movement, and spin grip.
        """
        # Convert speeds to m/s
        v_total = max(15.0, min(46.0, speed_kmh / 3.6))
        wind_ms = (wind_speed_kmh / 3.6)
        wind_rad = math.radians(wind_direction_deg)
        wind_vx = wind_ms * math.sin(wind_rad)
        wind_vz = wind_ms * math.cos(wind_rad)

        # Base drag coefficient affected by air density & humidity
        # Higher humidity and dense air slightly increases swing and air resistance
        base_drag = 0.0052 * (1.0 + (humidity_pct - 50.0) * 0.001)

        # Target pitch landing coordinate (z_pitch, x_pitch)
        length_targets = {
            "yorker": 2.2,
            "full": 4.5,
            "good_length": 6.8,
            "back_of_length": 9.2,
            "bouncer": 11.5,
        }
        z_pitch = length_targets.get(length, 6.8)

        line_targets = {
            "wide_outside_off": 0.85,
            "outside_off": 0.50,
            "off_stump": 0.22,
            "middle_stump": 0.00,
            "leg_stump": -0.22,
            "down_leg": -0.65,
        }
        x_target = line_targets.get(line, 0.40)
        if is_lhb:
            x_target = -x_target

        # Bowler release point (Over the wicket)
        is_spinner = "spin" in bowling_type.lower() or "chinaman" in bowling_type.lower()
        release_z = 19.0 if is_spinner else 20.0
        release_y = 2.05 if is_spinner else 2.28
        release_x = 0.55 if not is_lhb else -0.55

        # Flight time to pitch
        dist_z = release_z - z_pitch
        vz_avg = v_total * 0.95
        t_pitch = dist_z / vz_avg

        y_pitch = 0.04
        vy0 = (y_pitch - release_y + 0.5 * self.g * (t_pitch ** 2)) / t_pitch
        vz0 = -dist_z / t_pitch
        vx0 = (x_target - release_x) / t_pitch

        # Aerodynamic Swing / Drift acceleration
        swing_accel = 0.0
        if variation == "outswing":
            swing_accel = 1.75 if not is_lhb else -1.75
        elif variation == "inswing":
            swing_accel = -1.75 if not is_lhb else 1.75
        elif variation == "reverse_swing" and speed_kmh >= 138:
            swing_accel = -2.4 if not is_lhb else 2.4  # Vicious late reverse
        elif is_spinner:
            if "off_spin" in bowling_type or "orthodox" in bowling_type:
                swing_accel = 1.0 if not is_lhb else -1.0  # Drift away in air
            elif "leg_spin" in bowling_type or "chinaman" in bowling_type:
                swing_accel = -1.0 if not is_lhb else 1.0

        # Phase 1: Pre-pitch trajectory
        dt = 0.005
        t = 0.0
        x, y, z = release_x, release_y, release_z
        vx, vy, vz = vx0, vy0, vz0

        trajectory = []
        while z > z_pitch and y > 0.03 and t < 2.5:
            trajectory.append({
                "x": round(float(x), 3),
                "y": round(float(y), 3),
                "z": round(float(z), 3),
                "t": round(float(t), 3)
            })

            # Relative velocity to wind
            rel_vx = vx - wind_vx
            rel_vz = vz - wind_vz
            rel_speed = math.sqrt(rel_vx * rel_vx + vy * vy + rel_vz * rel_vz)
            drag = base_drag * rel_speed

            ax = -drag * rel_vx + swing_accel
            ay = -self.g - drag * vy
            az = -drag * rel_vz

            x += vx * dt
            y += vy * dt
            z += vz * dt
            vx += ax * dt
            vy += ay * dt
            vz += az * dt
            t += dt

        pitch_point = {
            "x": round(float(x), 3),
            "y": 0.04,
            "z": round(float(z), 3),
            "t": round(float(t), 3)
        }
        trajectory.append(pitch_point)

        # ── Pitch Degradation Mechanics ──
        if pitch_condition == "day_1_green":
            cor = 0.64 if not is_spinner else 0.58  # Higher lively bounce
            friction_z = 0.85
            seam_multiplier = 1.6  # High seam nip
            spin_multiplier = 0.7  # Less turn on fresh grass
        elif pitch_condition == "day_5_dusty":
            cor = 0.48 if not is_spinner else 0.42  # Variable, lower bounce
            friction_z = 0.76
            seam_multiplier = 0.8
            spin_multiplier = 2.2  # Massive turn and grip
        else:  # day_3_flat
            cor = 0.57 if not is_spinner else 0.50  # True, consistent bounce
            friction_z = 0.82
            seam_multiplier = 1.0
            spin_multiplier = 1.0

        vy = -vy * cor
        vx *= friction_z
        vz *= friction_z

        # Seam movement or Spin turn off the deck
        deviation = 0.0
        if is_spinner:
            if "off_spin" in bowling_type or "orthodox" in bowling_type:
                deviation = -3.4 * spin_multiplier if not is_lhb else 3.4 * spin_multiplier
            elif "leg_spin" in bowling_type or "chinaman" in bowling_type:
                deviation = 3.8 * spin_multiplier if not is_lhb else -3.8 * spin_multiplier
            if variation == "googly":
                deviation = -deviation
        else:
            if variation in ("outswing", "seam_away"):
                deviation = 1.4 * seam_multiplier if not is_lhb else -1.4 * seam_multiplier
            elif variation in ("inswing", "seam_in"):
                deviation = -1.4 * seam_multiplier if not is_lhb else 1.4 * seam_multiplier

        vx += deviation

        # Phase 2: Post-pitch trajectory until crossing batting crease (z = 0)
        while z > -0.25 and t < 3.2:
            trajectory.append({
                "x": round(float(x), 3),
                "y": round(float(y), 3),
                "z": round(float(z), 3),
                "t": round(float(t), 3)
            })

            speed = math.sqrt(vx * vx + vy * vy + vz * vz)
            drag = base_drag * speed

            ax = -drag * vx
            ay = -self.g - drag * vy
            az = -drag * vz

            x += vx * dt
            y += vy * dt
            z += vz * dt
            vx += ax * dt
            vy += ay * dt
            vz += az * dt
            t += dt

        arrival_point = {
            "x": round(float(x), 3),
            "y": round(float(max(0.04, y)), 3),
            "z": 0.0,
            "t": round(float(t), 3),
            "speed_kmh": round(speed_kmh * friction_z, 1)
        }

        # Stumps check: Height 0.71m, width 0.23m
        is_hitting_stumps = (abs(arrival_point["x"]) <= 0.13) and (0.05 <= arrival_point["y"] <= 0.73)

        return {
            "bowling_type": bowling_type,
            "speed_kmh": speed_kmh,
            "line": line,
            "length": length,
            "variation": variation,
            "pitch_condition": pitch_condition,
            "trajectory": trajectory,
            "pitch_point": pitch_point,
            "arrival_point": arrival_point,
            "hitting_stumps": is_hitting_stumps,
            "flight_duration": round(t, 3)
        }
