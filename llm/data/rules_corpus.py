"""
rules_corpus.py
Comprehensive foundational corpus of ICC Standard Playing Conditions and MCC Laws of Cricket.
Provides the continuous pre-training text for Test, ODI, and T20 match governance,
fielding restrictions, powerplay regulations, DRS ballistics, and illegal play laws.
"""

def get_complete_rules_corpus() -> str:
    return """
<|test_match|> ICC TEST MATCH STANDARD PLAYING CONDITIONS & MCC LAWS

SECTION 1: TEST MATCH FIELDING RESTRICTIONS AND STRATEGY
In Test Match cricket, matches are scheduled for five consecutive days consisting of 90 scheduled overs per day (450 overs total across 4 innings).
Unlike limited-overs formats, Test cricket places NO restrictions on the number of fielders permitted outside the 30-yard fielding circle at any stage of the game.
The fielding captain is permitted to set attacking cordons without limit, including:
- Up to five slips and a gully on the off-side.
- Leg-slip and short leg (bat-pad) on the leg-side.
- Silly point, silly mid-off, and short cover for bat-pad catches against turning spin.
The only universal fielding restriction under Law 28.4 states that no more than two fielders may be positioned on the leg-side behind the popping crease at the instant of the bowler's delivery (the 'two behind square' rule), originally enacted to outlaw dangerous Bodyline tactics.

SECTION 2: TEST MATCH BALL, PITCH DETERIORATION & FOLLOW-ON RULES
- Match Balls: The red leather ball (or pink ball for Day/Night Tests) is used. The fielding side has the option of taking a brand-new second ball after 80 overs have been bowled with the old ball.
- Pitch Wear & Ballistics: On Day 1, pitches exhibit high moisture content, living grass cover, and significant seam movement. By Day 3, the surface flattens, producing optimal batting conditions. By Day 4 and Day 5, the pitch degrades through repeated footmarks, producing dry cracks, variable bounce, sharp reverse swing when the ball is scuffed on one hemisphere, and pronounced turn for spin bowlers exploiting bowler footmarks outside the right-hander's off-stump.
- Follow-on Regulations: In a five-day Test match, if the team batting first leads by 200 runs or more after both teams have completed their first innings, the captain of the leading side has the option to enforce the follow-on, compelling the opposing side to bat their second innings immediately.

---

<|odi_match|> ICC ONE DAY INTERNATIONAL (ODI) PLAYING CONDITIONS

SECTION 3: ODI 50-OVER FORMAT & MANDATORY FIELDING RESTRICTIONS
An ODI match consists of 50 overs per side. The fielding restrictions are strictly segmented into three distinct Powerplay phases:
1. Mandatory Powerplay 1 (Overs 1 to 10):
   - A maximum of two (2) fielders are permitted outside the 30-yard fielding circle.
   - Designed to encourage fast-scoring off-side drives, pull shots, and aggressive pace bowling with slips.
2. Powerplay 2 (Overs 11 to 40):
   - A maximum of four (4) fielders are permitted outside the 30-yard fielding circle.
   - Teams build innings momentum through strike rotation, singles, and defensive field settings.
3. Powerplay 3 (Overs 41 to 50):
   - A maximum of five (5) fielders are permitted outside the 30-yard fielding circle.
   - Fielders protect boundary fence corridors (Long-on, Long-off, Deep Mid-wicket, Deep Point, Deep Fine Leg) against death-over yorkers and slower ball variations.
- Bowler Allocation: No bowler may bowl more than ten (10) overs in an uninterrupted 50-over innings.
- Balls Used: Two new white Kookaburra balls are used simultaneously from alternate ends throughout the innings, meaning each ball is used for 25 overs, significantly suppressing late reverse swing while preserving visibility under floodlights.

---

<|t20_match|> ICC TWENTY20 INTERNATIONAL (T20I) PLAYING CONDITIONS

SECTION 4: T20 20-OVER FORMAT, FIELDING PRESSURE & PENALTY CONSTRAINTS
In T20 cricket, each team bats for twenty (20) overs. The format demands hyper-aggressive boundary hitting and deceptive bowling variations.
1. Mandatory Powerplay (Overs 1 to 6):
   - Exactly two (2) fielders are permitted outside the 30-yard fielding circle.
   - Attackers target the infield elevation while bowlers employ wide yorkers, knuckleballs, and off-pace off-cutters.
2. Non-Powerplay Phase (Overs 7 to 20):
   - A maximum of five (5) fielders are permitted outside the 30-yard circle at all times.
- Bowler Over Limit: No bowler may deliver more than four (4) overs.
- Over Rate Penalty Clock: If the fielding team fails to begin the final over of the innings by the scheduled cut-off time, they are penalized for the remaining overs: one fewer fielder is allowed outside the circle (maximum 4 fielders outside the ring instead of 5), creating vulnerable boundary gaps.
- Tie-Breaker Protocol: In the event of tied runs at the completion of 20 overs, the winner is decided by a Super Over (one over per team, three batters nominated, two wickets per side). If the Super Over is tied, subsequent Super Overs are contested until an outright winner is determined.

---

SECTION 5: UNIVERSAL LAWS OF CRICKET & DECISION REVIEW SYSTEM (DRS)
1. Free Hit Rule on No-Balls:
   - In ODIs and T20Is, any front-foot or back-foot no-ball results in a Free Hit delivery on the following ball.
   - On a Free Hit, the batter cannot be dismissed by any means other than Run Out, Obstructing the Field, or Hit the Ball Twice. The fielding captain cannot change field positions unless the batters switched ends during the preceding delivery.
2. DRS Ball Tracking & Hawk-Eye Biomechanics:
   - Ball Pitching: Ball must pitch in-line with the stumps or on the off-side. A ball pitching outside leg-stump is automatically Not Out for LBW.
   - Impact Location: The ball must make primary contact with the batter's pad in-line with the stumps (unless no shot is offered, in which case impact outside off-stump is eligible for dismissal).
   - Wicket Zone Projection: Hawk-Eye's ballistic polynomial predicts whether the center of the ball would hit any part of the stumps. If more than 50% of the ball diameter misses, it is Not Out. If between 1% and 50% clips the outer stump or bails, it is designated 'Umpire's Call'.
3. Law 41 - Unfair Play:
   - Bowlers are prohibited from delivering dangerous high full-pitches (beamers) above waist height of the striker standing in their normal crease position.
   - Fielders must not deliberately distract or deceive the batter (fake fielding). A five-run penalty is awarded to the batting side upon breach.
<|endoftext|>
"""

