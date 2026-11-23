"""
trajectory.py
3D Ballistic Trajectory & Physics Engine for Cricket Shot Simulations.

Calculates realistic 3D ball flight paths under gravity and quadratic air resistance:
    m * d^2(r)/dt^2 = m*g - 0.5 * rho * C_d * A * |v| * v
    => a = g - k * |v| * v
where:
    k = drag coefficient per unit mass = 0.5 * rho * C_d * A / m
    theta = launch elevation angle (degrees or radians)
    phi = spray azimuth angle in ground plane X-Z (degrees or radians)
"""

import math
from typing import List, Dict, Tuple, Optional
import numpy as np


class TrajectoryEngine:
    """3D Ballistic Trajectory Calculator with Quadratic Aerodynamic Drag."""

    def __init__(self, g: float = 9.81, default_k: float = 0.006):
        """
        Initialize physics constants.
        :param g: Gravitational acceleration (m/s^2), default 9.81
        :param default_k: Air drag constant (m^-1), default ~0.006 for standard cricket ball
        """
        self.g = g
        self.default_k = default_k

    def calculate_trajectory(
        self,
        v0: float,
        theta: float,
        phi: float,
        k: Optional[float] = None,
        x0: float = 0.0,
        y0: float = 0.7,
        z0: float = 0.0,
        dt: float = 0.005,
        max_time: float = 10.0,
        in_degrees: bool = True,
        spin_rpm: float = 0.0,       # Ball backspin/topspin in RPM
        spin_axis: Tuple[float, float, float] = (1.0, 0.0, 0.0), # Spin axis unit vector
        is_lhb: bool = False         # If true, mirror trajectory laterally for left-handed batter
    ) -> List[Dict[str, float]]:
        """
        Compute the 3D trajectory of a cricket ball off the bat until it lands on the turf.
        Includes quadratic drag and optional Magnus aerodynamic lift from ball spin.
        """
        if k is None:
            k = self.default_k

        # If left-handed batter, mirror spray azimuth across pitch longitudinal axis
        effective_phi = -phi if is_lhb else phi

        # Convert angles to radians if provided in degrees
        rad_theta = math.radians(theta) if in_degrees else theta
        rad_phi = math.radians(effective_phi) if in_degrees else effective_phi

        # Initial velocity vectors
        v_h = v0 * math.cos(rad_theta)
        vx = v_h * math.sin(rad_phi)
        vy = v0 * math.sin(rad_theta)
        vz = v_h * math.cos(rad_phi)

        # Magnus spin angular velocity vector (rad/s)
        omega_mag = (spin_rpm * 2.0 * math.pi) / 60.0
        axis_norm = math.sqrt(sum(a * a for a in spin_axis))
        if axis_norm > 1e-6 and omega_mag > 0:
            omega = tuple((a / axis_norm) * omega_mag for a in spin_axis)
        else:
            omega = (0.0, 0.0, 0.0)

        # Lift coefficient constant for cricket ball Magnus force (C_L ~ 0.00015)
        k_magnus = 0.00015 if omega_mag > 0 else 0.0

        x, y, z = float(x0), float(y0), float(z0)
        t = 0.0

        trajectory = [{
            "x": round(x, 3),
            "y": round(y, 3),
            "z": round(z, 3),
            "t": round(t, 3)
        }]

        def derivatives(state: Tuple[float, float, float, float, float, float]):
            """Computes dx/dt, dy/dt, dz/dt, dvx/dt, dvy/dt, dvz/dt with drag and Magnus force."""
            _, _, _, curr_vx, curr_vy, curr_vz = state
            speed = math.sqrt(curr_vx * curr_vx + curr_vy * curr_vy + curr_vz * curr_vz)
            drag_factor = k * speed

            # Drag acceleration
            ax = -drag_factor * curr_vx
            ay = -self.g - drag_factor * curr_vy
            az = -drag_factor * curr_vz

            # Magnus acceleration: a_magnus = k_magnus * (omega x v)
            if k_magnus > 0:
                mag_x = k_magnus * (omega[1] * curr_vz - omega[2] * curr_vy)
                mag_y = k_magnus * (omega[2] * curr_vx - omega[0] * curr_vz)
                mag_z = k_magnus * (omega[0] * curr_vy - omega[1] * curr_vx)
                ax += mag_x
                ay += mag_y
                az += mag_z

            return curr_vx, curr_vy, curr_vz, ax, ay, az

        # Numerical integration using 4th-order Runge-Kutta (RK4)
        while t < max_time:
            # Current state
            s = (x, y, z, vx, vy, vz)

            # RK4 Stage 1
            k1_vx, k1_vy, k1_vz, k1_ax, k1_ay, k1_az = derivatives(s)

            # RK4 Stage 2
            s_k2 = (
                x + 0.5 * dt * k1_vx,
                y + 0.5 * dt * k1_vy,
                z + 0.5 * dt * k1_vz,
                vx + 0.5 * dt * k1_ax,
                vy + 0.5 * dt * k1_ay,
                vz + 0.5 * dt * k1_az
            )
            k2_vx, k2_vy, k2_vz, k2_ax, k2_ay, k2_az = derivatives(s_k2)

            # RK4 Stage 3
            s_k3 = (
                x + 0.5 * dt * k2_vx,
                y + 0.5 * dt * k2_vy,
                z + 0.5 * dt * k2_vz,
                vx + 0.5 * dt * k2_ax,
                vy + 0.5 * dt * k2_ay,
                vz + 0.5 * dt * k2_az
            )
            k3_vx, k3_vy, k3_vz, k3_ax, k3_ay, k3_az = derivatives(s_k3)

            # RK4 Stage 4
            s_k4 = (
                x + dt * k3_vx,
                y + dt * k3_vy,
                z + dt * k3_vz,
                vx + dt * k3_ax,
                vy + dt * k3_ay,
                vz + dt * k3_az
            )
            k4_vx, k4_vy, k4_vz, k4_ax, k4_ay, k4_az = derivatives(s_k4)

            # Advance state
            next_x = x + (dt / 6.0) * (k1_vx + 2 * k2_vx + 2 * k3_vx + k4_vx)
            next_y = y + (dt / 6.0) * (k1_vy + 2 * k2_vy + 2 * k3_vy + k4_vy)
            next_z = z + (dt / 6.0) * (k1_vz + 2 * k2_vz + 2 * k3_vz + k4_vz)
            next_vx = vx + (dt / 6.0) * (k1_ax + 2 * k2_ax + 2 * k3_ax + k4_ax)
            next_vy = vy + (dt / 6.0) * (k1_ay + 2 * k2_ay + 2 * k3_ay + k4_ay)
            next_vz = vz + (dt / 6.0) * (k1_az + 2 * k2_az + 2 * k3_az + k4_az)
            next_t = t + dt

            # Ground impact check (y <= 0)
            if next_y <= 0.0:
                # Linear interpolation to find precise ground intersection point (y = 0)
                fraction = (0.0 - y) / (next_y - y) if next_y != y else 0.0
                impact_x = x + fraction * (next_x - x)
                impact_z = z + fraction * (next_z - z)
                impact_t = t + fraction * dt

                trajectory.append({
                    "x": round(impact_x, 3),
                    "y": 0.0,
                    "z": round(impact_z, 3),
                    "t": round(impact_t, 3)
                })
                break

            x, y, z = next_x, next_y, next_z
            vx, vy, vz = next_vx, next_vy, next_vz
            t = next_t

            trajectory.append({
                "x": round(x, 3),
                "y": round(y, 3),
                "z": round(z, 3),
                "t": round(t, 3)
            })

        return trajectory

    def calculate_trajectory_array(
        self,
        v0: float,
        theta: float,
        phi: float,
        k: Optional[float] = None,
        x0: float = 0.0,
        y0: float = 0.7,
        z0: float = 0.0,
        dt: float = 0.005
    ) -> np.ndarray:
        """
        Return trajectory as an (N, 4) NumPy array of [X, Y, Z, t].
        """
        traj = self.calculate_trajectory(v0, theta, phi, k, x0, y0, z0, dt)
        arr = np.zeros((len(traj), 4), dtype=np.float64)
        for i, pt in enumerate(traj):
            arr[i, 0] = pt["x"]
            arr[i, 1] = pt["y"]
            arr[i, 2] = pt["z"]
            arr[i, 3] = pt["t"]
        return arr

    def get_shot_metrics(self, trajectory: List[Dict[str, float]]) -> Dict[str, float]:
        """Compute key analytical metrics for a shot trajectory."""
        if not trajectory:
            return {"range": 0.0, "max_height": 0.0, "flight_time": 0.0, "landing_x": 0.0, "landing_z": 0.0}

        max_height = max(p["y"] for p in trajectory)
        landing_pt = trajectory[-1]
        x0 = trajectory[0]["x"]
        z0 = trajectory[0]["z"]
        dx = landing_pt["x"] - x0
        dz = landing_pt["z"] - z0
        ground_distance = math.sqrt(dx * dx + dz * dz)

        return {
            "range": round(ground_distance, 2),
            "max_height": round(max_height, 2),
            "flight_time": round(landing_pt["t"], 2),
            "landing_x": landing_pt["x"],
            "landing_z": landing_pt["z"]
        }


# Standard Cricket Shot Presets
SHOT_PRESETS = {
    "Cover Drive": {"v0": 34.0, "theta": 14.0, "phi": 42.0, "description": "Crisp ground-skimming stroke through extra cover"},
    "Lofted Straight Drive": {"v0": 38.0, "theta": 32.0, "phi": 0.0, "description": "High lofted shot straight over bowler's head"},
    "Square Cut": {"v0": 32.0, "theta": 10.0, "phi": 85.0, "description": "Fast cut behind point toward deep backward point"},
    "Pull Shot": {"v0": 35.0, "theta": 22.0, "phi": -75.0, "description": "Powerful hook/pull in the air towards deep midwicket"},
    "Sweep Shot": {"v0": 26.0, "theta": 8.0, "phi": -120.0, "description": "Spin-countering sweep behind square leg"},
    "Ramp Shot": {"v0": 29.0, "theta": 42.0, "phi": 140.0, "description": "Delicate scoop over wicket-keeper towards third man"},
    "Slog Sweep": {"v0": 40.0, "theta": 36.0, "phi": -50.0, "description": "Massive maximum targeted over deep cow corner"}
}
