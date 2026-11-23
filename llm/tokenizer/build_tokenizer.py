"""
build_tokenizer.py
Constructs and trains a custom BPE (Byte-Pair Encoding) Tokenizer for NeuroSport-Cricket.
Features ByteFallback (zero <unk> tokens) and specialized cricket/neuroscience vocabulary.
"""

import os
from typing import List, Optional
from tokenizers import Tokenizer, models, pre_tokenizers, trainers, decoders, processors

SPECIAL_TOKENS = [
    "<|endoftext|>",
    "<|pad|>",
    "<|bos|>",
    "<|eos|>",
    # Match Formats & Structure
    "<|test_match|>",
    "<|odi_match|>",
    "<|t20_match|>",
    "<|innings_1|>",
    "<|innings_2|>",
    # Deliveries & In-Game Telemetry
    "<|over|>",
    "<|ball|>",
    "<|score|>",
    "<|wicket|>",
    "<|four|>",
    "<|six|>",
    "<|dot_ball|>",
    "<|pitch_map|>",
    "<|wagon_wheel|>",
    "<|field_setting|>",
    # Cricket Biomechanics & Neuroscience
    "<|saccadic_latency|>",
    "<|decision_window|>",
    "<|kinetic_chain|>",
    "<|motor_cortex|>",
    "<|optical_expansion|>",
    "<|foveal_fixation|>",
    "<|expected_runs_prevented|>",
    "<|xrp|>",
    # Cognitive Deliberation / Reasoning Chain
    "<|think|>",
    "</think>",
    "<|tactical_output|>",
    "<|biomechanical_breakdown|>"
]

def build_cricket_neuro_tokenizer(vocab_size: int = 16384) -> Tokenizer:
    """Instantiate and configure BPE Tokenizer with ByteFallback."""
    tokenizer = Tokenizer(models.BPE(unk_token=None, byte_fallback=True))
    
    # Pre-tokenization: Split by whitespace, punctuation, and digits
    tokenizer.pre_tokenizer = pre_tokenizers.Sequence([
        pre_tokenizers.ByteLevel(add_prefix_space=False, use_regex=True)
    ])
    tokenizer.decoder = decoders.ByteLevel()
    
    return tokenizer

def train_and_save_tokenizer(
    corpus_files: List[str],
    output_path: str = "llm/tokenizer/cricket_tokenizer.json",
    vocab_size: int = 16384
) -> Tokenizer:
    """Train the tokenizer on corpus files and persist as JSON."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    tokenizer = build_cricket_neuro_tokenizer(vocab_size=vocab_size)
    
    trainer = trainers.BpeTrainer(
        vocab_size=vocab_size,
        special_tokens=SPECIAL_TOKENS,
        initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),
        show_progress=True
    )
    
    print(f"Training NeuroSport BPE Tokenizer (vocab={vocab_size}) on {len(corpus_files)} files...")
    tokenizer.train(corpus_files, trainer)
    tokenizer.save(output_path)
    print(f"✓ Tokenizer saved successfully to {output_path}")
    return tokenizer

if __name__ == "__main__":
    import tempfile
    # Self-test: Train on seed text
    sample_corpus = [
        "The bowler releases a 148 km/h delivery on good length outside off stump.",
        "The batter foveal visual tracking saccade takes 195ms to register pitch impact.",
        "Under ICC Men's Test Playing Conditions Law 41, unfair play includes ball tampering."
    ]
    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        f.write("\n".join(sample_corpus))
        tmp_name = f.name
    
    tok = train_and_save_tokenizer([tmp_name], vocab_size=512)
    os.unlink(tmp_name)

