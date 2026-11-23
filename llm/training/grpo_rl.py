"""
grpo_rl.py
Reinforcement Learning via Group Relative Policy Optimization (GRPO) for NeuroSport-Cricket LLM.
Enables the model to learn autonomously through trial-and-error self-play inside our
3D cricket ballistics & neuroscience physics engine.

Reward Signals:
1. Outcome Reward: Wickets (+10), Dots (+4), Boundaries Conceded (-6), xRP (+1.5 * xRP).
2. Rule Legality Reward: Valid ICC field restrictions (+2), Illegal fields (-10 penalty).
3. Biophysical Accuracy Reward: Correctly calculated post-pitch decision window inside <|think|> (+3).
"""

import os
import copy
import re
import math
from typing import List, Dict, Any, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import AdamW
from tokenizers import Tokenizer

from llm.config import NeuroSportConfig
from llm.architecture.model import NeuroSportCricketLM
from llm.inference.generator import NeuroSportGenerator

# Import our underlying 3D game physics engines
from backend.game_server import CricketGameState, GAME_FIELD_PRESETS
from llm.data.neuro_cricket_synthesizer import NeuroCricketTransducer

class CricketRLEnvironment:
    """Simulates match scenarios and computes verifiable rewards based on physical ballistics."""
    def __init__(self):
        self.game = CricketGameState()

    def generate_random_scenario(self) -> Dict[str, Any]:
        """Generates dynamic match scenarios for RL policy rollouts."""
        scenarios = [
            {
                "format": "T20",
                "phase": "death_overs",
                "target_desc": "Defend 8 runs in the final over against an aggressive power-hitter.",
                "pitch_condition": "day_3_flat",
                "batter_hand": "RHB"
            },
            {
                "format": "ODI",
                "phase": "powerplay_1",
                "target_desc": "Take early wickets in Powerplay 1 (overs 1-10) with max 2 fielders outside the ring.",
                "pitch_condition": "day_1_green",
                "batter_hand": "RHB"
            },
            {
                "format": "TEST",
                "phase": "day_5_afternoon",
                "target_desc": "Break a stubborn partnership on a Day 5 dusty turning surface.",
                "pitch_condition": "day_5_dusty",
                "batter_hand": "LHB"
            }
        ]
        import random
        return random.choice(scenarios)

    def evaluate_action_in_physics(
        self,
        scenario: Dict[str, Any],
        proposed_speed: float,
        proposed_line: str,
        proposed_length: str,
        proposed_variation: str,
        proposed_preset: str,
        reasoned_decision_ms: float
    ) -> Dict[str, Any]:
        """Runs the action through the physical ballistics simulator to generate ground-truth reward."""
        self.game.pitch_condition = scenario["pitch_condition"]
        self.game.set_handedness(scenario["batter_hand"])
        self.game.set_preset(proposed_preset)
        self.game.bowling_config.update({
            "bowling_type": "fast" if proposed_speed > 115 else "off_spin",
            "speed_kmh": proposed_speed,
            "line": proposed_line,
            "length": proposed_length,
            "variation": proposed_variation
        })

        # Run full physics simulation
        result = self.game.simulate_ball()
        pursuit = result["pursuit"]
        neuro = result["neuro"]

        # 6. Verifiable Reward Calculation
        reward = 0.0
        outcome = pursuit["outcome"]

        # A. Game outcome reward
        if outcome in ["WICKET_CAUGHT", "WICKET_BOWLED"]:
            reward += 10.0
        elif outcome == "DOT_BALL":
            reward += 4.0
        elif outcome == "SINGLE":
            reward += 1.0
        elif outcome in ["FOUR", "SIX"]:
            reward -= 6.0

        # B. xRP Reward
        reward += neuro["xrp"] * 1.5

        # C. Rule Compliance (e.g. Powerplay 1 max 2 outside 30yd circle)
        num_deep_fielders = sum(1 for p in self.game.fielders.values() if math.sqrt(p["x"]**2 + p["z"]**2) > 27.43)
        if scenario["phase"] == "powerplay_1" and num_deep_fielders > 2:
            reward -= 10.0 # Illegal field penalty!
        else:
            reward += 2.0  # Legality bonus

        # D. Biophysical calculation accuracy inside <|think|>
        true_decision_ms = neuro["decision_window_ms"]
        if abs(reasoned_decision_ms - true_decision_ms) <= 25.0:
            reward += 3.0 # Accurate biophysical reasoning reward

        return {
            "reward": reward,
            "outcome": outcome,
            "runs": pursuit["runs_scored"],
            "xrp": neuro["xrp"],
            "true_decision_ms": true_decision_ms
        }


class GRPOTrainer:
    """Group Relative Policy Optimization (GRPO) Trainer for Self-Learning Cricket LLM."""
    def __init__(
        self,
        model: NeuroSportCricketLM,
        tokenizer: Tokenizer,
        lr: float = 2e-5,
        beta_kl: float = 0.04,
        clip_eps: float = 0.2,
        group_size: int = 4, # G = 4 rollouts per prompt
        device: str = "cuda"
    ):
        self.model = model.to(device)
        self.ref_model = copy.deepcopy(model).to(device)
        self.ref_model.eval()
        for p in self.ref_model.parameters():
            p.requires_grad = False

        self.tokenizer = tokenizer
        self.optimizer = AdamW(self.model.parameters(), lr=lr)
        self.env = CricketRLEnvironment()
        self.beta_kl = beta_kl
        self.clip_eps = clip_eps
        self.group_size = group_size
        self.device = device

    def parse_action_from_text(self, text: str) -> Tuple[float, str, str, str, str, float]:
        """Parses proposed tactical parameters and reasoned decision ms from model generation."""
        speed = 142.0
        line = "outside_off"
        length = "good_length"
        var = "outswing"
        preset = "Powerplay Attack (Slips + Gully)"
        decision_ms = 220.0

        # Extract speed
        m_speed = re.search(r"(\d{2,3})\s*km/h", text, re.IGNORECASE)
        if m_speed:
            speed = float(m_speed.group(1))

        # Extract line
        for l in ["outside_off", "off_stump", "middle_stump", "leg_stump"]:
            if l.replace("_", " ") in text.lower():
                line = l
                break

        # Extract length
        for ln in ["yorker", "bouncer", "good_length", "full"]:
            if ln.replace("_", " ") in text.lower():
                length = ln
                break

        # Extract reasoned decision window
        m_dec = re.search(r"decision\s*(?:window|ms)?[:=]?\s*(\d{2,3})", text, re.IGNORECASE)
        if m_dec:
            decision_ms = float(m_dec.group(1))

        return speed, line, length, var, preset, decision_ms

    def train_step(self, num_iterations: int = 5):
        """Runs GRPO self-play iterations."""
        self.model.train()
        print(f"\n======================================================================")
        print(f"🤖 STARTING GRPO REINFORCEMENT LEARNING SELF-PLAY ({num_iterations} steps)")
        print(f"======================================================================")

        for step in range(num_iterations):
            scenario = self.env.generate_random_scenario()
            prompt = (
                f"<|think|>\n"
                f"Scenario: {scenario['format']} {scenario['phase']}. {scenario['target_desc']}\n"
                f"Pitch: {scenario['pitch_condition']}, Batter: {scenario['batter_hand']}.\n"
                f"Formulate bowling plan (speed, line, length) and calculate post-pitch decision window.\n"
            )

            # Sample group of G candidate rollouts
            generator = NeuroSportGenerator(self.model, self.tokenizer, device=self.device)
            group_texts = []
            group_rewards = []

            for g in range(self.group_size):
                gen_text = generator.generate(prompt=prompt, max_new_tokens=100, temperature=0.85)
                group_texts.append(gen_text)

                speed, line, length, var, preset, dec_ms = self.parse_action_from_text(gen_text)
                sim_res = self.env.evaluate_action_in_physics(
                    scenario=scenario,
                    proposed_speed=speed,
                    proposed_line=line,
                    proposed_length=length,
                    proposed_variation=var,
                    proposed_preset=preset,
                    reasoned_decision_ms=dec_ms
                )
                group_rewards.append(sim_res["reward"])

            # Compute relative advantages within group: A_i = (r_i - mean) / (std + eps)
            rewards_tensor = torch.tensor(group_rewards, dtype=torch.float32, device=self.device)
            mean_r = rewards_tensor.mean()
            std_r = rewards_tensor.std() + 1e-5
            advantages = (rewards_tensor - mean_r) / std_r

            print(
                f"RL Step {step+1}/{num_iterations} | "
                f"Scenario: {scenario['format']} ({scenario['phase']}) | "
                f"Rewards: {[round(r, 1) for r in group_rewards]} | "
                f"Mean Reward: {mean_r.item():.2f}"
            )

            # Policy Gradient Update using GRPO
            total_loss = 0.0
            enc_prompt = self.tokenizer.encode(prompt).ids

            for i in range(self.group_size):
                enc_out = self.tokenizer.encode(group_texts[i]).ids
                full_ids = torch.tensor([enc_prompt + enc_out], dtype=torch.long, device=self.device)
                labels = torch.tensor([[-100] * len(enc_prompt) + enc_out], dtype=torch.long, device=self.device)

                # Active policy logits
                logits = self.model(full_ids)["logits"]
                shift_logits = logits[..., :-1, :].contiguous()
                shift_labels = labels[..., 1:].contiguous()
                log_probs = -F.cross_entropy(shift_logits.view(-1, self.model.config.vocab_size), shift_labels.view(-1), ignore_index=-100)

                # Reference policy logits for KL penalty
                with torch.no_grad():
                    ref_logits = self.ref_model(full_ids)["logits"]
                    shift_ref = ref_logits[..., :-1, :].contiguous()
                    ref_log_probs = -F.cross_entropy(shift_ref.view(-1, self.model.config.vocab_size), shift_labels.view(-1), ignore_index=-100)

                # Relative Advantage weighting
                adv = advantages[i]
                kl_div = log_probs - ref_log_probs

                # PPO-style objective
                loss_i = -(log_probs * adv) + self.beta_kl * kl_div
                total_loss += loss_i

            self.optimizer.zero_grad()
            (total_loss / self.group_size).backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()

        print("✓ GRPO Self-Learning Reinforcement Iterations Complete!")
