"""
cricket_knowledge.py
Complete cricket knowledge base:
- Phase rules (Powerplay / Middle / Death) with ICC field restrictions
- 18 Dedicated bowling presets per phase (Fast, Medium Pace, Off Spin, Leg Spin, LA Spin, Chinaman)
- Delivery matrix: line × length → ball physics + predicted shot response
- Real-time tactical delivery offsets (line/length shifts)
- Release speed profiles and role-based kinematics
- Fielding position catalogue
"""

# ─────────────────────────────────────────────────────────────────────────────
# MATCH PHASES  (the 3 modes the user selects first)
# ─────────────────────────────────────────────────────────────────────────────
MATCH_PHASES = {
    "powerplay": {
        "label":          "Powerplay",
        "t20_overs":      "1–6",
        "odi_overs":      "1–10",
        "max_outside":    2,          # ICC: max fielders outside 30-yard circle
        "description":    "Maximum 2 fielders outside the 30-yard circle. Attack with slips and ring."
    },
    "middle": {
        "label":          "Middle Overs",
        "t20_overs":      "7–15",
        "odi_overs":      "11–40",
        "max_outside":    5,
        "description":    "Up to 5 outside. Balance containment with wicket-taking catchers."
    },
    "death": {
        "label":          "Death Overs",
        "t20_overs":      "16–20",
        "odi_overs":      "41–50",
        "max_outside":    5,
        "description":    "All 5 outer slots on boundary protection. Yorkers and variations."
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# BOWLING TYPES
# ─────────────────────────────────────────────────────────────────────────────
BOWLING_TYPES = {
    "fast": {
        "label":       "Fast Bowling",
        "speed_kmh":   (140, 155),
        "avg_speed":   145.0,
        "swing":       "outswing",
        "seam":        True,
        "spin":        False,
        "description": "Express pace, outswing, seam movement. Primary weapon: edge to slips.",
    },
    "medium_pace": {
        "label":       "Medium Pace",
        "speed_kmh":   (115, 135),
        "avg_speed":   125.0,
        "swing":       "inswing/outswing",
        "seam":        True,
        "spin":        False,
        "description": "Swing and seam at controlled pace. Excellent in middle overs.",
    },
    "off_spin": {
        "label":       "Off Spin",
        "speed_kmh":   (80, 95),
        "avg_speed":   86.0,
        "swing":       None,
        "seam":        False,
        "spin":        "off",
        "description": "Turns from off to leg for RHB. Short leg and catching mid-wicket key.",
    },
    "leg_spin": {
        "label":       "Leg Spin",
        "speed_kmh":   (75, 90),
        "avg_speed":   82.0,
        "swing":       None,
        "seam":        False,
        "spin":        "leg",
        "description": "Turns away from RHB. Slip, deep cover, and long-off important.",
    },
    "left_arm_spin": {
        "label":       "Left Arm Spin",
        "speed_kmh":   (80, 92),
        "avg_speed":   84.0,
        "swing":       None,
        "seam":        False,
        "spin":        "left_orthodox",
        "description": "Orthodox spin for RHB acts like off-spin. Leg-side ring critical.",
    },
    "left_arm_chinaman": {
        "label":       "Left Arm Chinaman",
        "speed_kmh":   (78, 92),
        "avg_speed":   82.0,
        "swing":       None,
        "seam":        False,
        "spin":        "left_wrist",
        "description": "Wrist spin from left-arm, turns away from RHB like leg-spin.",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# SPEED PROFILES & CORDON DEPTH SCALING
# Keeper and slip depths adjust dynamically based on release speed
# ─────────────────────────────────────────────────────────────────────────────
BOWLING_SPEED_PROFILES = {
    "fast": {
        "avg_speed_kmh":   145.0,
        "keeper_depth_m":  21.0,
        "slip_depth_m":    22.0,
        "gully_depth_m":   11.0,
        "cordon_spacing_m": 3.0,
    },
    "medium_pace": {
        "avg_speed_kmh":   125.0,
        "keeper_depth_m":  15.0,
        "slip_depth_m":    16.0,
        "gully_depth_m":    9.0,
        "cordon_spacing_m": 2.8,
    },
    "off_spin": {
        "avg_speed_kmh":   86.0,
        "keeper_depth_m":  4.0,   # standing up to stumps
        "slip_depth_m":    6.0,
        "gully_depth_m":   5.5,
        "cordon_spacing_m": 2.5,
    },
    "leg_spin": {
        "avg_speed_kmh":   82.0,
        "keeper_depth_m":  4.5,   # up to stumps with room for turn
        "slip_depth_m":    6.5,
        "gully_depth_m":   5.8,
        "cordon_spacing_m": 2.8,
    },
    "left_arm_spin": {
        "avg_speed_kmh":   84.0,
        "keeper_depth_m":  4.2,
        "slip_depth_m":    6.2,
        "gully_depth_m":   5.5,
        "cordon_spacing_m": 2.5,
    },
    "left_arm_chinaman": {
        "avg_speed_kmh":   82.0,
        "keeper_depth_m":  4.5,
        "slip_depth_m":    6.5,
        "gully_depth_m":   5.8,
        "cordon_spacing_m": 2.8,
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# PHASE × BOWLING_TYPE → 18 BESPOKE PRESETS
# Every bowling type has a distinct, customized field in every match phase
# ─────────────────────────────────────────────────────────────────────────────
PHASE_FIELD_MAP = {
    "powerplay": {
        "fast":                "Fast - Powerplay Attack",
        "medium_pace":         "Medium Pace - Powerplay Attack",
        "off_spin":            "Off Spin - Powerplay Attack",
        "leg_spin":            "Leg Spin - Powerplay Attack",
        "left_arm_spin":       "Left Arm Spin - Powerplay Attack",
        "left_arm_chinaman":   "Chinaman - Powerplay Attack",
    },
    "middle": {
        "fast":                "Fast - Middle Overs",
        "medium_pace":         "Medium Pace - Middle",
        "off_spin":            "Spin - Off Spin Ring",
        "leg_spin":            "Spin - Leg Spin Trap",
        "left_arm_spin":       "Left Arm Spin Ring",
        "left_arm_chinaman":   "Chinaman Trap",
    },
    "death": {
        "fast":                "Fast - Death Yorker Attack",
        "medium_pace":         "Medium Pace - Death Slower Ball Trap",
        "off_spin":            "Off Spin - Death Slog Trap",
        "leg_spin":            "Leg Spin - Death Googly Trap",
        "left_arm_spin":       "Left Arm Spin - Death Flat Dart",
        "left_arm_chinaman":   "Chinaman - Death Variation Trap",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# PHASE TACTICAL NOTES (18 bespoke tactical game plans)
# ─────────────────────────────────────────────────────────────────────────────
PHASE_TACTICAL_NOTES = {
    ("powerplay", "fast"):
        "Attack with 3 slips + gully (7-2 off-side bias). Only 2 allowed outside (Fine Leg). Bowl full outswing into the 4th stump corridor.",
    ("powerplay", "medium_pace"):
        "2 slips + floating gully. Tight off-side ring (Cover, MidOff). Bowl disciplined swinging line outside off, force false drives.",
    ("powerplay", "off_spin"):
        "Powerplay spin choke: 1 slip + short leg + catching mid-wicket. Deep Mid-Wicket guards the slog sweep. Bowl into rough on off stump.",
    ("powerplay", "leg_spin"):
        "Attacking wrist spin: 1 slip + backward point + deep cover. Toss up outside off, invite the drive over the infield.",
    ("powerplay", "left_arm_spin"):
        "Over the wicket to RHB: Slip + short leg + square leg. Deep Mid-Wicket covers the boundary. Angle into pads with turn.",
    ("powerplay", "left_arm_chinaman"):
        "Wrist spin turning into RHB: 1 slip + catching mid-wicket + deep mid-wicket. Vary flight and angle.",

    ("middle", "fast"):
        "Pace containment: 4 boundary riders (Deep Cover, Deep Mid-Wicket, Long-Off, Long-On). Bowl cross-seam cutters and back-of-length.",
    ("middle", "medium_pace"):
        "Mixed ring: Deep Cover, Long-On, Fine Leg. Use subtle width and reverse swing after 25 overs. Restrict singles.",
    ("middle", "off_spin"):
        "Classic off-spin squeeze: Short Leg + Catching Mid-Wicket. Deep Mid-Wicket and Long-On protect the boundary. Attack the bat-pad.",
    ("middle", "leg_spin"):
        "Wrist spin trap: Slip + Deep Cover + Long-Off + Deep Mid-Wicket. Toss up outside off to generate dipping turn.",
    ("middle", "left_arm_spin"):
        "Left-arm orthodox squeeze: Short Leg + Square Leg. Angle into the body, tie down the right-hander with dot balls.",
    ("middle", "left_arm_chinaman"):
        "Chinaman variation trap: Deep Cover, Deep Mid-Wicket, Long-On. Bowl the wrong-un (arm ball) to trap LBW.",

    ("death", "fast"):
        "Wide yorker & bouncer setup: Deep Backward Point, Deep Cover, Long-Off, Long-On, Deep Mid-Wicket. Bowl yorkers targeting the tramline.",
    ("death", "medium_pace"):
        "Change of pace trap: Knuckle balls and back-of-hand slower balls. Long-Off, Long-On, Deep Mid-Wicket, Deep Square Leg.",
    ("death", "off_spin"):
        "Death off-spin: Dart into the pads. Deep Mid-Wicket (cow corner), Long-On, Deep Backward Square, Deep Cover.",
    ("death", "leg_spin"):
        "Googly variations: Deep Cover, Deep Mid-Wicket, Long-Off, Long-On, Deep Point. Bowl flatter googlies into the stumps.",
    ("death", "left_arm_spin"):
        "Flat dart into the blockhole: Deep Mid-Wicket, Long-On, Deep Backward Square, Deep Cover. Keep it low and straight.",
    ("death", "left_arm_chinaman"):
        "Wrist spin variation death: Deep Mid-Wicket, Long-On, Deep Cover, Deep Point, Deep Square Leg. High-risk, high-reward.",
}

# ─────────────────────────────────────────────────────────────────────────────
# DYNAMIC DELIVERY OFFSETS (Line & Length Shifts)
# Fielder coordinates shift in real-time when the delivery specification changes
# ─────────────────────────────────────────────────────────────────────────────
DELIVERY_FIELD_OFFSETS = {
    # ── LINE OFFSETS ──────────────────────────────────────────────────────────
    "outside_off": {
        # Off-side corridor attack: ring shifts 1.5 - 2.5m towards off (+X)
        "Point":              {"dx": +1.5, "dz": -0.5},
        "Cover":              {"dx": +2.0, "dz": -0.5},
        "ExtraCover":         {"dx": +2.0, "dz": +0.0},
        "MidOff":             {"dx": +1.5, "dz": +1.0},
        "MidOn":              {"dx": +2.0, "dz": +1.5},
        "MidWicket":          {"dx": +2.5, "dz": +1.0},
        "FineLeg":            {"dx": +2.0, "dz": +0.0},
        "DeepCover":          {"dx": +2.5, "dz": +0.0},
        "DeepPoint":          {"dx": +2.0, "dz": -1.0},
        "DeepBackwardPoint":  {"dx": +2.0, "dz": -1.0},
    },
    "on_middle": {
        # Straight line: straight fielders pinch tighter; ring balances symmetrically
        "MidOff":             {"dx": -1.0, "dz": +1.5},
        "MidOn":              {"dx": +1.0, "dz": +1.5},
        "LongOff":            {"dx": -2.0, "dz": +0.0},
        "LongOn":             {"dx": +2.0, "dz": +0.0},
        "Cover":              {"dx": -0.5, "dz": +0.0},
        "MidWicket":          {"dx": +0.5, "dz": +0.0},
    },
    "to_the_body": {
        # Leg-side attack: entire field rotates 2 - 3m towards leg-side (-X)
        "Point":              {"dx": -2.0, "dz": +0.0},
        "Cover":              {"dx": -2.5, "dz": +0.0},
        "MidOff":             {"dx": -2.5, "dz": +0.0},
        "MidOn":              {"dx": -1.5, "dz": -1.0},
        "MidWicket":          {"dx": -2.0, "dz": -0.5},
        "SquareLeg":          {"dx": -2.0, "dz": -1.0},
        "FineLeg":            {"dx": -3.0, "dz": -2.0},
        "DeepSquareLeg":      {"dx": -2.5, "dz": -1.0},
        "DeepMidWicket":      {"dx": -2.5, "dz": +0.0},
        "DeepBackwardSquare": {"dx": -2.5, "dz": -2.0},
    },

    # ── LENGTH OFFSETS ────────────────────────────────────────────────────────
    "fuller": {
        # Driven length: Ring moves 1.5m closer to save single; straight fielders back up
        "Cover":              {"dx": +0.0, "dz": -1.5},
        "ExtraCover":         {"dx": +0.0, "dz": -1.5},
        "MidOff":             {"dx": +0.0, "dz": -1.5},
        "MidOn":              {"dx": +0.0, "dz": -1.5},
        "MidWicket":          {"dx": +0.0, "dz": -1.5},
        "LongOff":            {"dx": +0.0, "dz": +2.0},
        "LongOn":             {"dx": +0.0, "dz": +2.0},
    },
    "yorker": {
        # Toe-crusher: Deep boundary fielders drop 3m back to cushions; keeper slightly forward
        "LongOff":            {"dx": +0.0, "dz": +3.0},
        "LongOn":             {"dx": +0.0, "dz": +3.0},
        "DeepCover":          {"dx": +2.0, "dz": +2.0},
        "DeepMidWicket":      {"dx": -1.0, "dz": +2.5},
        "WicketKeeper":       {"dx": +0.0, "dz": +2.0},  # stands closer to prevent bye single
    },
    "shorter": {
        # Bouncer: Behind-the-wicket fielders drop back; ring braces for cross-bat pull/cut
        "FineLeg":            {"dx": -2.0, "dz": -4.0},
        "DeepSquareLeg":      {"dx": -2.0, "dz": -3.0},
        "DeepBackwardSquare": {"dx": -2.0, "dz": -3.0},
        "Gully":              {"dx": +1.0, "dz": -1.5},
        "Point":              {"dx": +1.5, "dz": -1.0},
        "DeepPoint":          {"dx": +2.0, "dz": -2.0},
        "DeepBackwardPoint":  {"dx": +2.0, "dz": -3.0},
    },
    "slower": {
        # Change of pace: Catchers on the ring take 2.5m forward for mistimed chips
        "Cover":              {"dx": +0.0, "dz": -2.5},
        "ExtraCover":         {"dx": +0.0, "dz": -2.5},
        "MidWicket":          {"dx": +0.0, "dz": -2.5},
        "MidOff":             {"dx": +0.0, "dz": -2.0},
        "MidOn":              {"dx": +0.0, "dz": -2.0},
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# ROLE-BASED KINEMATICS
# Heterogeneous acceleration, speed, reaction latency and reach envelopes
# ─────────────────────────────────────────────────────────────────────────────
ROLE_KINEMATICS = {
    "close_catching": {
        "tau_react":       0.20,
        "a_max":           4.5,
        "v_max":           6.2,
        "reaction_radius": 3.0,
        "description":     "Reflex catchers in slips, gully, short leg. Fast latency, low top speed."
    },
    "specialist_wk": {
        "tau_react":       0.18,
        "a_max":           4.8,
        "v_max":           6.0,
        "reaction_radius": 3.5,
        "description":     "Wicket-keeper. Instant reaction, explosive lateral dive."
    },
    "specialist_bowl": {
        "tau_react":       0.40,
        "a_max":           3.8,
        "v_max":           7.5,
        "reaction_radius": 6.5,
        "description":     "Bowler in follow-through. Slightly slower reaction due to delivery stride."
    },
    "infield": {
        "tau_react":       0.28,
        "a_max":           4.8,
        "v_max":           8.0,
        "reaction_radius": 9.5,
        "description":     "Inner ring fielders (Point, Cover, Mid-Wicket). Explosive burst to save 1s."
    },
    "boundary": {
        "tau_react":       0.35,
        "a_max":           4.2,
        "v_max":           8.8,
        "reaction_radius": 12.0,
        "description":     "Boundary riders (Deep Cover, Deep Mid-Wicket, Long-On). High top sprint speed."
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# DELIVERY MATRIX
# line × length → ball physics + predicted batter response
# ─────────────────────────────────────────────────────────────────────────────
DELIVERY_MATRIX = {
    # ── Outside off stump ─────────────────────────────────────────────────
    ("outside_off", "fuller"): {
        "shot_label":  "Cover Drive",
        "v0": 33.0, "theta": 12.0, "phi":  42.0, "phi_spread": 20.0,
        "beat_prob": 0.12,
        "description": "Full outside off → batter drives through cover.",
    },
    ("outside_off", "yorker"): {
        "shot_label":  "Driven / Squeezed",
        "v0": 22.0, "theta":  6.0, "phi":  30.0, "phi_spread": 15.0,
        "beat_prob": 0.35,
        "description": "Yorker outside off → squeezed past mid-off or to cover.",
    },
    ("outside_off", "shorter"): {
        "shot_label":  "Square Cut",
        "v0": 34.0, "theta":  9.0, "phi":  80.0, "phi_spread": 18.0,
        "beat_prob": 0.10,
        "description": "Short outside off → hard cut behind point.",
    },
    ("outside_off", "slower"): {
        "shot_label":  "Mistimed Drive",
        "v0": 24.0, "theta": 18.0, "phi":  38.0, "phi_spread": 22.0,
        "beat_prob": 0.22,
        "description": "Slower ball outside off → mistimed, hangs in the air.",
    },
    # ── On middle / good length ───────────────────────────────────────────
    ("on_middle", "fuller"): {
        "shot_label":  "Straight Drive",
        "v0": 36.0, "theta": 15.0, "phi":   5.0, "phi_spread": 15.0,
        "beat_prob": 0.08,
        "description": "Full on middle → powered straight down the ground.",
    },
    ("on_middle", "yorker"): {
        "shot_label":  "Dug Out / Squeezed",
        "v0": 18.0, "theta":  4.0, "phi":  10.0, "phi_spread": 12.0,
        "beat_prob": 0.40,
        "description": "Yorker on middle → toe-crushed, minimal distance.",
    },
    ("on_middle", "shorter"): {
        "shot_label":  "Pull Shot",
        "v0": 36.0, "theta": 22.0, "phi": -60.0, "phi_spread": 20.0,
        "beat_prob": 0.09,
        "description": "Short on middle → pull through mid-wicket region.",
    },
    ("on_middle", "slower"): {
        "shot_label":  "Lofted Straight",
        "v0": 30.0, "theta": 30.0, "phi":   0.0, "phi_spread": 18.0,
        "beat_prob": 0.18,
        "description": "Slower on middle → slog loft over long-on.",
    },
    # ── To the body (leg stump line) ──────────────────────────────────────
    ("to_the_body", "fuller"): {
        "shot_label":  "Flick / Whip",
        "v0": 30.0, "theta": 14.0, "phi": -40.0, "phi_spread": 18.0,
        "beat_prob": 0.10,
        "description": "Full to the body → flicked through mid-wicket.",
    },
    ("to_the_body", "yorker"): {
        "shot_label":  "Leg Glance",
        "v0": 20.0, "theta":  8.0, "phi": -25.0, "phi_spread": 14.0,
        "beat_prob": 0.30,
        "description": "Yorker to the body → glanced to fine leg region.",
    },
    ("to_the_body", "shorter"): {
        "shot_label":  "Hook / Pull",
        "v0": 37.0, "theta": 26.0, "phi": -70.0, "phi_spread": 22.0,
        "beat_prob": 0.08,
        "description": "Short to the body → hook toward deep square leg.",
    },
    ("to_the_body", "slower"): {
        "shot_label":  "Slog Sweep",
        "v0": 32.0, "theta": 28.0, "phi": -50.0, "phi_spread": 22.0,
        "beat_prob": 0.15,
        "description": "Slower to the body → slog sweep to cow corner.",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# DELIVERY LINE / LENGTH LABELS for UI display
# ─────────────────────────────────────────────────────────────────────────────
DELIVERY_LINES = {
    "outside_off":  "Outside Off Stump",
    "on_middle":    "On Middle / Good Length",
    "to_the_body":  "To the Body (Leg)",
}

DELIVERY_LENGTHS = {
    "fuller":  "Full / Swinging Length",
    "yorker":  "Yorker",
    "shorter": "Short / Bouncer",
    "slower":  "Slower Ball",
}

# ─────────────────────────────────────────────────────────────────────────────
# ICC FIELDING RESTRICTIONS
# ─────────────────────────────────────────────────────────────────────────────
PHASE_ICC_RULES = {
    "powerplay": {"max_outside": 2, "label": "Powerplay"},
    "middle":    {"max_outside": 5, "label": "Middle Overs"},
    "death":     {"max_outside": 5, "label": "Death Overs"},
}

# ─────────────────────────────────────────────────────────────────────────────
# FULL FIELDING POSITION CATALOGUE
# ─────────────────────────────────────────────────────────────────────────────
FIELDING_POSITIONS = {
    "WicketKeeper":      {"name": "Wicket Keeper",        "aliases": ["keeper","wk"],               "category": "specialist_wk",  "side": "straight"},
    "Slip_1":            {"name": "First Slip",           "aliases": ["slip 1","first slip"],        "category": "close_catching", "side": "off"},
    "Slip_2":            {"name": "Second Slip",          "aliases": ["slip 2","second slip"],       "category": "close_catching", "side": "off"},
    "Slip_3":            {"name": "Third Slip",           "aliases": ["slip 3"],                     "category": "close_catching", "side": "off"},
    "LegSlip":           {"name": "Leg Slip",             "aliases": ["leg slip"],                   "category": "close_catching", "side": "leg"},
    "Gully":             {"name": "Gully",                "aliases": ["gully"],                      "category": "close_catching", "side": "off"},
    "ShortLeg":          {"name": "Short Leg",            "aliases": ["short leg","bat-pad"],        "category": "close_catching", "side": "leg"},
    "SillyPoint":        {"name": "Silly Point",          "aliases": ["silly point"],                "category": "close_catching", "side": "off"},
    "CatchingMidWicket": {"name": "Catching Mid-Wicket",  "aliases": ["catching mid wicket"],        "category": "close_catching", "side": "leg"},
    "BackwardPoint":     {"name": "Backward Point",       "aliases": ["backward point"],             "category": "infield",        "side": "off"},
    "Point":             {"name": "Point",                "aliases": ["point"],                      "category": "infield",        "side": "off"},
    "Cover":             {"name": "Cover",                "aliases": ["cover","cover point"],        "category": "infield",        "side": "off"},
    "ExtraCover":        {"name": "Extra Cover",          "aliases": ["extra cover"],                "category": "infield",        "side": "off"},
    "MidOff":            {"name": "Mid-Off",              "aliases": ["mid off","mid-off"],          "category": "infield",        "side": "off"},
    "MidOn":             {"name": "Mid-On",               "aliases": ["mid on","mid-on"],            "category": "infield",        "side": "leg"},
    "MidWicket":         {"name": "Mid-Wicket",           "aliases": ["mid wicket","mid-wicket"],    "category": "infield",        "side": "leg"},
    "ShortMidWicket":    {"name": "Short Mid-Wicket",     "aliases": ["short mid wicket"],           "category": "infield",        "side": "leg"},
    "SquareLeg":         {"name": "Square Leg",           "aliases": ["square leg"],                 "category": "infield",        "side": "leg"},
    "ShortThird":        {"name": "Short Third Man",      "aliases": ["short third"],                "category": "infield",        "side": "off"},
    "ShortFineLeg":      {"name": "Short Fine Leg",       "aliases": ["short fine leg"],             "category": "infield",        "side": "leg"},
    "Bowler":            {"name": "Bowler",               "aliases": ["bowler"],                     "category": "specialist_bowl","side": "straight"},
    "FineLeg":           {"name": "Fine Leg",             "aliases": ["fine leg"],                   "category": "boundary",       "side": "leg"},
    "DeepPoint":         {"name": "Deep Point",           "aliases": ["deep point"],                 "category": "boundary",       "side": "off"},
    "DeepBackwardPoint": {"name": "Deep Backward Point",  "aliases": ["deep backward point"],        "category": "boundary",       "side": "off"},
    "DeepCover":         {"name": "Deep Cover",           "aliases": ["deep cover"],                 "category": "boundary",       "side": "off"},
    "DeepExtraCover":    {"name": "Deep Extra Cover",     "aliases": ["deep extra cover"],           "category": "boundary",       "side": "off"},
    "LongOff":           {"name": "Long-Off",             "aliases": ["long off"],                   "category": "boundary",       "side": "off"},
    "LongOn":            {"name": "Long-On",              "aliases": ["long on"],                    "category": "boundary",       "side": "leg"},
    "DeepMidWicket":     {"name": "Deep Mid-Wicket",      "aliases": ["deep mid wicket","cow corner"],"category": "boundary",     "side": "leg"},
    "DeepSquareLeg":     {"name": "Deep Square Leg",      "aliases": ["deep square leg"],            "category": "boundary",       "side": "leg"},
    "DeepBackwardSquare":{"name": "Deep Backward Square", "aliases": ["backward square leg"],        "category": "boundary",       "side": "leg"},
    "ThirdMan":          {"name": "Third Man",            "aliases": ["third man"],                  "category": "boundary",       "side": "off"},
}

# ─────────────────────────────────────────────────────────────────────────────
# COACHING TIPS per bowling type
# ─────────────────────────────────────────────────────────────────────────────
BOWLING_TIPS = {
    "fast": [
        "Use the new ball with 3 slips and gully in the powerplay (+X off-side cordon).",
        "Move to cutters and wide yorkers in the death — keep the blockhole as your primary weapon.",
        "Bowl full to avoid giving width — back-of-a-length invites the pull."
    ],
    "medium_pace": [
        "Reverse swing becomes your weapon after 30 overs in ODIs.",
        "Vary your pace by 10–15 km/h — batters time based on expectation.",
        "Middle-over cutters on dry pitches can generate sharp deviation."
    ],
    "off_spin": [
        "Attack RHB with short leg and catching mid-wicket — the bat-pad is your primary dismissal.",
        "Bowl into the rough outside off stump to RHB for maximum turn through the gate.",
        "Toss it up and invite the drive — the outside edge to slip is gold."
    ],
    "leg_spin": [
        "The googly is your stock ball in limited overs — disguise is everything.",
        "Deep cover and long-off must be in place before you toss one up.",
        "Target the corridor outside off — let the turn beat the outside edge."
    ],
    "left_arm_spin": [
        "Bowl over the wicket to RHB — angle into the body and turn away.",
        "Short leg and square leg form your catching triangle.",
        "Use the crease width to vary the angle of entry."
    ],
    "left_arm_chinaman": [
        "The wrong-un (arm ball) is your key variation — hide it well.",
        "Like leg-spin: deep cover and long-off are non-negotiable.",
        "Attack around the wicket to RHB — turns sharply away from a full length."
    ],
}
