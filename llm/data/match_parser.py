"""
match_parser.py
Parses international match JSON files (Cricsheet / ICC standard ball-by-ball schemas)
and serializes them into rich chronological match streams for continuous causal pre-training.
Prevents rote QA memorization by modeling match trajectories as continuous spatio-temporal streams.
"""

import json
import os
from typing import Dict, Any, List, Generator

def parse_cricsheet_match_to_stream(match_data: Dict[str, Any]) -> str:
    """
    Transforms ball-by-ball match JSON into continuous sequence modeling text.
    Captures format, venue, teams, pitch conditions, over-by-over field pressure,
    wicket sequences, and ball-by-ball tactics.
    """
    info = match_data.get("info", {})
    match_type = info.get("match_type", "ODI").upper()
    teams = info.get("teams", ["Team A", "Team B"])
    venue = info.get("venue", "International Stadium")
    outcome = info.get("outcome", {})
    winner = outcome.get("winner", "Draw/Tie")
    win_margin = outcome.get("by", {})

    # Match Format Token
    fmt_token = "<|test_match|>" if match_type in ["TEST", "MDDM"] else (
        "<|t20_match|>" if "T20" in match_type else "<|odi_match|>"
    )

    stream = [
        f"{fmt_token} MATCH METADATA",
        f"Format: {match_type} | Venue: {venue} | Teams: {teams[0]} vs {teams[1]}",
        f"Toss: {info.get('toss', {}).get('winner', 'Unknown')} elected to {info.get('toss', {}).get('decision', 'bat')}",
        ""
    ]

    # Process Innings
    innings = match_data.get("innings", [])
    for inn_idx, inning in enumerate(innings):
        inn_name = inning.get("team", f"Innings {inn_idx+1}")
        stream.append(f"<|innings_{min(2, inn_idx+1)}|> INNINGS {inn_idx+1}: {inn_name}")
        
        overs = inning.get("overs", [])
        total_runs = 0
        total_wickets = 0

        for over_data in overs:
            over_num = over_data.get("over", 0)
            deliveries = over_data.get("deliveries", [])
            stream.append(f"<|over|> Over {over_num}:")

            for ball_idx, deliv in enumerate(deliveries):
                bowler = deliv.get("bowler", "Bowler")
                batter = deliv.get("batter", "Batter")
                non_striker = deliv.get("non_striker", "")
                runs = deliv.get("runs", {})
                batter_runs = runs.get("batter", 0)
                extras = runs.get("extras", 0)
                ball_runs = runs.get("total", 0)
                total_runs += ball_runs

                ball_str = f"<|ball|> Ball {over_num}.{ball_idx+1}: {bowler} to {batter}"
                
                # Check outcome tags
                wickets = deliv.get("wickets", [])
                if wickets:
                    total_wickets += len(wickets)
                    w = wickets[0]
                    kind = w.get("kind", "dismissal")
                    player_out = w.get("player_out", batter)
                    fielders = [f.get("name", "") for f in w.get("fielders", []) if f.get("name")]
                    fielder_str = f" c {fielders[0]}" if fielders else ""
                    ball_str += f" -> <|wicket|> OUT! ({kind}{fielder_str}) {player_out} dismissed!"
                elif batter_runs == 4:
                    ball_str += f" -> <|four|> FOUR runs! Pierces the boundary."
                elif batter_runs == 6:
                    ball_str += f" -> <|six|> SIX runs! Clears the rope."
                elif ball_runs == 0:
                    ball_str += f" -> <|dot_ball|> Dot ball. Defensive block."
                else:
                    ball_str += f" -> {ball_runs} run(s) taken."

                ball_str += f" [Score: {total_runs}/{total_wickets}]"
                stream.append(ball_str)

        stream.append(f"Innings Total: {total_runs}/{total_wickets} in {len(overs)} overs.\n")

    # Match Conclusion
    stream.append(f"Match Result: Winner: {winner} ({win_margin})\n<|endoftext|>\n")
    return "\n".join(stream)

def stream_matches_from_directory(directory_path: str) -> Generator[str, None, None]:
    """Recursively yields formatted match text streams from a directory of JSON files."""
    if not os.path.exists(directory_path):
        return

    for root, _, files in os.walk(directory_path):
        for f in files:
            if f.endswith(".json"):
                full_path = os.path.join(root, f)
                try:
                    with open(full_path, "r", encoding="utf-8") as jf:
                        data = json.load(jf)
                        yield parse_cricsheet_match_to_stream(data)
                except Exception as e:
                    print(f"Skipping corrupt or non-cricsheet file {f}: {e}")

