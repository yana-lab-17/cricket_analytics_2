"""
server.py  —  NeuroSport Cricket Fielding Analytics Server
Workflow: Phase → Bowling Type → Line/Length → auto-field + predicted trajectory
With dynamic release-speed cordon scaling, real-time line/length tactical offsets,
and 18 bespoke bowling presets.
"""
import asyncio, json, logging, os, base64
from datetime import datetime
from typing import Dict, Any, Set, Tuple

import websockets
from websockets.server import WebSocketServerProtocol

from backend.trajectory import TrajectoryEngine, SHOT_PRESETS
from backend.analytics  import FieldAnalytics, FieldComplianceEngine
from backend.ai_coach   import CricketCoachSession
from backend.cricket_knowledge import (
    FIELDING_POSITIONS, BOWLING_TYPES, DELIVERY_MATRIX,
    DELIVERY_LINES, DELIVERY_LENGTHS,
    PHASE_FIELD_MAP, PHASE_ICC_RULES, MATCH_PHASES, BOWLING_TIPS,
    BOWLING_SPEED_PROFILES, DELIVERY_FIELD_OFFSETS, PHASE_TACTICAL_NOTES,
)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("CricketServer")

# ─────────────────────────────────────────────────────────────────────────────
# 18 DEDICATED FIELDING PRESETS (coordinates in metres, x=off/leg, z=pitch dir)
# RHB Orientation: +X = Off-Side, -X = Leg-Side, +Z = Down Ground, -Z = Behind Stumps
# ─────────────────────────────────────────────────────────────────────────────
FIELDING_PRESETS: Dict[str, Dict[str, Dict[str, float]]] = {

    # ═════════════════════════════════════════════════════════════════════════
    # POWERPLAY PRESETS (Max 2 fielders outside 30-yd circle)
    # ═════════════════════════════════════════════════════════════════════════
    "Fast - Powerplay Attack": {
        "WicketKeeper": {"x":   0.0, "y": 1.0, "z": -21.0},
        "Slip_1":       {"x":   3.2, "y": 1.0, "z": -22.0},
        "Slip_2":       {"x":   6.2, "y": 1.0, "z": -21.2},
        "Slip_3":       {"x":   9.2, "y": 1.0, "z": -20.0},
        "Gully":        {"x":  14.0, "y": 1.0, "z": -10.5},
        "Point":        {"x":  24.0, "y": 1.0, "z":   1.0},
        "Cover":        {"x":  22.0, "y": 1.0, "z":  11.0},
        "MidOff":       {"x":  11.0, "y": 1.0, "z":  24.0},
        "MidOn":        {"x": -11.0, "y": 1.0, "z":  24.0},
        "Bowler":       {"x":   0.0, "y": 1.0, "z":  18.0},
        "FineLeg":      {"x": -28.0, "y": 1.0, "z": -44.0},
    },
    "Medium Pace - Powerplay Attack": {
        "WicketKeeper": {"x":   0.0, "y": 1.0, "z": -15.0},
        "Slip_1":       {"x":   3.0, "y": 1.0, "z": -16.0},
        "Slip_2":       {"x":   5.8, "y": 1.0, "z": -15.2},
        "Gully":        {"x":  13.0, "y": 1.0, "z":  -8.0},
        "Point":        {"x":  24.0, "y": 1.0, "z":   1.0},
        "Cover":        {"x":  22.0, "y": 1.0, "z":  11.0},
        "ExtraCover":   {"x":  14.0, "y": 1.0, "z":  22.0},
        "MidOff":       {"x":  10.0, "y": 1.0, "z":  24.0},
        "MidOn":        {"x": -10.0, "y": 1.0, "z":  24.0},
        "Bowler":       {"x":   0.0, "y": 1.0, "z":  18.0},
        "FineLeg":      {"x": -28.0, "y": 1.0, "z": -42.0},
    },
    "Off Spin - Powerplay Attack": {
        "WicketKeeper": {"x":   0.0, "y": 1.0, "z":  -4.0},
        "Slip_1":       {"x":   2.5, "y": 1.0, "z":  -6.0},
        "ShortLeg":     {"x":  -5.5, "y": 1.0, "z":   3.5},
        "Point":        {"x":  23.0, "y": 1.0, "z":   2.0},
        "Cover":        {"x":  21.0, "y": 1.0, "z":  10.0},
        "MidOff":       {"x":  11.0, "y": 1.0, "z":  23.0},
        "MidOn":        {"x": -11.0, "y": 1.0, "z":  23.0},
        "MidWicket":    {"x": -20.0, "y": 1.0, "z":  10.0},
        "Bowler":       {"x":   0.0, "y": 1.0, "z":  16.0},
        "DeepMidWicket":{"x": -52.0, "y": 1.0, "z":  22.0},
        "LongOn":       {"x": -18.0, "y": 1.0, "z":  58.0},
    },
    "Leg Spin - Powerplay Attack": {
        "WicketKeeper": {"x":   0.0, "y": 1.0, "z":  -4.5},
        "Slip_1":       {"x":   2.8, "y": 1.0, "z":  -6.5},
        "BackwardPoint":{"x":  18.0, "y": 1.0, "z":  -4.0},
        "Point":        {"x":  23.0, "y": 1.0, "z":   1.0},
        "Cover":        {"x":  22.0, "y": 1.0, "z":  10.0},
        "ExtraCover":   {"x":  14.0, "y": 1.0, "z":  21.0},
        "MidWicket":    {"x": -18.0, "y": 1.0, "z":  12.0},
        "MidOn":        {"x": -11.0, "y": 1.0, "z":  23.0},
        "Bowler":       {"x":   0.0, "y": 1.0, "z":  16.0},
        "DeepCover":    {"x":  50.0, "y": 1.0, "z":  28.0},
        "LongOff":      {"x":  18.0, "y": 1.0, "z":  58.0},
    },
    "Left Arm Spin - Powerplay Attack": {
        "WicketKeeper": {"x":   0.0, "y": 1.0, "z":  -4.2},
        "Slip_1":       {"x":   2.5, "y": 1.0, "z":  -6.2},
        "ShortLeg":     {"x":  -5.5, "y": 1.0, "z":   3.5},
        "SquareLeg":    {"x": -22.0, "y": 1.0, "z":  -1.0},
        "MidWicket":    {"x": -20.0, "y": 1.0, "z":  10.0},
        "Point":        {"x":  23.0, "y": 1.0, "z":   1.0},
        "Cover":        {"x":  21.0, "y": 1.0, "z":  10.0},
        "MidOff":       {"x":  11.0, "y": 1.0, "z":  23.0},
        "Bowler":       {"x":   0.0, "y": 1.0, "z":  16.0},
        "DeepMidWicket":{"x": -52.0, "y": 1.0, "z":  22.0},
        "LongOn":       {"x": -18.0, "y": 1.0, "z":  58.0},
    },
    "Chinaman - Powerplay Attack": {
        "WicketKeeper": {"x":   0.0, "y": 1.0, "z":  -4.5},
        "Slip_1":       {"x":   2.8, "y": 1.0, "z":  -6.5},
        "CatchingMidWicket": {"x": -15.0, "y": 1.0, "z": 10.0},
        "Point":        {"x":  23.0, "y": 1.0, "z":   1.0},
        "Cover":        {"x":  21.0, "y": 1.0, "z":  10.0},
        "MidOff":       {"x":  11.0, "y": 1.0, "z":  23.0},
        "SquareLeg":    {"x": -21.0, "y": 1.0, "z":  -2.0},
        "MidWicket":    {"x": -19.0, "y": 1.0, "z":  12.0},
        "Bowler":       {"x":   0.0, "y": 1.0, "z":  16.0},
        "DeepCover":    {"x":  50.0, "y": 1.0, "z":  28.0},
        "DeepMidWicket":{"x": -50.0, "y": 1.0, "z":  24.0},
    },

    # ═════════════════════════════════════════════════════════════════════════
    # MIDDLE OVERS PRESETS (Max 5 fielders outside 30-yd circle)
    # ═════════════════════════════════════════════════════════════════════════
    "Fast - Middle Overs": {
        "WicketKeeper": {"x":   0.0, "y": 1.0, "z": -16.0},
        "ShortThird":   {"x":  16.0, "y": 1.0, "z": -13.0},
        "Point":        {"x":  24.0, "y": 1.0, "z":  -1.0},
        "Cover":        {"x":  22.0, "y": 1.0, "z":  11.0},
        "ExtraCover":   {"x":  13.0, "y": 1.0, "z":  22.0},
        "MidWicket":    {"x": -21.0, "y": 1.0, "z":  10.0},
        "Bowler":       {"x":   0.0, "y": 1.0, "z":  18.0},
        "DeepCover":    {"x":  52.0, "y": 1.0, "z":  22.0},
        "LongOff":      {"x":  18.0, "y": 1.0, "z":  60.0},
        "LongOn":       {"x": -18.0, "y": 1.0, "z":  60.0},
        "DeepMidWicket":{"x": -52.0, "y": 1.0, "z":  22.0},
    },
    "Medium Pace - Middle": {
        "WicketKeeper": {"x":   0.0, "y": 1.0, "z": -14.0},
        "Slip_1":       {"x":   3.0, "y": 1.0, "z": -15.0},
        "Gully":        {"x":  13.0, "y": 1.0, "z":  -6.0},
        "Point":        {"x":  24.0, "y": 1.0, "z":  -1.0},
        "Cover":        {"x":  22.0, "y": 1.0, "z":  11.0},
        "MidOff":       {"x":  11.0, "y": 1.0, "z":  23.0},
        "MidOn":        {"x": -11.0, "y": 1.0, "z":  23.0},
        "Bowler":       {"x":   0.0, "y": 1.0, "z":  18.0},
        "DeepCover":    {"x":  50.0, "y": 1.0, "z":  22.0},
        "LongOn":       {"x": -18.0, "y": 1.0, "z":  58.0},
        "FineLeg":      {"x": -28.0, "y": 1.0, "z": -42.0},
    },
    "Spin - Off Spin Ring": {
        "WicketKeeper":      {"x":   0.0, "y": 1.0, "z":  -4.0},
        "Slip_1":            {"x":   2.5, "y": 1.0, "z":  -6.0},
        "ShortLeg":          {"x":  -5.5, "y": 1.0, "z":   3.5},
        "CatchingMidWicket": {"x": -14.0, "y": 1.0, "z":  11.0},
        "SquareLeg":         {"x": -22.0, "y": 1.0, "z":   0.0},
        "Bowler":            {"x":   0.0, "y": 1.0, "z":  16.0},
        "Point":             {"x":  23.0, "y": 1.0, "z":  -1.0},
        "Cover":             {"x":  21.0, "y": 1.0, "z":  10.0},
        "LongOn":            {"x": -18.0, "y": 1.0, "z":  60.0},
        "DeepMidWicket":     {"x": -52.0, "y": 1.0, "z":  20.0},
        "DeepBackwardSquare":{"x": -48.0, "y": 1.0, "z": -26.0},
    },
    "Spin - Leg Spin Trap": {
        "WicketKeeper": {"x":   0.0, "y": 1.0, "z":  -4.5},
        "Slip_1":       {"x":   2.8, "y": 1.0, "z":  -6.5},
        "BackwardPoint":{"x":  19.0, "y": 1.0, "z":  -5.0},
        "Cover":        {"x":  22.0, "y": 1.0, "z":  11.0},
        "MidWicket":    {"x": -20.0, "y": 1.0, "z":   9.0},
        "Bowler":       {"x":   0.0, "y": 1.0, "z":  16.0},
        "DeepPoint":    {"x":  58.0, "y": 1.0, "z":  -2.0},
        "DeepCover":    {"x":  50.0, "y": 1.0, "z":  30.0},
        "LongOff":      {"x":  18.0, "y": 1.0, "z":  62.0},
        "LongOn":       {"x": -18.0, "y": 1.0, "z":  62.0},
        "DeepMidWicket":{"x": -50.0, "y": 1.0, "z":  22.0},
    },
    "Left Arm Spin Ring": {
        "WicketKeeper": {"x":   0.0, "y": 1.0, "z":  -4.2},
        "Slip_1":       {"x":   2.5, "y": 1.0, "z":  -6.2},
        "ShortLeg":     {"x":  -5.5, "y": 1.0, "z":   3.5},
        "SquareLeg":    {"x": -22.0, "y": 1.0, "z":   0.0},
        "MidWicket":    {"x": -20.0, "y": 1.0, "z":  10.0},
        "Bowler":       {"x":   0.0, "y": 1.0, "z":  16.0},
        "Point":        {"x":  23.0, "y": 1.0, "z":  -1.0},
        "Cover":        {"x":  21.0, "y": 1.0, "z":  10.0},
        "LongOn":       {"x": -18.0, "y": 1.0, "z":  60.0},
        "DeepMidWicket":{"x": -52.0, "y": 1.0, "z":  20.0},
        "FineLeg":      {"x": -28.0, "y": 1.0, "z": -42.0},
    },
    "Chinaman Trap": {
        "WicketKeeper": {"x":   0.0, "y": 1.0, "z":  -4.5},
        "Slip_1":       {"x":   2.8, "y": 1.0, "z":  -6.5},
        "CatchingMidWicket": {"x": -15.0, "y": 1.0, "z": 10.0},
        "Cover":        {"x":  22.0, "y": 1.0, "z":  11.0},
        "SquareLeg":    {"x": -21.0, "y": 1.0, "z":  -2.0},
        "Bowler":       {"x":   0.0, "y": 1.0, "z":  16.0},
        "DeepCover":    {"x":  50.0, "y": 1.0, "z":  30.0},
        "DeepPoint":    {"x":  56.0, "y": 1.0, "z":  -2.0},
        "LongOff":      {"x":  18.0, "y": 1.0, "z":  60.0},
        "LongOn":       {"x": -18.0, "y": 1.0, "z":  60.0},
        "DeepMidWicket":{"x": -50.0, "y": 1.0, "z":  22.0},
    },

    # ═════════════════════════════════════════════════════════════════════════
    # DEATH OVERS PRESETS (Max 5 fielders outside 30-yd circle)
    # ═════════════════════════════════════════════════════════════════════════
    "Fast - Death Yorker Attack": {
        "WicketKeeper":      {"x":   0.0, "y": 1.0, "z": -14.0},
        "ShortThird":        {"x":  17.0, "y": 1.0, "z": -13.0},
        "Point":             {"x":  24.0, "y": 1.0, "z":  -1.0},
        "ExtraCover":        {"x":  19.0, "y": 1.0, "z":  16.0},
        "MidWicket":         {"x": -21.0, "y": 1.0, "z":  10.0},
        "Bowler":            {"x":   0.0, "y": 1.0, "z":  18.0},
        "DeepBackwardPoint": {"x":  54.0, "y": 1.0, "z": -12.0},
        "DeepCover":         {"x":  50.0, "y": 1.0, "z":  32.0},
        "LongOff":           {"x":  18.0, "y": 1.0, "z":  62.0},
        "LongOn":            {"x": -18.0, "y": 1.0, "z":  62.0},
        "DeepMidWicket":     {"x": -52.0, "y": 1.0, "z":  22.0},
    },
    "Medium Pace - Death Slower Ball Trap": {
        "WicketKeeper": {"x":   0.0, "y": 1.0, "z": -13.0},
        "ShortThird":   {"x":  16.0, "y": 1.0, "z": -12.0},
        "Point":        {"x":  24.0, "y": 1.0, "z":   1.0},
        "Cover":        {"x":  20.0, "y": 1.0, "z":  14.0},
        "MidWicket":    {"x": -20.0, "y": 1.0, "z":  11.0},
        "Bowler":       {"x":   0.0, "y": 1.0, "z":  18.0},
        "DeepCover":    {"x":  50.0, "y": 1.0, "z":  28.0},
        "LongOff":      {"x":  17.0, "y": 1.0, "z":  60.0},
        "LongOn":       {"x": -17.0, "y": 1.0, "z":  60.0},
        "DeepMidWicket":{"x": -52.0, "y": 1.0, "z":  24.0},
        "DeepSquareLeg":{"x": -54.0, "y": 1.0, "z":  -8.0},
    },
    "Off Spin - Death Slog Trap": {
        "WicketKeeper":      {"x":   0.0, "y": 1.0, "z":  -4.2},
        "ShortThird":        {"x":  16.0, "y": 1.0, "z": -12.0},
        "Point":             {"x":  23.0, "y": 1.0, "z":   2.0},
        "Cover":             {"x":  20.0, "y": 1.0, "z":  12.0},
        "MidWicket":         {"x": -20.0, "y": 1.0, "z":  12.0},
        "Bowler":            {"x":   0.0, "y": 1.0, "z":  16.0},
        "DeepCover":         {"x":  48.0, "y": 1.0, "z":  28.0},
        "LongOn":            {"x": -18.0, "y": 1.0, "z":  60.0},
        "LongOff":           {"x":  18.0, "y": 1.0, "z":  60.0},
        "DeepMidWicket":     {"x": -52.0, "y": 1.0, "z":  22.0},
        "DeepBackwardSquare":{"x": -48.0, "y": 1.0, "z": -22.0},
    },
    "Leg Spin - Death Googly Trap": {
        "WicketKeeper": {"x":   0.0, "y": 1.0, "z":  -4.5},
        "ShortThird":   {"x":  16.0, "y": 1.0, "z": -12.0},
        "Point":        {"x":  23.0, "y": 1.0, "z":   1.0},
        "ExtraCover":   {"x":  19.0, "y": 1.0, "z":  15.0},
        "MidWicket":    {"x": -20.0, "y": 1.0, "z":  10.0},
        "Bowler":       {"x":   0.0, "y": 1.0, "z":  16.0},
        "DeepPoint":    {"x":  54.0, "y": 1.0, "z":  -2.0},
        "DeepCover":    {"x":  50.0, "y": 1.0, "z":  30.0},
        "LongOff":      {"x":  18.0, "y": 1.0, "z":  62.0},
        "LongOn":       {"x": -18.0, "y": 1.0, "z":  62.0},
        "DeepMidWicket":{"x": -50.0, "y": 1.0, "z":  24.0},
    },
    "Left Arm Spin - Death Flat Dart": {
        "WicketKeeper":      {"x":   0.0, "y": 1.0, "z":  -4.2},
        "ShortThird":        {"x":  16.0, "y": 1.0, "z": -12.0},
        "Point":             {"x":  23.0, "y": 1.0, "z":   1.0},
        "Cover":             {"x":  20.0, "y": 1.0, "z":  12.0},
        "MidWicket":         {"x": -20.0, "y": 1.0, "z":  10.0},
        "Bowler":            {"x":   0.0, "y": 1.0, "z":  16.0},
        "DeepCover":         {"x":  48.0, "y": 1.0, "z":  28.0},
        "LongOn":            {"x": -18.0, "y": 1.0, "z":  60.0},
        "LongOff":           {"x":  18.0, "y": 1.0, "z":  60.0},
        "DeepMidWicket":     {"x": -52.0, "y": 1.0, "z":  22.0},
        "DeepBackwardSquare":{"x": -48.0, "y": 1.0, "z": -22.0},
    },
    "Chinaman - Death Variation Trap": {
        "WicketKeeper": {"x":   0.0, "y": 1.0, "z":  -4.5},
        "ShortThird":   {"x":  16.0, "y": 1.0, "z": -12.0},
        "Point":        {"x":  23.0, "y": 1.0, "z":   1.0},
        "Cover":        {"x":  21.0, "y": 1.0, "z":  12.0},
        "MidWicket":    {"x": -20.0, "y": 1.0, "z":  10.0},
        "Bowler":       {"x":   0.0, "y": 1.0, "z":  16.0},
        "DeepPoint":    {"x":  54.0, "y": 1.0, "z":  -2.0},
        "DeepCover":    {"x":  50.0, "y": 1.0, "z":  30.0},
        "LongOff":      {"x":  18.0, "y": 1.0, "z":  60.0},
        "LongOn":       {"x": -18.0, "y": 1.0, "z":  60.0},
        "DeepMidWicket":{"x": -50.0, "y": 1.0, "z":  22.0},
    },
}

# Aliases for backward compatibility
FIELDING_PRESETS["Powerplay"]        = FIELDING_PRESETS["Fast - Powerplay Attack"]
FIELDING_PRESETS["Middle Overs"]     = FIELDING_PRESETS["Fast - Middle Overs"]
FIELDING_PRESETS["Death Overs"]      = FIELDING_PRESETS["Fast - Death Yorker Attack"]
FIELDING_PRESETS["Pace - Attacking"] = FIELDING_PRESETS["Fast - Powerplay Attack"]

# Always-inside positions (never count against ICC circle limit)
_ALWAYS_INSIDE = {"WicketKeeper", "Bowler"}
INFIELD_RADIUS  = 27.43  # 30 yards in metres


def _classify_outside(fielders: Dict) -> int:
    """Count fielders outside the 30-yard circle."""
    n = 0
    for name, pos in fielders.items():
        if name in _ALWAYS_INSIDE:
            continue
        dist = (pos["x"] ** 2 + pos["z"] ** 2) ** 0.5
        if dist > INFIELD_RADIUS:
            n += 1
    return n


def _enforce_compliance(fielders: Dict, phase: str) -> Tuple[Dict, list]:
    """
    Enforce ICC rules: if more fielders are outside the 30-yard circle than allowed,
    pull the excess boundary fielders inward along their radial vector to radius 24.5 m
    (safely inside the 27.43 m 30-yard circle) to prevent illegal fielding setups.
    Returns (corrected_fielders, list_of_change_messages).
    """
    import math
    rule      = PHASE_ICC_RULES.get(phase, {"max_outside": 5, "label": phase})
    max_out   = rule["max_outside"]
    corrected = {n: dict(p) for n, p in fielders.items()}
    changes   = []

    # Identify outside fielders sorted by distance descending
    outside = []
    for name, pos in corrected.items():
        if name in _ALWAYS_INSIDE:
            continue
        dist = math.sqrt(pos["x"] ** 2 + pos["z"] ** 2)
        if dist > INFIELD_RADIUS:
            outside.append((dist, name))
    outside.sort(reverse=True)

    excess = len(outside) - max_out
    if excess <= 0:
        return corrected, changes

    for dist, name in outside[:excess]:
        pos   = corrected[name]
        scale = 24.5 / max(dist, 0.1)
        new_x = round(pos["x"] * scale, 2)
        new_z = round(pos["z"] * scale, 2)
        corrected[name]["x"] = new_x
        corrected[name]["z"] = new_z
        changes.append(
            f"{name} brought infield to 24.5m (was {dist:.0f}m) — "
            f"{rule['label']} allows max {max_out} outside the circle."
        )
    return corrected, changes


# ─────────────────────────────────────────────────────────────────────────────
# SERVER
# ─────────────────────────────────────────────────────────────────────────────
class CricketSpatialServer:

    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port

        self.trajectory_engine = TrajectoryEngine()
        self.analytics_engine  = FieldAnalytics()
        self.compliance_engine = FieldComplianceEngine()

        # ── Workflow state ──────────────────────────────────────────────────
        self.phase            = "powerplay"          # powerplay | middle | death
        self.bowling_type     = "fast"               # key from BOWLING_TYPES
        self.delivery_line    = "outside_off"        # outside_off | on_middle | to_the_body
        self.delivery_length  = "fuller"             # fuller | yorker | shorter | slower
        self.batter_handedness = "RHB"

        self._compliance_changes = []
        self.fielders = {}

        # Resolve initial field & trajectory
        self._resolve_and_apply_field()
        self._recalculate_trajectory()

        self.active_trajectory = self._traj
        self.active_shot_info  = self._shot_info

        self.connected_clients: Set[WebSocketServerProtocol] = set()
        self.coach_session = CricketCoachSession(self)

    # ── Dynamic Field Synthesis ──────────────────────────────────────────────
    def _resolve_and_apply_field(self):
        """
        Dynamically synthesize fielding setup from:
        1. Base Phase × Bowling Type bespoke preset (18 dedicated configurations)
        2. Release speed cordon depth scaling
        3. Real-time delivery line & length tactical offsets
        4. Handedness mirroring (LHB / RHB)
        5. ICC compliance verification and enforcement
        """
        preset_name = PHASE_FIELD_MAP.get(self.phase, {}).get(
            self.bowling_type, "Fast - Powerplay Attack"
        )
        self.current_preset = preset_name

        # 1. Base preset
        base_dict = FIELDING_PRESETS.get(preset_name, FIELDING_PRESETS["Fast - Powerplay Attack"])
        field = {n: dict(p) for n, p in base_dict.items()}

        # 2. Release speed cordon depth adjustment
        speed_prof = BOWLING_SPEED_PROFILES.get(self.bowling_type)
        if speed_prof:
            kd = speed_prof.get("keeper_depth_m")
            sd = speed_prof.get("slip_depth_m")
            if "WicketKeeper" in field and kd:
                field["WicketKeeper"]["z"] = -round(kd, 2)
            if "Slip_1" in field and sd:
                field["Slip_1"]["z"] = -round(sd, 2)
            if "Slip_2" in field and sd:
                field["Slip_2"]["z"] = -round(sd - 0.8, 2)
            if "Slip_3" in field and sd:
                field["Slip_3"]["z"] = -round(sd - 1.8, 2)

        # 3. Dynamic Delivery Offsets (Line × Length)
        line_offsets = DELIVERY_FIELD_OFFSETS.get(self.delivery_line, {})
        length_offsets = DELIVERY_FIELD_OFFSETS.get(self.delivery_length, {})
        for name, pos in field.items():
            dx = 0.0
            dz = 0.0
            if name in line_offsets:
                dx += line_offsets[name].get("dx", 0.0)
                dz += line_offsets[name].get("dz", 0.0)
            if name in length_offsets:
                dx += length_offsets[name].get("dx", 0.0)
                dz += length_offsets[name].get("dz", 0.0)
            pos["x"] = round(pos["x"] + dx, 2)
            pos["z"] = round(pos["z"] + dz, 2)

        # 4. Mirror if Left-Hand Batter
        if self.batter_handedness == "LHB":
            field = self.analytics_engine.mirror_field_for_lhb(field)

        # 5. Enforce ICC compliance
        self.fielders, self._compliance_changes = _enforce_compliance(field, self.phase)

    # ── Trajectory calculation ───────────────────────────────────────────────
    def _recalculate_trajectory(self):
        key  = (self.delivery_line, self.delivery_length)
        spec = DELIVERY_MATRIX.get(key, list(DELIVERY_MATRIX.values())[0])
        phi  = -spec["phi"] if self.batter_handedness == "LHB" else spec["phi"]

        self._traj = self.trajectory_engine.calculate_trajectory(
            v0=spec["v0"], theta=spec["theta"], phi=phi,
            k=0.006, spin_rpm=0.0, is_lhb=(self.batter_handedness == "LHB")
        )
        metrics = self.trajectory_engine.get_shot_metrics(self._traj)
        self._shot_info = {
            "shot_label":      spec["shot_label"],
            "description":     spec["description"],
            "beat_prob":       spec["beat_prob"],
            "delivery_line":   self.delivery_line,
            "delivery_length": self.delivery_length,
            "line_label":      DELIVERY_LINES.get(self.delivery_line, self.delivery_line),
            "length_label":    DELIVERY_LENGTHS.get(self.delivery_length, self.delivery_length),
            **metrics,
        }

    # ── Manual Field application (legacy/override) ───────────────────────────
    def _apply_field(self, preset_name: str):
        if preset_name not in FIELDING_PRESETS:
            return
        self.current_preset = preset_name
        raw = {n: dict(p) for n, p in FIELDING_PRESETS[preset_name].items()}
        if self.batter_handedness == "LHB":
            raw = self.analytics_engine.mirror_field_for_lhb(raw)
        self.fielders, self._compliance_changes = _enforce_compliance(raw, self.phase)

    # ── State payload ────────────────────────────────────────────────────────
    def build_state_payload(self) -> dict:
        cov = self.analytics_engine.calculate_field_coverage(self.fielders)
        vor = self.analytics_engine.compute_voronoi(self.fielders)

        lx = self._shot_info.get("landing_x", 0.0)
        lz = self._shot_info.get("landing_z", 0.0)
        ft = self._shot_info.get("flight_time", 1.0)
        pursuit   = self.analytics_engine.calculate_apollonius_pursuit(lx, lz, ft, self.fielders)
        intercept = self.analytics_engine.assess_shot_intercept(lx, lz, ft, self.fielders)

        outside_count = _classify_outside(self.fielders)
        rule          = PHASE_ICC_RULES.get(self.phase, {})

        bowling_info = BOWLING_TYPES.get(self.bowling_type, {})
        phase_info   = MATCH_PHASES.get(self.phase, {})
        tips         = BOWLING_TIPS.get(self.bowling_type, [])
        tac_note     = PHASE_TACTICAL_NOTES.get((self.phase, self.bowling_type), "")

        return {
            # Workflow state
            "phase":             self.phase,
            "phase_label":       phase_info.get("label", self.phase),
            "phase_info":        phase_info,
            "bowling_type":      self.bowling_type,
            "bowling_label":     bowling_info.get("label", self.bowling_type),
            "bowling_info":      bowling_info,
            "delivery_line":     self.delivery_line,
            "delivery_length":   self.delivery_length,
            "batter_handedness": self.batter_handedness,
            # Field
            "preset":            self.current_preset,
            "fielders":          self.fielders,
            # Analytics
            "coverage_score":    cov["coverage_score"],
            "analytics":         cov,
            "voronoi":           vor,
            # Trajectory & prediction
            "trajectory":        self._traj,
            "shot_info":         self._shot_info,
            "intercept":         intercept,
            "pursuit":           pursuit,
            # Compliance
            "compliance": {
                "outside_count": outside_count,
                "max_outside":   rule.get("max_outside", 5),
                "phase_label":   rule.get("label", ""),
                "changes":       self._compliance_changes,
                "valid":         len(self._compliance_changes) == 0,
            },
            # Coaching
            "tactical_note":     tac_note,
            "bowling_tips":      tips,
            # Catalogue
            "available_phases":        list(MATCH_PHASES.keys()),
            "available_bowling_types": list(BOWLING_TYPES.keys()),
            "available_lines":         list(DELIVERY_LINES.keys()),
            "available_lengths":       list(DELIVERY_LENGTHS.keys()),
            "delivery_lines_labels":   DELIVERY_LINES,
            "delivery_lengths_labels": DELIVERY_LENGTHS,
            "bowling_types_labels":    {k: v["label"] for k, v in BOWLING_TYPES.items()},
            "available_shots":         list(SHOT_PRESETS.keys()),
            "available_presets":       list(FIELDING_PRESETS.keys()),
        }

    # ── Broadcast helpers ────────────────────────────────────────────────────
    async def broadcast_state(self):
        if not self.connected_clients:
            return
        payload = json.dumps(self.build_state_payload())
        results = await asyncio.gather(
            *[c.send(payload) for c in self.connected_clients],
            return_exceptions=True
        )
        for c, r in zip(list(self.connected_clients), results):
            if isinstance(r, Exception):
                self.connected_clients.discard(c)

    async def broadcast_command(self, payload: dict):
        if not self.connected_clients:
            return
        s = json.dumps(payload)
        await asyncio.gather(*[c.send(s) for c in self.connected_clients], return_exceptions=True)

    # ── Helpers used by AI coach ─────────────────────────────────────────────
    async def set_preset(self, preset_name: str):
        self._apply_field(preset_name)
        await self.broadcast_state()

    async def update_fielder(self, name: str, x: float, z: float):
        if name in self.fielders:
            self.fielders[name]["x"] = round(float(x), 2)
            self.fielders[name]["z"] = round(float(z), 2)
            self.fielders, self._compliance_changes = _enforce_compliance(
                self.fielders, self.phase
            )
            await self.broadcast_state()

    async def set_handedness(self, new_h: str):
        if new_h in ("RHB", "LHB") and new_h != self.batter_handedness:
            self.batter_handedness = new_h
            self._resolve_and_apply_field()
            self._recalculate_trajectory()
            await self.broadcast_state()

    async def simulate_shot(self, shot_type: str):
        if shot_type in SHOT_PRESETS:
            cfg = SHOT_PRESETS[shot_type]
            is_l = (self.batter_handedness == "LHB")
            self._traj = self.trajectory_engine.calculate_trajectory(
                v0=cfg["v0"], theta=cfg["theta"], phi=cfg["phi"],
                k=0.006, spin_rpm=0.0, is_lhb=is_l
            )
            metrics = self.trajectory_engine.get_shot_metrics(self._traj)
            self._shot_info = {
                "shot_label":  shot_type,
                "description": cfg.get("description", ""),
                "beat_prob":   0.1,
                **metrics,
            }
            self.active_trajectory = self._traj
            self.active_shot_info  = self._shot_info
            await self.broadcast_state()

    # ── Message handler ──────────────────────────────────────────────────────
    async def handle_client(self, websocket: WebSocketServerProtocol):
        self.connected_clients.add(websocket)
        logger.info(f"Client connected: {websocket.remote_address}")
        try:
            await websocket.send(json.dumps(self.build_state_payload()))
            async for raw in websocket:
                try:
                    data = json.loads(raw)
                except Exception:
                    continue

                action = data.get("action", "")

                # ── Step 1: Set phase (powerplay / middle / death) ──────────
                if action == "set_phase":
                    new_phase = data.get("phase", "").lower()
                    if new_phase in MATCH_PHASES:
                        self.phase = new_phase
                        self._resolve_and_apply_field()
                        logger.info(f"Phase → {self.phase}  preset → {self.current_preset}")
                    await self.broadcast_state()

                # ── Step 2: Set bowling type ────────────────────────────────
                elif action == "set_bowling_type":
                    bt = data.get("bowling_type", "")
                    if bt in BOWLING_TYPES:
                        self.bowling_type = bt
                        self._resolve_and_apply_field()
                        logger.info(f"Bowling → {bt}  phase → {self.phase}  preset → {self.current_preset}")
                    await self.broadcast_state()

                # ── Step 3: Set delivery line ───────────────────────────────
                elif action == "set_delivery_line":
                    line = data.get("line", "")
                    if line in DELIVERY_LINES:
                        self.delivery_line = line
                        self._resolve_and_apply_field()
                        self._recalculate_trajectory()
                    await self.broadcast_state()

                # ── Step 3b: Set delivery length ────────────────────────────
                elif action == "set_delivery_length":
                    length = data.get("length", "")
                    if length in DELIVERY_LENGTHS:
                        self.delivery_length = length
                        self._resolve_and_apply_field()
                        self._recalculate_trajectory()
                    await self.broadcast_state()

                # ── Batter handedness ───────────────────────────────────────
                elif action == "set_handedness":
                    await self.set_handedness(data.get("handedness", "RHB").upper())

                # ── Manual preset override ──────────────────────────────────
                elif action == "set_preset":
                    pn = data.get("preset", "")
                    if pn in FIELDING_PRESETS:
                        self._apply_field(pn)
                    await self.broadcast_state()

                # ── Individual fielder drag ─────────────────────────────────
                elif action == "update_fielder":
                    nm = data.get("name", "")
                    if nm in self.fielders:
                        if "x" in data: self.fielders[nm]["x"] = round(float(data["x"]), 2)
                        if "z" in data: self.fielders[nm]["z"] = round(float(data["z"]), 2)
                        self.fielders, self._compliance_changes = _enforce_compliance(
                            self.fielders, self.phase
                        )
                    await self.broadcast_state()

                # ── Simulate a named shot ───────────────────────────────────
                elif action == "simulate_shot":
                    st = data.get("shot_type", "")
                    await self.simulate_shot(st)

                # ── AI Coach message ────────────────────────────────────────
                elif action == "coach_message":
                    text = data.get("text", "").strip()
                    if text:
                        resp = await self.coach_session.send_message(text)
                        await websocket.send(json.dumps(resp))

                # ── Misc ────────────────────────────────────────────────────
                elif action == "get_state":
                    await websocket.send(json.dumps(self.build_state_payload()))

                elif action == "ping":
                    await websocket.send(json.dumps({"action": "pong"}))

                elif action == "export_data":
                    export_dir = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "exports"
                    )
                    os.makedirs(export_dir, exist_ok=True)
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    fn = f"cricket_analytics_{ts}.json"
                    payload = self.build_state_payload()
                    payload["export_timestamp"] = datetime.now().isoformat()
                    with open(os.path.join(export_dir, fn), "w") as f:
                        json.dump(payload, f, indent=2, default=str)
                    b64 = base64.b64encode(
                        json.dumps(payload, indent=2, default=str).encode()
                    ).decode()
                    await websocket.send(json.dumps({
                        "action":   "export_ready",
                        "filename": fn,
                        "data_uri": f"data:application/json;base64,{b64}"
                    }))

        except websockets.exceptions.ConnectionClosedOK:
            logger.info(f"Client {websocket.remote_address} disconnected")
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning(f"Client error: {e}")
        finally:
            self.connected_clients.discard(websocket)

    async def start(self):
        logger.info(f"NeuroSport Cricket Server  ws://{self.host}:{self.port}")
        async with websockets.serve(self.handle_client, self.host, self.port):
            await asyncio.Future()


def main():
    server = CricketSpatialServer()
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("Server stopped.")


if __name__ == "__main__":
    main()
