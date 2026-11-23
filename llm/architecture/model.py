"""
model.py
The Complete NeuroSportCricketLM Architecture.
Production-grade causal autoregressive model tailored for cricket ballistics,
laws of the sport, and neuroscience motor control cognition.
"""

import math
from typing import Optional, Tuple, Dict, Any, List
import torch
import torch.nn as nn
import torch.nn.functional as F

from llm.config import NeuroSportConfig
from llm.architecture.attention import RotaryEmbedding
from llm.architecture.blocks import RMSNorm, NeuroSportDecoderLayer

class NeuroSportCricketLM(nn.Module):
    """
    Custom NeuroSport-Cricket Foundation Language Model.
    Features:
    - Grouped-Query Attention (GQA) with RoPE (Rotary Position Embeddings)
    - SwiGLU Non-Linear Feed-Forward Blocks
    - Biomechanical Cognitive Cross-Attention Layers
    - RMSNorm Pre-Normalization
    - Hardware-accelerated Flash Attention via PyTorch SDPA
    - Zero-allocation KV-Caching for high-speed streaming generation
    """
    def __init__(self, config: NeuroSportConfig):
        super().__init__()
        self.config = config

        self.tok_embeddings = nn.Embedding(config.vocab_size, config.hidden_dim)
        self.rotary_emb = RotaryEmbedding(
            dim=config.head_dim,
            max_seq_len=config.max_seq_len,
            theta=config.rope_theta
        )

        # Decoder layers stack
        self.layers = nn.ModuleList([
            NeuroSportDecoderLayer(
                hidden_dim=config.hidden_dim,
                num_heads=config.num_heads,
                num_kv_heads=config.num_kv_heads,
                head_dim=config.head_dim,
                intermediate_dim=config.intermediate_dim,
                rms_norm_eps=config.rms_norm_eps,
                use_cognitive_attention=config.use_cognitive_attention and (i % 2 == 1), # Interleaved cognitive layers
                cognitive_feature_dim=config.cognitive_feature_dim,
                attn_dropout=config.attn_dropout,
                resid_dropout=config.resid_dropout
            )
            for i in range(config.num_layers)
        ])

        self.norm = RMSNorm(config.hidden_dim, eps=config.rms_norm_eps)
        self.lm_head = nn.Linear(config.hidden_dim, config.vocab_size, bias=False)

        if config.tie_word_embeddings:
            self.lm_head.weight = self.tok_embeddings.weight

        self._init_weights()

    def _init_weights(self):
        """Initialize weights using scaled Gaussian initialization."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                torch.nn.init.normal_(module.weight, mean=0.0, std=self.config.initializer_range)
                if module.bias is not None:
                    torch.nn.init.zeros_(module.bias)
            elif isinstance(module, nn.Embedding):
                torch.nn.init.normal_(module.weight, mean=0.0, std=self.config.initializer_range)
        
        # Scale residual projections for deep stability
        scale = 1.0 / math.sqrt(2.0 * self.config.num_layers)
        for layer in self.layers:
            layer.self_attn.o_proj.weight.data.mul_(scale)
            layer.mlp.down_proj.weight.data.mul_(scale)

    def forward(
        self,
        input_ids: torch.Tensor,
        labels: Optional[torch.Tensor] = None,
        cognitive_features: Optional[torch.Tensor] = None,
        kv_caches: Optional[List[Tuple[torch.Tensor, torch.Tensor]]] = None,
        use_cache: bool = False
    ) -> Dict[str, Any]:
        """
        Forward pass for training (calculates causal loss) or generation (produces next token logits).
        """
        batch_size, seq_len = input_ids.shape
        
        # Token Embeddings
        hidden_states = self.tok_embeddings(input_ids)

        new_kv_caches = [] if use_cache else None

        # Pass through decoder blocks
        for i, layer in enumerate(self.layers):
            layer_cache = kv_caches[i] if kv_caches is not None else None
            hidden_states, new_cache = layer(
                hidden_states,
                rotary_emb=self.rotary_emb,
                cognitive_features=cognitive_features,
                kv_cache=layer_cache,
                use_cache=use_cache
            )
            if use_cache:
                new_kv_caches.append(new_cache)

        # Final RMSNorm
        hidden_states = self.norm(hidden_states)
        logits = self.lm_head(hidden_states)

        # Compute next-token prediction cross-entropy loss if labels are provided
        loss = None
        if labels is not None:
            # Shift so that tokens < n predict n
            shift_logits = logits[..., :-1, :].contiguous()
            shift_labels = labels[..., 1:].contiguous()
            loss = F.cross_entropy(
                shift_logits.view(-1, self.config.vocab_size),
                shift_labels.view(-1),
                ignore_index=-100
            )

        return {
            "loss": loss,
            "logits": logits,
            "kv_caches": new_kv_caches
        }

    def count_parameters(self) -> Dict[str, int]:
        total = sum(p.numel() for p in self.parameters())
        trainable = sum(p.numel() for p in self.parameters() if p.requires_grad)
        emb = self.tok_embeddings.weight.numel()
        return {
            "total_parameters": total,
            "trainable_parameters": trainable,
            "non_embedding_parameters": total - emb
        }

