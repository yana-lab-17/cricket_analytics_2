"""
game_server.py
Unified Game Server for 3D Cricket Simulation with Advanced Ballistics,
Cognitive Neuroscience Engine, Captain's Academy Challenge Mode,
and Match Analytics (Wagon Wheel, Pitch Map, Expected Runs Prevented xRP).
"""

import asyncio
import json
import logging
import math
import os
import sys
import base64
import hashlib
import struct
from http.server import SimpleHTTPRequestHandler, HTTPServer
import threading
from typing import Dict, List, Tuple, Any, Set

from backend.bowling_engine import BowlingEngine
from backend.batter_ai import BatterAI
from backend.fielding_sim import FieldingSimulationEngine
from backend.pedagogy import TacticalExplainer
from backend.neuro_engine import CricketNeuroEngine
from backend.academy import AcademyManager, ACADEMY_LEVELS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("CricketGameEngine")

# ─────────────────────────────────────────────────────────────────────────────
# FIELDING PRESETS
# ─────────────────────────────────────────────────────────────────────────────
GAME_FIELD_PRESETS = {
    "Powerplay Attack (Slips + Gully)": {
        "WicketKeeper": {"x": 0.0, "y": 1.0, "z": -20.0},
        "Slip_1": {"x": 3.2, "y": 1.0, "z": -21.0},
        "Slip_2": {"x": 6.2, "y": 1.0, "z": -20.2},
        "Gully": {"x": 13.5, "y": 1.0, "z": -10.0},
        "Point": {"x": 23.5, "y": 1.0, "z": 2.0},
        "Cover": {"x": 21.0, "y": 1.0, "z": 12.0},
        "MidOff": {"x": 11.0, "y": 1.0, "z": 23.0},
        "MidOn": {"x": -11.0, "y": 1.0, "z": 23.0},
        "MidWicket": {"x": -20.0, "y": 1.0, "z": 10.0},
        "Bowler": {"x": 0.0, "y": 1.0, "z": 18.0},
        "FineLeg": {"x": -28.0, "y": 1.0, "z": -42.0},
    },
    "T20 Death Yorker Lock (5 on Boundary)": {
        "WicketKeeper": {"x": 0.0, "y": 1.0, "z": -14.0},
        "ShortThird": {"x": 16.0, "y": 1.0, "z": -12.0},
        "Point": {"x": 24.0, "y": 1.0, "z": 0.0},
        "ExtraCover": {"x": 19.0, "y": 1.0, "z": 16.0},
        "MidWicket": {"x": -20.0, "y": 1.0, "z": 11.0},
        "Bowler": {"x": 0.0, "y": 1.0, "z": 18.0},
        "DeepCover": {"x": 50.0, "y": 1.0, "z": 30.0},
        "DeepBackwardPoint": {"x": 52.0, "y": 1.0, "z": -14.0},
        "LongOff": {"x": 18.0, "y": 1.0, "z": 62.0},
        "LongOn": {"x": -18.0, "y": 1.0, "z": 62.0},
        "DeepMidWicket": {"x": -52.0, "y": 1.0, "z": 22.0},
    },
    "Spin Trap (Close Catchers + Boundary Traps)": {
        "WicketKeeper": {"x": 0.0, "y": 1.0, "z": -4.2},
        "Slip_1": {"x": 2.6, "y": 1.0, "z": -6.2},
        "ShortLeg": {"x": -5.2, "y": 1.0, "z": 3.8},
        "Point": {"x": 23.0, "y": 1.0, "z": 0.0},
        "Cover": {"x": 21.0, "y": 1.0, "z": 10.0},
        "CatchingMidWicket": {"x": -14.0, "y": 1.0, "z": 11.0},
        "Bowler": {"x": 0.0, "y": 1.0, "z": 16.0},
        "SquareLeg": {"x": -21.0, "y": 1.0, "z": -2.0},
        "DeepMidWicket": {"x": -52.0, "y": 1.0, "z": 20.0},
        "LongOn": {"x": -18.0, "y": 1.0, "z": 60.0},
        "LongOff": {"x": 18.0, "y": 1.0, "z": 60.0},
    },
    "Balanced One-Day Ring": {
        "WicketKeeper": {"x": 0.0, "y": 1.0, "z": -15.0},
        "Slip_1": {"x": 3.0, "y": 1.0, "z": -16.0},
        "Point": {"x": 24.0, "y": 1.0, "z": 0.0},
        "Cover": {"x": 22.0, "y": 1.0, "z": 11.0},
        "MidOff": {"x": 11.0, "y": 1.0, "z": 23.0},
        "MidOn": {"x": -11.0, "y": 1.0, "z": 23.0},
        "MidWicket": {"x": -20.0, "y": 1.0, "z": 10.0},
        "Bowler": {"x": 0.0, "y": 1.0, "z": 18.0},
        "DeepCover": {"x": 50.0, "y": 1.0, "z": 25.0},
        "DeepMidWicket": {"x": -50.0, "y": 1.0, "z": 24.0},
        "FineLeg": {"x": -28.0, "y": 1.0, "z": -42.0},
    }
}

LHB_SWAP_NAMES = {
    "Point": "SquareLeg",
    "SquareLeg": "Point",
    "Cover": "MidWicket",
    "MidWicket": "Cover",
    "ExtraCover": "ShortMidWicket",
    "ShortMidWicket": "ExtraCover",
    "MidOff": "MidOn",
    "MidOn": "MidOff",
    "DeepCover": "DeepMidWicket",
    "DeepMidWicket": "DeepCover",
    "LongOff": "LongOn",
    "LongOn": "LongOff",
    "Gully": "ShortLeg",
    "ShortLeg": "Gully",
    "FineLeg": "ThirdMan",
    "ThirdMan": "FineLeg",
    "ShortThird": "ShortFineLeg",
    "ShortFineLeg": "ShortThird"
}


class CricketGameState:
    """Manages the full game state, physics simulators, and match scoreboard."""

    def __init__(self):
        self.bowling_engine = BowlingEngine()
        self.batter_ai = BatterAI()
        self.fielding_sim = FieldingSimulationEngine()
        self.explainer = TacticalExplainer()
        self.neuro = CricketNeuroEngine()
        self.academy = AcademyManager()

        self.current_preset = "Powerplay Attack (Slips + Gully)"
        self.fielders = {n: dict(p) for n, p in GAME_FIELD_PRESETS[self.current_preset].items()}
        self.batter_handedness = "RHB"
        self.pitch_condition = "day_3_flat"  # day_1_green, day_3_flat, day_5_dusty
        self.game_mode = "free_play"  # free_play, academy

        # Bowling configuration
        self.bowling_config = {
            "bowling_type": "fast",
            "speed_kmh": 142.0,
            "line": "outside_off",
            "length": "good_length",
            "variation": "outswing"
        }

        # Scoreboard & Match Analytics Suite
        self.balls_bowled = 0
        self.runs_conceded = 0
        self.wickets_taken = 0
        self.dots_bowled = 0
        self.total_xrp = 0.0
        self.wagon_wheel = []  # [{shot_name, angle, distance, runs, outcome}]
        self.pitch_map = []    # [{x, z, length, line}]
        self.last_result = None

    def set_preset(self, preset_name: str):
        if preset_name in GAME_FIELD_PRESETS:
            self.current_preset = preset_name
            raw = {n: dict(p) for n, p in GAME_FIELD_PRESETS[preset_name].items()}
            if self.batter_handedness == "LHB":
                self.fielders = self._mirror_for_lhb(raw)
            else:
                self.fielders = raw

    def update_fielder(self, name: str, x: float, z: float):
        if name in self.fielders:
            dist = math.sqrt(x * x + z * z)
            if dist > 68.0:
                scale = 67.5 / dist
                x *= scale
                z *= scale
            self.fielders[name]["x"] = round(float(x), 2)
            self.fielders[name]["z"] = round(float(z), 2)

    def set_handedness(self, hand: str):
        hand = hand.upper()
        if hand in ("RHB", "LHB") and hand != self.batter_handedness:
            self.batter_handedness = hand
            self.fielders = self._mirror_for_lhb(self.fielders)

    def set_pitch_condition(self, condition: str):
        if condition in ("day_1_green", "day_3_flat", "day_5_dusty"):
            self.pitch_condition = condition

    def _mirror_for_lhb(self, field: dict) -> dict:
        mirrored = {}
        for name, pos in field.items():
            new_x = round(-pos["x"], 2)
            new_z = pos["z"]
            new_name = LHB_SWAP_NAMES.get(name, name)
            mirrored[new_name] = {"x": new_x, "y": pos.get("y", 1.0), "z": new_z}
        return mirrored

    def simulate_ball(self) -> dict:
        """Executes full delivery + reactive shot + pursuit + outcome + neuroscience."""
        self.balls_bowled += 1
        is_l = (self.batter_handedness == "LHB")

        # 1. Simulate delivery
        delivery = self.bowling_engine.simulate_delivery(
            bowling_type=self.bowling_config["bowling_type"],
            speed_kmh=self.bowling_config["speed_kmh"],
            line=self.bowling_config["line"],
            length=self.bowling_config["length"],
            variation=self.bowling_config["variation"],
            pitch_condition=self.pitch_condition,
            is_lhb=is_l
        )

        # 2. Reactive batter AI
        shot = self.batter_ai.evaluate_and_play_shot(
            delivery_info=delivery,
            fielders=self.fielders,
            is_lhb=is_l
        )

        # 3. Fielder pursuit & outcome
        pursuit = self.fielding_sim.simulate_pursuit(
            shot_info=shot,
            fielders=self.fielders,
            is_bowled=(shot["shot_type"] == "bowled")
        )

        # 4. Educational coaching commentary & Neuroscience analysis
        explanation = self.explainer.explain_play(
            delivery=delivery,
            shot=shot,
            pursuit=pursuit,
            fielders=self.fielders
        )

        neuro_metrics = self.neuro.analyze_play(
            delivery=delivery,
            shot=shot,
            pursuit=pursuit,
            fielders=self.fielders
        )

        # 5. Update scoreboard & analytics
        runs = pursuit["runs_scored"]
        self.runs_conceded += runs
        if "WICKET" in pursuit["outcome"]:
            self.wickets_taken += 1
        if runs == 0:
            self.dots_bowled += 1
        self.total_xrp += neuro_metrics["xrp"]

        # Record Wagon Wheel & Pitch Map
        pitch_pt = delivery.get("pitch_point", {"x": 0.4, "z": 6.8})
        self.pitch_map.append({
            "x": pitch_pt["x"],
            "z": pitch_pt["z"],
            "line": self.bowling_config["line"],
            "length": self.bowling_config["length"]
        })

        last_pt = shot["trajectory"][-1] if shot["trajectory"] else {"x": 0, "z": 0}
        dist = math.sqrt(last_pt["x"] ** 2 + last_pt["z"] ** 2)
        self.wagon_wheel.append({
            "shot_name": shot["shot_name"],
            "angle": shot["spray_azimuth"],
            "distance": round(dist, 1),
            "runs": runs,
            "outcome": pursuit["outcome"]
        })

        # Academy check
        academy_status = None
        if self.game_mode == "academy":
            academy_status = self.academy.record_play(pursuit["outcome"], runs)

        self.last_result = {
            "outcome": pursuit["outcome"],
            "headline": pursuit["outcome_headline"],
            "runs": runs,
            "shot_name": shot["shot_name"],
            "speed_kmh": delivery["speed_kmh"],
            "xrp": neuro_metrics["xrp"]
        }

        return {
            "delivery": delivery,
            "shot": shot,
            "pursuit": pursuit,
            "coaching_tip": explanation,
            "neuro": neuro_metrics,
            "scoreboard": self.get_scoreboard(),
            "academy_status": academy_status
        }

    def get_scoreboard(self) -> dict:
        overs = f"{self.balls_bowled // 6}.{self.balls_bowled % 6}"
        economy = round((self.runs_conceded / (self.balls_bowled / 6.0)), 2) if self.balls_bowled > 0 else 0.0
        return {
            "balls_bowled": self.balls_bowled,
            "overs": overs,
            "runs_conceded": self.runs_conceded,
            "wickets_taken": self.wickets_taken,
            "dots_bowled": self.dots_bowled,
            "economy": economy,
            "total_xrp": round(self.total_xrp, 1),
            "pitch_condition": self.pitch_condition,
            "game_mode": self.game_mode,
            "last_result": self.last_result
        }

    def get_match_analytics(self) -> dict:
        return {
            "scoreboard": self.get_scoreboard(),
            "wagon_wheel": self.wagon_wheel,
            "pitch_map": self.pitch_map,
            "total_xrp": round(self.total_xrp, 1)
        }

    def build_state_payload(self) -> dict:
        return {
            "current_preset": self.current_preset,
            "batter_handedness": self.batter_handedness,
            "pitch_condition": self.pitch_condition,
            "game_mode": self.game_mode,
            "fielders": self.fielders,
            "bowling_config": self.bowling_config,
            "scoreboard": self.get_scoreboard(),
            "academy_level": self.academy.get_current_level(),
            "available_presets": list(GAME_FIELD_PRESETS.keys()),
            "academy_levels": ACADEMY_LEVELS
        }


# ─────────────────────────────────────────────────────────────────────────────
# RFC 6455 WEBSOCKET PROTOCOL IMPLEMENTATION (STANDARD LIBRARY ASYNCIO)
# ─────────────────────────────────────────────────────────────────────────────
WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

def create_ws_accept(sec_key: str) -> str:
    combined = sec_key.strip() + WS_GUID
    return base64.b64encode(hashlib.sha1(combined.encode()).digest()).decode()

def encode_ws_frame(message: str) -> bytes:
    payload = message.encode("utf-8")
    length = len(payload)
    if length <= 125:
        header = struct.pack("!BB", 0x81, length)
    elif length <= 65535:
        header = struct.pack("!BBH", 0x81, 126, length)
    else:
        header = struct.pack("!BBQ", 0x81, 127, length)
    return header + payload

def decode_ws_frame(data: bytearray) -> Tuple[str, int]:
    if len(data) < 2:
        return "", 0
    second = data[1]
    is_masked = bool(second & 0x80)
    payload_len = second & 0x7F

    offset = 2
    if payload_len == 126:
        if len(data) < 4: return "", 0
        payload_len = struct.unpack("!H", data[2:4])[0]
        offset = 4
    elif payload_len == 127:
        if len(data) < 10: return "", 0
        payload_len = struct.unpack("!Q", data[2:10])[0]
        offset = 10

    if is_masked:
        if len(data) < offset + 4: return "", 0
        mask = data[offset:offset+4]
        offset += 4
        if len(data) < offset + payload_len: return "", 0
        payload = bytearray(data[offset:offset+payload_len])
        for i in range(len(payload)):
            payload[i] ^= mask[i % 4]
        return payload.decode("utf-8", errors="ignore"), offset + payload_len
    else:
        if len(data) < offset + payload_len: return "", 0
        payload = data[offset:offset+payload_len]
        return payload.decode("utf-8", errors="ignore"), offset + payload_len


class PureAsyncWebSocketServer:
    """Zero-dependency RFC 6455 WebSocket Server."""

    def __init__(self, game_state: CricketGameState, host: str = "0.0.0.0", port: int = 8765):
        self.state = game_state
        self.host = host
        self.port = port
        self.clients = set()

    async def broadcast(self, payload: dict):
        if not self.clients:
            return
        frame = encode_ws_frame(json.dumps(payload))
        to_remove = set()
        for writer in self.clients:
            try:
                writer.write(frame)
                await writer.drain()
            except Exception:
                to_remove.add(writer)
        self.clients -= to_remove

    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        handshake_data = await reader.read(4096)
        text = handshake_data.decode("utf-8", errors="ignore")
        sec_key = None
        for line in text.split("\r\n"):
            if line.lower().startswith("sec-websocket-key:"):
                sec_key = line.split(":", 1)[1].strip()
                break

        if not sec_key:
            writer.close()
            return

        accept_key = create_ws_accept(sec_key)
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept_key}\r\n\r\n"
        )
        writer.write(response.encode())
        await writer.drain()

        self.clients.add(writer)
        logger.info(f"Client connected. Active clients: {len(self.clients)}")

        try:
            init_frame = encode_ws_frame(json.dumps({
                "action": "state_sync",
                "state": self.state.build_state_payload()
            }))
            writer.write(init_frame)
            await writer.drain()
        except Exception:
            self.clients.discard(writer)
            writer.close()
            return

        buffer = bytearray()
        try:
            while True:
                chunk = await reader.read(4096)
                if not chunk:
                    break
                buffer.extend(chunk)

                while buffer:
                    msg, consumed = decode_ws_frame(buffer)
                    if consumed == 0:
                        break
                    buffer = buffer[consumed:]
                    if msg:
                        await self.process_message(msg, writer)
        except Exception as e:
            logger.debug(f"Client disconnected: {e}")
        finally:
            self.clients.discard(writer)
            writer.close()
            logger.info("Client disconnected.")

    async def process_message(self, raw_msg: str, writer: asyncio.StreamWriter):
        try:
            data = json.loads(raw_msg)
        except Exception:
            return

        action = data.get("action", "")

        # ── Move Fielder (Drag & Drop) ──────────────────────────────────
        if action == "update_fielder":
            name = data.get("name")
            x = data.get("x")
            z = data.get("z")
            if name and x is not None and z is not None:
                self.state.update_fielder(name, float(x), float(z))
                await self.broadcast({
                    "action": "fielder_moved",
                    "name": name,
                    "x": self.state.fielders[name]["x"],
                    "z": self.state.fielders[name]["z"]
                })

        # ── Set Preset ─────────────────────────────────────────────────
        elif action == "set_preset":
            preset = data.get("preset", "")
            self.state.set_preset(preset)
            await self.broadcast({
                "action": "state_sync",
                "state": self.state.build_state_payload()
            })

        # ── Set Pitch Condition ─────────────────────────────────────────
        elif action == "set_pitch_condition":
            cond = data.get("condition", "day_3_flat")
            self.state.set_pitch_condition(cond)
            await self.broadcast({
                "action": "pitch_condition_updated",
                "condition": self.state.pitch_condition
            })

        # ── Set Bowling Config ──────────────────────────────────────────
        elif action == "set_bowling_config":
            cfg = data.get("config", {})
            for k in ("bowling_type", "speed_kmh", "line", "length", "variation"):
                if k in cfg:
                    self.state.bowling_config[k] = cfg[k]
            await self.broadcast({
                "action": "bowling_config_updated",
                "config": self.state.bowling_config
            })

        # ── Set Handedness (RHB / LHB) ──────────────────────────────────
        elif action == "set_handedness":
            hand = data.get("handedness", "RHB")
            self.state.set_handedness(hand)
            await self.broadcast({
                "action": "state_sync",
                "state": self.state.build_state_payload()
            })

        # ── Start Academy Level ─────────────────────────────────────────
        elif action == "start_academy_level":
            level_id = data.get("level_id", "level_1")
            lvl = self.state.academy.start_level(level_id)
            self.state.game_mode = "academy"
            # Apply recommended preset and bowling
            if "default_field" in lvl:
                self.state.set_preset(lvl["default_field"])
            if "default_bowling" in lvl:
                self.state.bowling_config.update(lvl["default_bowling"])
            await self.broadcast({
                "action": "state_sync",
                "state": self.state.build_state_payload()
            })

        # ── Switch Game Mode ────────────────────────────────────────────
        elif action == "set_game_mode":
            self.state.game_mode = data.get("mode", "free_play")
            await self.broadcast({
                "action": "state_sync",
                "state": self.state.build_state_payload()
            })

        # ── BOWL BALL (Game Simulation Trigger) ─────────────────────────
        elif action == "bowl_delivery":
            result = self.state.simulate_ball()
            await self.broadcast({
                "action": "delivery_result",
                "data": result
            })

        # ── Get Match Analytics Suite (Wagon Wheel, Pitch Map, xRP) ─────
        elif action == "get_match_analytics":
            analytics = self.state.get_match_analytics()
            frame = encode_ws_frame(json.dumps({
                "action": "match_analytics_report",
                "analytics": analytics
            }))
            writer.write(frame)
            await writer.drain()

        # ── Reset Scoreboard ───────────────────────────────────────────
        elif action == "reset_match":
            self.state.balls_bowled = 0
            self.state.runs_conceded = 0
            self.state.wickets_taken = 0
            self.state.dots_bowled = 0
            self.state.total_xrp = 0.0
            self.state.wagon_wheel.clear()
            self.state.pitch_map.clear()
            self.state.last_result = None
            await self.broadcast({
                "action": "state_sync",
                "state": self.state.build_state_payload()
            })

        # ── State Sync ─────────────────────────────────────────────────
        elif action == "get_state":
            frame = encode_ws_frame(json.dumps({
                "action": "state_sync",
                "state": self.state.build_state_payload()
            }))
            writer.write(frame)
            await writer.drain()

    async def start(self):
        server = await asyncio.start_server(self.handle_connection, self.host, self.port)
        logger.info(f"Cricket Game WebSocket Server running on ws://{self.host}:{self.port}")
        async with server:
            await server.serve_forever()


# ─────────────────────────────────────────────────────────────────────────────
# STATIC HTTP SERVER FOR PLAYCANVAS FRONTEND
# ─────────────────────────────────────────────────────────────────────────────
def run_http_server(root_dir: str, default_port: int = 8080):
    class QuietHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=root_dir, **kwargs)
        def log_message(self, format, *args):
            pass

    class ReusableHTTPServer(HTTPServer):
        allow_reuse_address = True

    for p in [default_port, 8081, 8000, 8888]:
        try:
            httpd = ReusableHTTPServer(("0.0.0.0", p), QuietHandler)
            logger.info(f"Cricket 3D WebGL Frontend running at http://localhost:{p}")
            httpd.serve_forever()
            break
        except OSError:
            continue


def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    state = CricketGameState()

    http_thread = threading.Thread(target=run_http_server, args=(root_dir, 8080), daemon=True)
    http_thread.start()

    ws_server = PureAsyncWebSocketServer(state, host="0.0.0.0", port=8765)
    try:
        asyncio.run(ws_server.start())
    except KeyboardInterrupt:
        logger.info("Game server stopped.")


if __name__ == "__main__":
    main()
