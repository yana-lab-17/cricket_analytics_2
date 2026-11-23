"""
pretrain.py
Production-grade Pre-training Engine for NeuroSport-Cricket LLM.
Features:
- Mixed-Precision Autocasting (AMP FP16/BF16)
- Cosine Annealing Learning Rate Schedule with Warmup
- Gradient Accumulation for Large Effective Batch Sizes
- Decoupled AdamW Weight Decay (exempts RMSNorm and Biases)
- Gradient Norm Clipping
- Checkpoint Resumption and Perplexity Evaluation
"""

import os
import math
import time
import argparse
from typing import Dict, Any, Optional
import torch
import torch.nn as nn
from torch.optim import AdamW

from llm.config import NeuroSportConfig
from llm.architecture.model import NeuroSportCricketLM
from llm.data.dataset_builder import NeuroSportDataPipeline

def configure_optimizers(model: nn.Module, lr: float, weight_decay: float = 0.1) -> AdamW:
    """Decouples weight decay so 1D parameters (biases, RMSNorm weights) are not decayed."""
    decay_params = []
    no_decay_params = []

    for name, param in model.named_parameters():
        if not param.requires_grad:
            continue
        if param.dim() >= 2:
            decay_params.append(param)
        else:
            no_decay_params.append(param)

    optim_groups = [
        {"params": decay_params, "weight_decay": weight_decay},
        {"params": no_decay_params, "weight_decay": 0.0}
    ]
    return AdamW(optim_groups, lr=lr, betas=(0.9, 0.95), eps=1e-8)

def get_cosine_schedule_with_warmup(
    optimizer,
    num_warmup_steps: int,
    num_training_steps: int,
    min_lr_ratio: float = 0.1
):
    """Cosine learning rate decay with linear warmup."""
    def lr_lambda(current_step: int):
        if current_step < num_warmup_steps:
            return float(current_step) / float(max(1, num_warmup_steps))
        progress = float(current_step - num_warmup_steps) / float(max(1, num_training_steps - num_warmup_steps))
        return min_lr_ratio + 0.5 * (1.0 - min_lr_ratio) * (1.0 + math.cos(math.pi * progress))
    return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

def train_pretrain(
    config_name: str = "base",
    epochs: int = 3,
    batch_size: int = 4,
    gradient_accumulation_steps: int = 4,
    learning_rate: float = 3e-4,
    warmup_steps: int = 50,
    save_every_steps: int = 100,
    checkpoint_dir: str = "llm/checkpoints",
    resume_from: Optional[str] = None
):
    os.makedirs(checkpoint_dir, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"======================================================================")
    print(f"🚀 NEUROSPORT-CRICKET LLM PRE-TRAINING ENGINE")
    print(f"======================================================================")
    print(f"Device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    # 1. Config selection
    if config_name == "tiny":
        cfg = NeuroSportConfig.tiny()
    elif config_name == "large":
        cfg = NeuroSportConfig.large()
    else:
        cfg = NeuroSportConfig.base()

    # 2. Data Pipeline
    pipeline = NeuroSportDataPipeline(
        raw_data_dir="llm/raw_datasets",
        tokenizer_path="llm/tokenizer/cricket_tokenizer.json",
        vocab_size=cfg.vocab_size,
        max_seq_len=cfg.max_seq_len
    )
    dataloader = pipeline.build_dataloader(batch_size=batch_size, shuffle=True)

    # 3. Model Architecture
    model = NeuroSportCricketLM(cfg).to(device)
    param_info = model.count_parameters()
    print(f"Model Parameters: {param_info['total_parameters']:,} (Trainable: {param_info['trainable_parameters']:,})")

    # 4. Optimizer & Scheduler
    optimizer = configure_optimizers(model, lr=learning_rate)
    total_training_steps = (len(dataloader) // gradient_accumulation_steps) * epochs
    scheduler = get_cosine_schedule_with_warmup(
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=max(1, total_training_steps)
    )

    # 5. Mixed Precision Scaler
    scaler = torch.cuda.amp.GradScaler(enabled=torch.cuda.is_available())
    use_bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    amp_dtype = torch.bfloat16 if use_bf16 else torch.float16
    print(f"Mixed Precision: enabled ({'BF16' if use_bf16 else 'FP16'})")

    global_step = 0
    start_epoch = 0

    if resume_from and os.path.exists(resume_from):
        print(f"-> Resuming checkpoint from {resume_from}...")
        ckpt = torch.load(resume_from, map_location=device)
        model.load_state_dict(ckpt["model_state_dict"])
        optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        global_step = ckpt.get("step", 0)
        start_epoch = ckpt.get("epoch", 0)

    # 6. Training Loop
    model.train()
    print(f"\nStarting Pre-Training ({epochs} epochs, {len(dataloader)} batches/epoch)...")
    start_time = time.time()

    for epoch in range(start_epoch, epochs):
        epoch_loss = 0.0
        accumulated_loss = 0.0

        for step, batch in enumerate(dataloader):
            input_ids = batch["input_ids"].to(device)
            labels = batch["labels"].to(device)

            with torch.cuda.amp.autocast(enabled=torch.cuda.is_available(), dtype=amp_dtype):
                outputs = model(input_ids, labels=labels)
                loss = outputs["loss"] / gradient_accumulation_steps

            scaler.scale(loss).backward()
            accumulated_loss += loss.item() * gradient_accumulation_steps

            if (step + 1) % gradient_accumulation_steps == 0 or (step + 1) == len(dataloader):
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad(set_to_none=True)
                scheduler.step()

                global_step += 1
                curr_lr = scheduler.get_last_lr()[0]
                ppl = math.exp(min(accumulated_loss, 20.0))

                if global_step % 10 == 0 or global_step == 1:
                    tokens_per_sec = (batch_size * cfg.max_seq_len * gradient_accumulation_steps) / max(1e-4, time.time() - start_time)
                    start_time = time.time()
                    print(
                        f"Epoch {epoch+1}/{epochs} | Step {global_step}/{total_training_steps} | "
                        f"Loss: {accumulated_loss:.4f} | PPL: {ppl:.2f} | LR: {curr_lr:.2e} | "
                        f"Speed: {tokens_per_sec:.0f} tok/s"
                    )

                if global_step % save_every_steps == 0:
                    ckpt_path = os.path.join(checkpoint_dir, f"neurosport_step_{global_step}.pt")
                    torch.save({
                        "step": global_step,
                        "epoch": epoch,
                        "config": cfg,
                        "model_state_dict": model.state_dict(),
                        "optimizer_state_dict": optimizer.state_dict(),
                        "loss": accumulated_loss
                    }, ckpt_path)
                    print(f"   💾 Saved Checkpoint -> {ckpt_path}")

                epoch_loss += accumulated_loss
                accumulated_loss = 0.0

    # Final Checkpoint
    final_path = os.path.join(checkpoint_dir, "neurosport_pretrained_final.pt")
    torch.save({
        "step": global_step,
        "config": cfg,
        "model_state_dict": model.state_dict(),
        "loss": epoch_loss / max(1, len(dataloader))
    }, final_path)
    print(f"\n✓ Pre-Training Completed Successfully! Final model saved -> {final_path}")
    return final_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NeuroSport-Cricket LLM Pre-Training")
    parser.add_argument("--config", type=str, default="tiny", choices=["tiny", "base", "large"])
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch_size", type=int, default=2)
    parser.add_argument("--grad_accum", type=int, default=2)
    parser.add_argument("--lr", type=float, default=3e-4)
    args = parser.parse_args()

    train_pretrain(
        config_name=args.config,
        epochs=args.epochs,
        batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr
    )

