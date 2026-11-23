"""
analytics.py
Spatial Analytics Engine for Cricket Fielding:
- Voronoi Tessellation (Scipy Spatial)
- Field Coverage Score (FC_s) Calculation via Reaction Radii
- Infield / Outfield Spatial Partitioning
- ICC Fielding Restriction Validator & Auto-Corrector
"""

import math
from typing import Dict, List, Tuple, Any
import numpy as np
from scipy.spatial import Voronoi, cKDTree


class FieldAnalytics:
    """Spatial geometry and coverage calculator for cricket fielding configurations."""

    def __init__(
        self,
        reaction_radius: float = 10.0,
        infield_radius: float = 27.43,   # 30 yards
        boundary_radius: float = 68.0,   # Standard cricket boundary
        grid_resolution: float = 0.4     # High-precision numerical grid spacing (meters)
    ):
        self.reaction_radius = reaction_radius
        self.infield_radius = infield_radius
        self.boundary_radius = boundary_radius
        self.grid_res = grid_resolution

    def compute_voronoi(self, fielders: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """
        Compute 2D Voronoi diagram for fielder coordinates (X, Z).
        Returns bounded ridge segments and per-fielder cells suitable for 3D rendering.

        :param fielders: Dict mapping fielder names to {'x': float, 'y': float, 'z': float}
        :return: Dict containing ridges, vertices, and fielder cell metadata
        """
        names = list(fielders.keys())
        points = np.array([[fielders[n]["x"], fielders[n]["z"]] for n in names], dtype=np.float64)

        if len(points) < 4:
            return {"ridges": [], "cells": {}, "vertices": []}

        vor = Voronoi(points)
        center = points.mean(axis=0)

        # Extract finite and semi-infinite ridges bounded by field radius
        ridge_segments = []
        for (p1, p2), (v1, v2) in zip(vor.ridge_points, vor.ridge_vertices):
            fielder1_name = names[p1]
            fielder2_name = names[p2]

            if v1 >= 0 and v2 >= 0:
                # Finite ridge segment
                start_pt = vor.vertices[v1]
                end_pt = vor.vertices[v2]
                ridge_segments.append({
                    "start": {"x": round(float(start_pt[0]), 2), "z": round(float(start_pt[1]), 2)},
                    "end": {"x": round(float(end_pt[0]), 2), "z": round(float(end_pt[1]), 2)},
                    "fielders": [fielder1_name, fielder2_name],
                    "is_boundary": False
                })
            else:
                # Semi-infinite ridge: extend ray towards boundary
                finite_v = v1 if v1 >= 0 else v2
                if finite_v < 0:
                    continue
                start_pt = vor.vertices[finite_v]

                # Perpendicular direction to the line between p1 and p2
                midpoint = (points[p1] + points[p2]) / 2.0
                direction = np.array([-(points[p2][1] - points[p1][1]), points[p2][0] - points[p1][0]])
                
                # Orient direction outwards from center
                if np.dot(direction, start_pt - center) < 0:
                    direction = -direction

                norm = np.linalg.norm(direction)
                if norm > 1e-6:
                    direction = direction / norm
                    # Extend to outer boundary
                    end_pt = start_pt + direction * 40.0
                    ridge_segments.append({
                        "start": {"x": round(float(start_pt[0]), 2), "z": round(float(start_pt[1]), 2)},
                        "end": {"x": round(float(end_pt[0]), 2), "z": round(float(end_pt[1]), 2)},
                        "fielders": [fielder1_name, fielder2_name],
                        "is_boundary": True
                    })

        # Voronoi cell vertex indices and area calculations for each fielder
        cells = {}
        for idx, name in enumerate(names):
            region_idx = vor.point_region[idx]
            region = vor.regions[region_idx]
            cell_verts = []
            cell_area = 0.0

            if -1 not in region and len(region) >= 3:
                for v_idx in region:
                    v = vor.vertices[v_idx]
                    cell_verts.append({"x": round(float(v[0]), 2), "z": round(float(v[1]), 2)})
                
                # Shoelace formula for polygon area
                n_v = len(cell_verts)
                area_sum = 0.0
                for vi in range(n_v):
                    v_curr = cell_verts[vi]
                    v_next = cell_verts[(vi + 1) % n_v]
                    area_sum += (v_curr["x"] * v_next["z"]) - (v_next["x"] * v_curr["z"])
                cell_area = abs(area_sum) * 0.5
            else:
                # Unbounded cell approximation based on distance to nearest neighbor
                cell_area = 1250.0  # Estimated boundary sector

            # Vulnerability level based on territorial area
            # Ideal average territory on a 68m boundary cricket ground is ~1320 m^2
            if cell_area < 450.0:
                vuln_tier = "fortified"      # High defensive concentration
                vuln_color = "rgba(34, 197, 94, 0.25)"   # Soft green
            elif cell_area < 950.0:
                vuln_tier = "balanced"       # Optimal coverage
                vuln_color = "rgba(56, 189, 248, 0.22)"  # Cyan
            elif cell_area < 1600.0:
                vuln_tier = "stretched"      # Broad territory to cover
                vuln_color = "rgba(245, 158, 11, 0.22)"  # Amber
            else:
                vuln_tier = "critical_gap"   # Large open zone, easy boundary target
                vuln_color = "rgba(239, 68, 68, 0.28)"   # Red

            cells[name] = {
                "position": {"x": round(float(points[idx, 0]), 2), "z": round(float(points[idx, 1]), 2)},
                "polygon": cell_verts,
                "area_m2": round(float(cell_area), 1),
                "vulnerability_tier": vuln_tier,
                "shading_color": vuln_color
            }

        return {
            "ridges": ridge_segments,
            "cells": cells,
            "vertices": [{"x": round(float(v[0]), 2), "z": round(float(v[1]), 2)} for v in vor.vertices]
        }

    def calculate_field_coverage(
        self,
        fielders: Dict[str, Dict[str, float]],
        reaction_radius: float = None
    ) -> Dict[str, Any]:
        """
        Calculate Field Coverage Score (FC_s) as the percentage of the total
        playable field area (boundary circle) patrolled by at least one fielder
        within their reaction radius r.

        Score = (union of fielder disks ∩ field circle) / total field area × 100

        This gives a meaningful score that visibly changes as fielders are spread
        across different zones vs. clustered together.
        """
        r = reaction_radius if reaction_radius is not None else self.reaction_radius
        names = list(fielders.keys())
        n_fielders = len(names)

        if n_fielders == 0:
            return {
                "coverage_score": 0.0,
                "total_area_covered_m2": 0.0,
                "infield_covered_pct": 0.0,
                "outfield_covered_m2": 0.0,
                "field_area_m2": 0.0,
                "overlap_ratio": 0.0
            }

        coords = np.array([[fielders[n]["x"], fielders[n]["z"]] for n in names], dtype=np.float64)
        cell_area = self.grid_res * self.grid_res

        # Build a grid covering the full boundary circle
        R = self.boundary_radius
        xs = np.arange(-R, R + self.grid_res, self.grid_res)
        zs = np.arange(-R, R + self.grid_res, self.grid_res)
        grid_x, grid_z = np.meshgrid(xs, zs)
        grid_points = np.column_stack([grid_x.ravel(), grid_z.ravel()])

        # Restrict to points inside the boundary circle (the playable field)
        dist_from_centre = np.sqrt(grid_points[:, 0]**2 + grid_points[:, 1]**2)
        field_mask = dist_from_centre <= R
        field_points = grid_points[field_mask]
        total_field_points = len(field_points)
        total_field_area = total_field_points * cell_area  # ≈ π × R²

        # Find grid points within reaction radius of ANY fielder (union of disks)
        tree = cKDTree(coords)
        dists, _ = tree.query(field_points)
        covered_mask = dists <= r

        total_covered_points = np.count_nonzero(covered_mask)
        total_covered_area = total_covered_points * cell_area

        # Coverage score = fraction of field patrolled
        coverage_score = (total_covered_area / total_field_area * 100.0) if total_field_area > 0 else 0.0
        coverage_score = min(100.0, max(0.0, coverage_score))

        # Infield breakdown (30-yard circle)
        dist_from_origin = np.sqrt(field_points[:, 0]**2 + field_points[:, 1]**2)
        infield_mask = dist_from_origin <= self.infield_radius
        total_infield_points = np.count_nonzero(infield_mask)
        covered_infield_points = np.count_nonzero(covered_mask & infield_mask)
        infield_covered_pct = (
            (covered_infield_points / total_infield_points * 100.0)
            if total_infield_points > 0 else 0.0
        )

        # Outfield breakdown
        outfield_covered_points = np.count_nonzero(covered_mask & ~infield_mask)
        outfield_covered_area = outfield_covered_points * cell_area

        # Overlap ratio: how much of each disk overlaps another (wasted coverage)
        single_disk_area = math.pi * (r ** 2)
        max_possible_area = n_fielders * single_disk_area
        overlap_area = max(0.0, max_possible_area - total_covered_area)
        overlap_ratio = max(0.0, overlap_area / max_possible_area) if max_possible_area > 0 else 0.0

        return {
            "coverage_score": float(round(coverage_score, 1)),
            "total_area_covered_m2": float(round(total_covered_area, 1)),
            "infield_covered_pct": float(round(infield_covered_pct, 1)),
            "outfield_covered_m2": float(round(outfield_covered_area, 1)),
            "field_area_m2": float(round(total_field_area, 1)),
            "overlap_ratio": float(round(overlap_ratio, 3))
        }

    def calculate_apollonius_pursuit(
        self,
        landing_x: float,
        landing_z: float,
        flight_time: float,
        fielders: Dict[str, Dict[str, float]],
        tau_react: float = 0.35,     # Default visual-motor reaction time latency (seconds)
        a_max: float = 4.2,          # Default max sprint acceleration (m/s^2)
        v_max: float = 8.2           # Default peak sprint speed (m/s) ~ 29.5 km/h
    ) -> Dict[str, Any]:
        """
        Calculates realistic kinematic pursuit dynamics and Apollonius reach envelopes
        for all 11 fielders contesting a cricket shot, incorporating role-based kinematics:
        - Wicket-keeper: fast reflex (0.18s), explosive lateral dive, small patrol radius.
        - Close catching (Slips/Gully/Short Leg): reflex catchers (0.20s), reach 3.0m.
        - Inner ring (Point/Cover/Mid-Wicket): explosive acceleration (4.8 m/s²) to save singles.
        - Boundary sweepers: high top speed (8.8 m/s) with larger patrol envelopes.
        - Bowler: follow-through reaction latency (0.40s).
        """
        landing_pt = np.array([landing_x, landing_z], dtype=np.float64)

        def _get_kinematics(f_name: str):
            if f_name == "WicketKeeper":
                return 0.18, 4.8, 6.0, 3.5
            elif any(k in f_name for k in ["Slip", "Gully", "ShortLeg", "SillyPoint", "LegSlip"]):
                return 0.20, 4.5, 6.2, 3.0
            elif f_name == "Bowler":
                return 0.40, 3.8, 7.5, 6.5
            elif any(k in f_name for k in ["Deep", "LongOff", "LongOn", "FineLeg", "ThirdMan"]):
                return 0.35, 4.2, 8.8, 12.0
            else:  # Infield ring: Point, Cover, ExtraCover, MidOff, MidOn, MidWicket, SquareLeg, etc.
                return 0.28, 4.8, 8.0, 9.5

        fielder_pursuits = []

        for name, pos in fielders.items():
            f_pt = np.array([pos["x"], pos["z"]], dtype=np.float64)
            dist = float(np.linalg.norm(f_pt - landing_pt))

            f_tau, f_a, f_v, f_r = _get_kinematics(name)

            t_accel = f_v / f_a if f_a > 0 else 0.0
            d_accel = 0.5 * f_a * (t_accel ** 2)

            eff_ft = max(0.0, flight_time - f_tau)
            if eff_ft <= 0:
                apollonius_radius = 0.0
            elif eff_ft <= t_accel:
                apollonius_radius = 0.5 * f_a * (eff_ft ** 2)
            else:
                apollonius_radius = d_accel + f_v * (eff_ft - t_accel)

            # Time to cover distance
            if dist <= f_r:
                # Immediate diving reaction
                t_sprint = (dist / (f_v * 0.9)) if f_v > 0 else 0.0
                t_total = f_tau * 0.5 + t_sprint
            elif dist <= d_accel:
                t_sprint = math.sqrt((2.0 * dist) / f_a) if f_a > 0 else 999.0
                t_total = f_tau + t_sprint
            else:
                t_sprint = t_accel + ((dist - d_accel) / f_v)
                t_total = f_tau + t_sprint

            time_margin = flight_time - t_total  # Positive = reaches before ball lands

            # Catch probability model via logistic sigmoid
            prob_catch = 1.0 / (1.0 + math.exp(-3.5 * time_margin))
            prob_catch = min(0.98, max(0.01, prob_catch))

            # Direction vector
            dir_vec = landing_pt - f_pt
            dir_norm = np.linalg.norm(dir_vec)
            unit_dir = (dir_vec / dir_norm) if dir_norm > 1e-6 else np.array([0.0, 0.0])

            fielder_pursuits.append({
                "name": name,
                "start_pos": {"x": round(float(f_pt[0]), 2), "z": round(float(f_pt[1]), 2)},
                "distance_to_ball_m": round(dist, 2),
                "time_to_reach_s": round(t_total, 2),
                "time_margin_s": round(time_margin, 2),
                "can_intercept": (dist <= apollonius_radius) or (time_margin >= 0.0),
                "catch_probability_pct": round(prob_catch * 100.0, 1),
                "sprint_vector": {
                    "dx": round(float(unit_dir[0]), 3),
                    "dz": round(float(unit_dir[1]), 3)
                },
                "apollonius_reach_m": round(apollonius_radius, 2)
            })

        # Sort fielders by distance to landing
        fielder_pursuits.sort(key=lambda item: item["distance_to_ball_m"])

        primary_fielder = fielder_pursuits[0] if fielder_pursuits else None
        secondary_fielder = fielder_pursuits[1] if len(fielder_pursuits) > 1 else None

        # Determine tactical outcome
        if primary_fielder:
            if primary_fielder["can_intercept"] and primary_fielder["time_margin_s"] >= 0.15:
                outcome = "Catch / Intercept Probable"
                outcome_status = "safe"
            elif primary_fielder["can_intercept"]:
                outcome = "Contested 50-50 Catch Opportunity"
                outcome_status = "contested"
            elif primary_fielder["distance_to_ball_m"] <= primary_fielder["apollonius_reach_m"] + 6.0:
                outcome = "Fielded on Bounce (Single / Two)"
                outcome_status = "controlled"
            else:
                outcome = "Defensive Gap Penetrated (Boundary 4/6)"
                outcome_status = "breached"
        else:
            outcome = "Uncontested"
            outcome_status = "breached"

        max_reach = max((f["apollonius_reach_m"] for f in fielder_pursuits), default=0.0)

        return {
            "primary_fielder": primary_fielder["name"] if primary_fielder else None,
            "secondary_backer": secondary_fielder["name"] if secondary_fielder else None,
            "primary_metrics": primary_fielder,
            "secondary_metrics": secondary_fielder,
            "all_pursuits": fielder_pursuits,
            "apollonius_reach_m": round(max_reach, 2),
            "tactical_outcome": outcome,
            "outcome_status": outcome_status
        }

    def assess_shot_intercept(
        self,
        landing_x: float,
        landing_z: float,
        flight_time: float,
        fielders: Dict[str, Dict[str, float]],
        fielder_sprint_speed: float = 8.0
    ) -> Dict[str, Any]:
        """Backward-compatible wrapper redirecting to full Apollonius kinematics."""
        pursuit = self.calculate_apollonius_pursuit(
            landing_x=landing_x,
            landing_z=landing_z,
            flight_time=flight_time,
            fielders=fielders
        )
        prim = pursuit.get("primary_metrics", {})
        return {
            "closest_fielder": pursuit.get("primary_fielder"),
            "secondary_backer": pursuit.get("secondary_backer"),
            "distance_m": prim.get("distance_to_ball_m", 0.0),
            "time_to_reach_s": prim.get("time_to_reach_s", 0.0),
            "time_margin_s": prim.get("time_margin_s", 0.0),
            "intercept_possible": prim.get("can_intercept", False),
            "catch_probability_pct": prim.get("catch_probability_pct", 0.0),
            "apollonius_reach_m": pursuit.get("apollonius_reach_m", 0.0),
            "tactical_outcome": pursuit.get("tactical_outcome"),
            "outcome_status": pursuit.get("outcome_status")
        }

    @staticmethod
    def mirror_field_for_lhb(fielders: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
        """
        Mirror fielding setup laterally across the pitch axis (X -> -X)
        for a Left-Handed Batter (LHB), maintaining 11 unique fielder identities
        and ensuring smooth WebGL spatial interpolation without dictionary collisions.
        """
        mirrored = {}
        for name, pos in fielders.items():
            mirrored[name] = {
                "x": float(round(-pos["x"], 2)),
                "y": float(pos.get("y", 1.0)),
                "z": float(pos["z"])
            }
        return mirrored


# ─────────────────────────────────────────────────────────────────────────────
# ICC FIELDING RESTRICTION RULES  (inline — mirrors cricket_knowledge.py but
# kept here so analytics stays self-contained for the validator)
# ─────────────────────────────────────────────────────────────────────────────
_ICC_RULES = {
    "T20": [
        {"label": "Powerplay",     "overs": (1,  6),  "min_outside": 0, "max_outside": 2},
        {"label": "Middle Overs",  "overs": (7,  15), "min_outside": 0, "max_outside": 5},
        {"label": "Death Overs",   "overs": (16, 20), "min_outside": 0, "max_outside": 5},
    ],
    "ODI": [
        {"label": "Powerplay",     "overs": (1,  10), "min_outside": 0, "max_outside": 2},
        {"label": "Middle Overs",  "overs": (11, 40), "min_outside": 0, "max_outside": 4},
        {"label": "Death Overs",   "overs": (41, 50), "min_outside": 0, "max_outside": 5},
    ],
    "Test": [
        {"label": "All",           "overs": (1, 999), "min_outside": 0, "max_outside": 11},
    ],
}

# Positions that are never counted against outside-circle limits regardless of
# coordinates (they serve a structural role inside the arc by convention).
_ALWAYS_INSIDE = {"WicketKeeper", "Bowler"}


class FieldComplianceEngine:
    """
    Validates and auto-corrects a fielding configuration against ICC powerplay
    fielding restriction rules.

    The 30-yard (27.43 m) circle is the dividing line: any fielder whose
    distance from the pitch centre exceeds infield_radius is counted as
    'outside the circle'.
    """

    def __init__(self, infield_radius: float = 27.43):
        self.infield_radius = infield_radius

    # ── Public API ─────────────────────────────────────────────────────────

    def get_phase_rule(self, match_format: str, current_over: int) -> Dict[str, Any]:
        """Return the ICC rule dict that applies for the given format + over."""
        rules = _ICC_RULES.get(match_format, _ICC_RULES["T20"])
        for rule in rules:
            lo, hi = rule["overs"]
            if lo <= current_over <= hi:
                return rule
        return rules[-1]  # fallback to last phase

    def classify_fielders(
        self, fielders: Dict[str, Dict[str, float]]
    ) -> Dict[str, Any]:
        """
        Split fielders into inside/outside the 30-yard circle.
        Returns classification dict with counts and per-fielder details.
        """
        inside = {}
        outside = {}

        for name, pos in fielders.items():
            dist = math.sqrt(pos["x"] ** 2 + pos["z"] ** 2)
            is_inside = (dist <= self.infield_radius) or (name in _ALWAYS_INSIDE)
            entry = {
                "name": name,
                "x": pos["x"],
                "z": pos["z"],
                "dist_from_centre": round(dist, 1),
                "in_circle": is_inside,
            }
            if is_inside:
                inside[name] = entry
            else:
                outside[name] = entry

        return {
            "inside": inside,
            "outside": outside,
            "inside_count": len(inside),
            "outside_count": len(outside),
        }

    def validate(
        self,
        fielders: Dict[str, Dict[str, float]],
        match_format: str,
        current_over: int,
    ) -> Dict[str, Any]:
        """
        Check the field against ICC rules for the current phase.

        Returns:
          valid          : bool
          violations     : list of human-readable violation strings
          rule           : the ICC rule that was applied
          classification : inside/outside breakdown
          outside_count  : int
          max_outside    : int
        """
        rule = self.get_phase_rule(match_format, current_over)
        clf = self.classify_fielders(fielders)
        n_out = clf["outside_count"]
        max_out = rule["max_outside"]
        min_out = rule["min_outside"]

        violations = []
        if n_out > max_out:
            violations.append(
                f"{n_out} fielder(s) outside the 30-yard circle but the "
                f"{rule['label']} limit is {max_out}. "
                f"Move {n_out - max_out} fielder(s) inside."
            )
        if n_out < min_out:
            violations.append(
                f"Only {n_out} fielder(s) outside the 30-yard circle but "
                f"{rule['label']} requires at least {min_out}."
            )

        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "rule": rule,
            "classification": clf,
            "outside_count": n_out,
            "max_outside": max_out,
            "min_outside": min_out,
            "phase_label": rule["label"],
        }

    def enforce(
        self,
        fielders: Dict[str, Dict[str, float]],
        match_format: str,
        current_over: int,
    ) -> Tuple[Dict[str, Dict[str, float]], Dict[str, Any]]:
        """
        Auto-correct a fielding configuration to comply with ICC rules.

        Strategy:
          TOO MANY outside → pull the excess boundary fielders inward by
            scaling their radius to just inside the circle (27 m).
          TOO FEW outside  → push the farthest infield fielders outward to
            a standard boundary depth (56 m, i.e. ~82% of a 68 m boundary).

        Returns (corrected_fielders, compliance_report).
        The compliance_report also contains a 'changes' list describing
        every position that was moved.
        """
        report = self.validate(fielders, match_format, current_over)
        changes = []

        if report["valid"]:
            report["changes"] = changes
            report["corrected"] = False
            return dict(fielders), report

        corrected = {n: dict(p) for n, p in fielders.items()}
        clf = report["classification"]
        max_out = report["max_outside"]
        n_out = report["outside_count"]

        # ── Case 1: Too many outside → pull some inward ───────────────────
        if n_out > max_out:
            excess = n_out - max_out
            # Sort outside fielders by distance descending — pull the
            # deepest ones first (they contribute least to infield pressure)
            outside_sorted = sorted(
                clf["outside"].values(),
                key=lambda e: e["dist_from_centre"],
                reverse=True
            )
            for entry in outside_sorted[:excess]:
                name = entry["name"]
                ox, oz = entry["x"], entry["z"]
                dist = entry["dist_from_centre"]
                if dist < 0.1:
                    dist = 0.1
                # Scale to just inside the circle (26 m keeps a comfortable margin)
                scale = 26.0 / dist
                new_x = round(ox * scale, 2)
                new_z = round(oz * scale, 2)
                corrected[name]["x"] = new_x
                corrected[name]["z"] = new_z
                changes.append({
                    "fielder": name,
                    "reason": "outside_limit_exceeded",
                    "old_pos": {"x": round(ox, 2), "z": round(oz, 2)},
                    "new_pos": {"x": new_x, "z": new_z},
                    "message": (
                        f"{name} pulled from boundary ({dist:.0f} m) to infield "
                        f"({26:.0f} m) — {report['phase_label']} allows only "
                        f"{max_out} outside the circle."
                    ),
                })

        # ── Case 2: Too few outside → push some outward ───────────────────
        elif n_out < report["min_outside"]:
            deficit = report["min_outside"] - n_out
            # Push the farthest infield fielders (not keeper/bowler) outward
            inside_sorted = sorted(
                [e for e in clf["inside"].values()
                 if e["name"] not in _ALWAYS_INSIDE],
                key=lambda e: e["dist_from_centre"],
                reverse=True
            )
            boundary_depth = 56.0  # standard boundary depth (~82% of 68 m)
            for entry in inside_sorted[:deficit]:
                name = entry["name"]
                ox, oz = entry["x"], entry["z"]
                dist = entry["dist_from_centre"]
                if dist < 0.5:
                    # Fielder is near the centre; push straight back
                    new_x = round(ox, 2)
                    new_z = round(boundary_depth, 2)
                else:
                    scale = boundary_depth / dist
                    new_x = round(ox * scale, 2)
                    new_z = round(oz * scale, 2)
                corrected[name]["x"] = new_x
                corrected[name]["z"] = new_z
                changes.append({
                    "fielder": name,
                    "reason": "outside_minimum_not_met",
                    "old_pos": {"x": round(ox, 2), "z": round(oz, 2)},
                    "new_pos": {"x": new_x, "z": new_z},
                    "message": (
                        f"{name} pushed to boundary ({boundary_depth:.0f} m) — "
                        f"{report['phase_label']} requires at least "
                        f"{report['min_outside']} outside the circle."
                    ),
                })

        report["changes"] = changes
        report["corrected"] = True

        # Re-validate the corrected field to confirm compliance
        re_check = self.validate(corrected, match_format, current_over)
        report["after_correction_valid"] = re_check["valid"]
        report["after_correction_outside_count"] = re_check["outside_count"]

        return corrected, report
