"""
post_train.py
Post-Training & Cognitive Alignment Pipeline for NeuroSport-Cricket LLM.
Features:
1. Cognitive Chain-of-Thought (CoT) Reasoning Grounding (<|think|> ... </think>)
2. Direct Preference Optimization (DPO) enforcing ICC Playing Conditions & Biophysics,
   penalizing hallucinations or physically impossible reaction claims.
"""

import os
import copy
from typing import List, Dict, Any, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import AdamW
from tokenizers import Tokenizer

from llm.config import NeuroSportConfig
from llm.architecture.model import NeuroSportCricketLM

COGNITIVE_ALIGNMENT_EXAMPLES = [
    {
        "prompt": "The bowler is bowling at 150 km/h with a 7-2 off-side field. Can a batsman wait for the ball to pitch before deciding whether to cut or drive?",
        "chosen": "<|think|>\n1. Delivery Speed: 150 km/h = 41.7 m/s.\n2. Total Flight Time: 435 ms from release point.\n3. Pitch Landing: Occurs at ~235 ms, leaving a post-pitch decision window of only 200 ms.\n4. Neuromuscular Latency: Foveal saccadic repositioning requires 195 ms; corticospinal motor execution requires ~180-220 ms.\n5. Biophysical Verdict: Waiting for pitch impact leaves less than 20 ms for motor correction, which violates human ocular-motor limits.\n</think>\n<|tactical_output|>\nNo. At 150 km/h, the post-pitch decision window is only ~200 ms, while human saccadic latency and corticospinal motor recruitment require 195 ms and 180-220 ms respectively. The batsman must make a predictive motor forecast within the first 150 ms of release based on bowler wrist cock and arm slot, rather than reacting after the bounce.",
        "rejected": "Yes, a world-class batsman has extraordinary reflexes and can simply watch the ball bounce off the pitch, see which way it seams, and then quickly adjust their bat in 40 ms to play the cut shot safely."
    },
    {
        "prompt": "In an ODI match during Over 8, the captain places 4 fielders on the deep boundary fence. Is this legal?",
        "chosen": "<|think|>\n1. Match Format: One Day International (ODI).\n2. Current Over: Over 8.\n3. Applicable Rule: Mandatory Powerplay 1 spans Overs 1 to 10.\n4. Powerplay 1 Regulation: Clause 28.1 dictates a maximum of TWO (2) fielders outside the 30-yard circle.\n5. Proposed Field: 4 fielders on the boundary fence exceeds the mandatory cap by 2 fielders.\n</think>\n<|tactical_output|>\nNo, this field placement is illegal. Under ICC ODI Standard Playing Conditions, Overs 1 through 10 constitute Mandatory Powerplay 1, during which a maximum of two (2) fielders are permitted outside the 30-yard fielding circle. Placing 4 fielders on the boundary will prompt the standing umpire to call a No-Ball, resulting in a 1-run penalty and a subsequent Free Hit.",
        "rejected": "Yes, in modern ODI cricket the captain is allowed to place as many fielders on the boundary as they want to prevent boundaries if the opposing batsmen are hitting aggressively."
    },
    {
        "prompt": "On a Day 5 dusty pitch, why does late reverse swing catch the outside edge more often than conventional swing?",
        "chosen": "<|think|>\n1. Pitch & Ball Condition: Day 5 pitch provides abrasive turf, creating a heavily scuffed rough hemisphere and a smooth shined hemisphere.\n2. Fluid Dynamics: Reverse swing occurs late in ball flight (after 12-14 meters) due to delayed boundary layer separation on the rough side.\n3. Cognitive Perception: Conventional swing deviates early in trajectory (visible during the initial 150 ms tracking window). Reverse swing deviates inside the final 80 ms, well inside the batsman's saccadic suppression window.\n</think>\n<|tactical_output|>\nOn Day 5, the rough hemisphere produces late asymmetric boundary layer turbulence, causing the ball to dart sharply during the final 5 to 6 meters of flight. Because this deviation occurs inside the batsman's 195 ms saccadic suppression window, the batsman cannot execute an optical motor correction in time, resulting in an outside edge to the slips cordon.",
        "rejected": "Reverse swing is just regular swing that happens when the bowler spins the ball with their fingers, making the batsman confused about the rotation."
    }
]

def compute_logps(
    model: nn.Module,
    input_ids: torch.Tensor,
    labels: torch.Tensor
) -> torch.Tensor:
    """Computes log-probabilities of labels given input_ids."""
    logits = model(input_ids)["logits"]
    # Shift so that tokens < n predict n
    shift_logits = logits[..., :-1, :].contiguous()
    shift_labels = labels[..., 1:].contiguous()
    
    loss_mask = (shift_labels != -100)
    per_token_logps = torch.gather(
        shift_logits.log_softmax(-1),
        dim=2,
        index=shift_labels.unsqueeze(2).clamp(min=0)
    ).squeeze(2)

    return (per_token_logps * loss_mask).sum(-1)

def run_dpo_alignment(
    model: NeuroSportCricketLM,
    tokenizer: Tokenizer,
    beta: float = 0.1,
    learning_rate: float = 5e-5,
    epochs: int = 3,
    device: str = "cuda"
):
    """
    Executes Direct Preference Optimization (DPO) to anchor the model
    in physical biomechanics and ICC regulations without rote memorization.
    """
    print(f"\n======================================================================")
    print(f"🎯 NEUROSPORT COGNITIVE REASONING & DPO ALIGNMENT")
    print(f"======================================================================")

    # Reference model copy (frozen policy pi_ref)
    ref_model = copy.deepcopy(model).to(device)
    ref_model.eval()
    for param in ref_model.parameters():
        param.requires_grad = False

    model.train()
    optimizer = AdamW(model.parameters(), lr=learning_rate)

    print(f"Aligning policy with {len(COGNITIVE_ALIGNMENT_EXAMPLES)} cognitive physics benchmarks (beta={beta})...")

    for epoch in range(epochs):
        epoch_loss = 0.0

        for example in COGNITIVE_ALIGNMENT_EXAMPLES:
            prompt = example["prompt"]
            chosen = example["chosen"]
            rejected = example["rejected"]

            # Tokenize prompt + chosen, prompt + rejected
            enc_prompt = tokenizer.encode(prompt).ids
            enc_chosen = tokenizer.encode(chosen).ids
            enc_rejected = tokenizer.encode(rejected).ids

            # Build inputs & labels with prompt masked (-100)
            chosen_ids = torch.tensor([enc_prompt + enc_chosen], dtype=torch.long, device=device)
            chosen_labels = torch.tensor([[-100] * len(enc_prompt) + enc_chosen], dtype=torch.long, device=device)

            rejected_ids = torch.tensor([enc_prompt + enc_rejected], dtype=torch.long, device=device)
            rejected_labels = torch.tensor([[-100] * len(enc_prompt) + enc_rejected], dtype=torch.long, device=device)

            # Active model log probabilities
            pi_chosen = compute_logps(model, chosen_ids, chosen_labels)
            pi_rejected = compute_logps(model, rejected_ids, rejected_labels)

            # Reference model log probabilities
            with torch.no_grad():
                ref_chosen = compute_logps(ref_model, chosen_ids, chosen_labels)
                ref_rejected = compute_logps(ref_model, rejected_ids, rejected_labels)

            # DPO Loss calculation
            pi_ratio = pi_chosen - pi_rejected
            ref_ratio = ref_chosen - ref_rejected
            dpo_loss = -F.logsigmoid(beta * (pi_ratio - ref_ratio)).mean()

            optimizer.zero_grad()
            dpo_loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            epoch_loss += dpo_loss.item()

        print(f"DPO Epoch {epoch+1}/{epochs} | Loss: {epoch_loss / len(COGNITIVE_ALIGNMENT_EXAMPLES):.4f}")

    print("✓ DPO Cognitive Grounding Alignment Completed.")
    return model

