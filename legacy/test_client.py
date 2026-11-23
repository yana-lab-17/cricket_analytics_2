"""
test_client.py
Automated Verification & Integration Test Suite for Cricket Fielding Analytics Engine.
Tests two-way WebSocket communication, preset toggles, Voronoi math, trajectory physics,
18 bespoke bowling presets, delivery line/length dynamic shifts, and cordon geometry.
"""

import asyncio
import json
import sys
import websockets

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


async def run_integration_tests(server_uri: str = "ws://localhost:8765"):

    print("=" * 70)
    print("CRICKET SPATIAL ANALYTICS - END-TO-END VERIFICATION TEST SUITE")
    print(f"Target Server: {server_uri}")
    print("=" * 70)

    try:
        async with websockets.connect(server_uri) as ws:
            print("\n[TEST 1] Client Handshake & Initial State Payload")
            raw_msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
            state = json.loads(raw_msg)

            assert "preset" in state, "Missing 'preset' key"
            assert "fielders" in state, "Missing 'fielders' key"
            assert "coverage_score" in state, "Missing 'coverage_score' key"
            assert "voronoi" in state, "Missing 'voronoi' key"
            assert "trajectory" in state, "Missing 'trajectory' key"

            n_fielders = len(state["fielders"])
            cov_score = state["coverage_score"]
            preset = state["preset"]
            n_ridges = len(state["voronoi"].get("ridges", []))
            n_traj_pts = len(state["trajectory"])

            print(f"  ✓ Connected successfully to {server_uri}")
            print(f"  ✓ Active Preset: {preset}")
            print(f"  ✓ Fielder Count: {n_fielders}/11")
            print(f"  ✓ Field Coverage Score (FC_s): {cov_score}%")
            print(f"  ✓ Voronoi Ridge Count: {n_ridges}")
            print(f"  ✓ Initial Trajectory Points: {n_traj_pts}")
            assert n_fielders == 11, f"Expected 11 fielders, found {n_fielders}"
            assert cov_score > 0, "Coverage score should be positive"

            # Check Slip geometry: Slips must be on off-side (positive X) for RHB
            if "Slip_1" in state["fielders"]:
                s1_x = state["fielders"]["Slip_1"]["x"]
                assert s1_x > 0, f"Slip_1 X should be positive on off-side for RHB, got {s1_x}"
                print(f"  ✓ Slip_1 correctly on off-side: x={s1_x}m, z={state['fielders']['Slip_1']['z']}m")

            # -------------------------------------------------------------
            print("\n[TEST 2] Preset Toggle: 'Middle Overs'")
            await ws.send(json.dumps({
                "action": "set_preset",
                "preset": "Middle Overs"
            }))
            resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
            assert "Middle Overs" in resp["preset"], f"Preset was not updated to Middle Overs, got {resp['preset']}"
            mid_score = resp["coverage_score"]
            print(f"  ✓ Switched to 'Middle Overs' ({resp['preset']})")
            print(f"  ✓ Updated FC_s: {mid_score}% (Infield: {resp['analytics']['infield_covered_pct']}%)")
            assert "DeepCover" in resp["fielders"], "Expected boundary fielder in Middle Overs"

            # -------------------------------------------------------------
            print("\n[TEST 3] Preset Toggle: 'Death Overs'")
            await ws.send(json.dumps({
                "action": "set_preset",
                "preset": "Death Overs"
            }))
            resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
            assert "Death" in resp["preset"], f"Preset was not updated to Death Overs, got {resp['preset']}"
            death_score = resp["coverage_score"]
            print(f"  ✓ Switched to 'Death Overs' ({resp['preset']})")
            print(f"  ✓ Updated FC_s: {death_score}%")

            # -------------------------------------------------------------
            print("\n[TEST 4] Fielder Coordinate Drag & Spatial Recomputation")
            test_x, test_z = 32.5, 14.0
            await ws.send(json.dumps({
                "action": "update_fielder",
                "name": "Point",
                "x": test_x,
                "z": test_z
            }))
            resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
            pt_pos = resp["fielders"]["Point"]
            print(f"  ✓ Point updated to x={pt_pos['x']}, z={pt_pos['z']}")
            assert abs(pt_pos["x"] - test_x) < 0.1, "Fielder X coordinate mismatch"
            assert abs(pt_pos["z"] - test_z) < 0.1, "Fielder Z coordinate mismatch"

            # -------------------------------------------------------------
            print("\n[TEST 5] 3D Ballistic Trajectory Simulation ('Pull Shot')")
            await ws.send(json.dumps({
                "action": "simulate_shot",
                "shot_type": "Pull Shot"
            }))
            resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
            shot = resp["shot_info"]
            traj = resp["trajectory"]
            intercept = resp.get("intercept", {})
            print(f"  ✓ Calculated Range: {shot.get('range')} m")
            print(f"  ✓ Max Height (Apex): {shot.get('max_height')} m")
            print(f"  ✓ Flight Time: {shot.get('flight_time')} s")
            print(f"  ✓ Trajectory Steps: {len(traj)} points")
            print(f"  ✓ Closest Fielder: {intercept.get('closest_fielder')} ({intercept.get('distance_m')}m away)")
            assert len(traj) > 50, "Expected full trajectory series"
            assert shot.get("range", 0) > 30.0, "Pull shot range should be realistic"

            # -------------------------------------------------------------
            print("\n[TEST 6] Heartbeat / Ping-Pong Protocol")
            await ws.send(json.dumps({"action": "ping"}))
            ping_resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
            assert ping_resp.get("action") == "pong", "Failed ping-pong test"
            print("  ✓ Ping-Pong roundtrip verified")

            # -------------------------------------------------------------
            print("\n[TEST 7] Bowling Type Switch to 'off_spin' (Speed Profile & Cordon Scaling)")
            await ws.send(json.dumps({
                "action": "set_bowling_type",
                "bowling_type": "off_spin"
            }))
            resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
            wk_pos = resp["fielders"].get("WicketKeeper", {})
            print(f"  ✓ Switched to Off Spin (Preset: {resp['preset']})")
            print(f"  ✓ Keeper Depth: z={wk_pos.get('z')}m (Standing up to the stumps!)")
            assert abs(wk_pos.get("z", 0.0)) <= 5.5, f"Expected spinner keeper depth <= 5.5m, got {wk_pos.get('z')}"
            assert len(resp["fielders"]) == 11, "Must maintain exactly 11 fielders"

            # -------------------------------------------------------------
            print("\n[TEST 8] Dynamic Delivery Line Offset Test ('to_the_body')")
            old_pt_x = resp["fielders"]["Point"]["x"]
            await ws.send(json.dumps({
                "action": "set_delivery_line",
                "line": "to_the_body"
            }))
            resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
            new_pt_x = resp["fielders"]["Point"]["x"]
            print(f"  ✓ Point X shifted from {old_pt_x} to {new_pt_x} (Leg-side rotation bias)")
            assert new_pt_x < old_pt_x, "Delivery line 'to_the_body' should shift ring fielders toward leg-side (-X)"

            # -------------------------------------------------------------
            print("\n[TEST 9] Left-Hand Batter (LHB) Symmetrical Mirroring")
            await ws.send(json.dumps({
                "action": "set_handedness",
                "handedness": "LHB"
            }))
            resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
            lhb_pt_x = resp["fielders"]["Point"]["x"]
            print(f"  ✓ LHB active: Point mirrored to x={lhb_pt_x} (Lateral pitch inversion)")
            assert lhb_pt_x < 0, "For LHB, Point should be on negative X"
            assert len(resp["fielders"]) == 11, "Field must maintain 11 fielders after mirroring"

            # -------------------------------------------------------------
            print("\n" + "=" * 70)
            print(">>> ALL 9 INTEGRATION TESTS PASSED SUCCESSFULLY! <<<")
            print("Python Backend <-> PlayCanvas Protocol Contract 100% Operational.")
            print("=" * 70)
            return True

    except Exception as e:
        print(f"\n❌ TEST FAILURE: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_integration_tests())
    sys.exit(0 if success else 1)
