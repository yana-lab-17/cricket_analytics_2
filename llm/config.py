"""
config.py
Hyperparameter and architectural configurations for the NeuroSport-Cricket LLM.
Supports tiny (prototyping/testing), base (production single-node/GPU), and scaled configurations.
"""

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class NeuroSportConfig:
    # Model dimensions
    vocab_size: int = 16384
    hidden_dim: int = 768
    intermediate_dim: int = 2048       # SwiGLU hidden dim (approx 8/3 * hidden_dim)
    num_layers: int = 12
    num_heads: int = 12                # Query attention heads
    num_kv_heads: int = 4              # Grouped-Query Attention (GQA) heads
    head_dim: int = 64                 # hidden_dim // num_heads = 64
    max_seq_len: int = 4096
    
    # Normalization & Embeddings
    rms_norm_eps: float = 1e-6
    rope_theta: float = 500000.0       # High-frequency base for long-sequence match logs
    initializer_range: float = 0.02
    
    # Custom NeuroSport Architectural Enhancements
    use_cognitive_attention: bool = True   # Cross-attention between kinetic temporal states & token stream
    cognitive_feature_dim: int = 64        # Spatial & temporal cognitive metrics (saccade, decision ms, xRP)
    use_sliding_window: bool = False
    sliding_window_size: int = 1024
    tie_word_embeddings: bool = False
    
    # Dropout & Regularization
    attn_dropout: float = 0.0
    resid_dropout: float = 0.0
    
    # Training defaults
    dtype: str = "bfloat16"                # bfloat16 or float16
    
    @classmethod
    def tiny(cls):
        """Ultra-fast configuration for architectural validation, unit tests, and CI/CD."""
        return cls(
            vocab_size=4096,
            hidden_dim=256,
            intermediate_dim=680,
            num_layers=4,
            num_heads=4,
            num_kv_heads=2,
            head_dim=64,
            max_seq_len=1024,
            cognitive_feature_dim=32
        )

    @classmethod
    def base(cls):
        """Production grade configuration designed for high throughput on RTX/A100/H100."""
        return cls(
            vocab_size=16384,
            hidden_dim=768,
            intermediate_dim=2048,
            num_layers=12,
            num_heads=12,
            num_kv_heads=4,
            head_dim=64,
            max_seq_len=4096,
            cognitive_feature_dim=64
        )

    @classmethod
    def large(cls):
        """Full-scale production model for distributed multi-GPU training."""
        return cls(
            vocab_size=32768,
            hidden_dim=1536,
            intermediate_dim=4096,
            num_layers=24,
            num_heads=16,
            num_kv_heads=4,
            head_dim=96,
            max_seq_len=8192,
            cognitive_feature_dim=128
        )

