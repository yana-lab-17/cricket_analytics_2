"""
server.py
Interactive CLI & Server for NeuroSport-Cricket LLM.
Supports interactive multi-turn terminal chat, cognitive biophysical queries,
and real-time streaming integration with the 3D Cricket Game Simulator.
"""

import os
import sys
import argparse
from typing import Tuple, Dict, Any, Optional
import torch
from tokenizers import Tokenizer

from llm.config import NeuroSportConfig
from llm.architecture.model import NeuroSportCricketLM
from llm.inference.generator import NeuroSportGenerator
from llm.data.dataset_builder import NeuroSportDataPipeline

def get_or_create_neurosport_engine(
    config_name: str = "base",
    checkpoint_path: str = "llm/checkpoints/neurosport_pretrained_final.pt",
    device: str = "cuda"
) -> Tuple[NeuroSportCricketLM, Tokenizer]:
    """Loads existing trained weights or initializes the model ready for training/inference."""
    if config_name == "tiny":
        cfg = NeuroSportConfig.tiny()
    else:
        cfg = NeuroSportConfig.base()

    pipeline = NeuroSportDataPipeline(vocab_size=cfg.vocab_size)
    docs = pipeline.collect_all_text_streams()
    tokenizer = pipeline.prepare_tokenizer(docs)

    model = NeuroSportCricketLM(cfg).to(device)

    if os.path.exists(checkpoint_path):
        print(f"Loading checkpoint from {checkpoint_path}...")
        ckpt = torch.load(checkpoint_path, map_location=device)
        model.load_state_dict(ckpt["model_state_dict"])
        print("✓ Loaded model weights.")
    else:
        print("Notice: No saved checkpoint found at path. Initialized with fresh architectural weights.")

    return model, tokenizer

def run_interactive_cli():
    """Terminal chat interface for NeuroSport-Cricket LLM."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("\n" + "=" * 70)
    print("🧠 NEUROSPORT-CRICKET INTERACTIVE AI REASONING TERMINAL")
    print("=" * 70)
    print("Ask any question on Cricket Laws (Test/ODI/T20), Fielding Physics, or Neuroscience!")
    print("Type 'exit' or 'quit' to close.\n")

    model, tokenizer = get_or_create_neurosport_engine(config_name="base", device=device)
    generator = NeuroSportGenerator(model, tokenizer, device=device)

    while True:
        try:
            query = input("\n🏏 Ask NeuroSport > ").strip()
            if not query:
                continue
            if query.lower() in ["exit", "quit", "q"]:
                print("Exiting NeuroSport AI session.")
                break

            prompt = f"<|think|>\nQuery: {query}\n"
            print("\n💡 NeuroSport Response:\n", end="", flush=True)

            for token in generator.stream_generate(
                prompt=prompt,
                max_new_tokens=180,
                temperature=0.6,
                top_p=0.9
            ):
                sys.stdout.write(token)
                sys.stdout.flush()
            print()

        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chat", action="store_true", help="Launch interactive CLI chat")
    parser.add_argument("--config", type=str, default="base")
    args = parser.parse_args()

    run_interactive_cli()
