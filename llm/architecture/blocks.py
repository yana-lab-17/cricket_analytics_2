"""
blocks.py
Core building blocks for NeuroSport-Cricket LLM:
RMSNorm, SwiGLU MLP, and NeuroSport Decoder Blocks.
"""

from typing import Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F

from llm.architecture.attention import GroupedQueryAttention, CognitiveCrossAttention, RotaryEmbedding

class RMSNorm(nn.Module):
    """Root Mean Square Layer Normalization (Zhang & Sennrich, 2019)."""
    def __init__(self, dim: int, eps: float = 1e-6):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))

    def _norm(self, x: torch.Tensor) -> torch.Tensor:
        return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        output = self._norm(x.float()).type_as(x)
        return output * self.weight


class SwiGLU(nn.Module):
    """
    SwiGLU Feed-Forward Network:
    FFN_SwiGLU(x) = (SiLU(x W_gate) * (x W_up)) W_down
    Shown in PaLM / LLaMA to provide superior representation learning per parameter.
    """
    def __init__(self, hidden_dim: int, intermediate_dim: int, dropout: float = 0.0):
        super().__init__()
        self.gate_proj = nn.Linear(hidden_dim, intermediate_dim, bias=False)
        self.up_proj = nn.Linear(hidden_dim, intermediate_dim, bias=False)
        self.down_proj = nn.Linear(intermediate_dim, hidden_dim, bias=False)
        self.dropout = nn.Dropout(dropout) if dropout > 0 else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # F.silu(gate) * up
        gate = F.silu(self.gate_proj(x))
        up = self.up_proj(x)
        out = self.down_proj(gate * up)
        return self.dropout(out)


class NeuroSportDecoderLayer(nn.Module):
    """
    Complete Transformer Decoder Layer with:
    1. Pre-RMSNorm
    2. Grouped-Query Attention (GQA) with RoPE
    3. Biomechanical Cognitive Cross-Attention (optional)
    4. SwiGLU Feed-Forward Network
    5. Residual pathways
    """
    def __init__(
        self,
        hidden_dim: int,
        num_heads: int,
        num_kv_heads: int,
        head_dim: int,
        intermediate_dim: int,
        rms_norm_eps: float = 1e-6,
        use_cognitive_attention: bool = False,
        cognitive_feature_dim: int = 64,
        attn_dropout: float = 0.0,
        resid_dropout: float = 0.0
    ):
        super().__init__()
        self.input_layernorm = RMSNorm(hidden_dim, eps=rms_norm_eps)
        self.self_attn = GroupedQueryAttention(
            hidden_dim=hidden_dim,
            num_heads=num_heads,
            num_kv_heads=num_kv_heads,
            head_dim=head_dim,
            attn_dropout=attn_dropout,
            resid_dropout=resid_dropout
        )
        
        self.use_cognitive_attention = use_cognitive_attention
        if use_cognitive_attention:
            self.cognitive_norm = RMSNorm(hidden_dim, eps=rms_norm_eps)
            self.cognitive_attn = CognitiveCrossAttention(
                hidden_dim=hidden_dim,
                cognitive_dim=cognitive_feature_dim,
                num_heads=num_kv_heads
            )

        self.post_attention_layernorm = RMSNorm(hidden_dim, eps=rms_norm_eps)
        self.mlp = SwiGLU(hidden_dim=hidden_dim, intermediate_dim=intermediate_dim, dropout=resid_dropout)

    def forward(
        self,
        x: torch.Tensor,
        rotary_emb: RotaryEmbedding,
        cognitive_features: Optional[torch.Tensor] = None,
        kv_cache: Optional[Tuple[torch.Tensor, torch.Tensor]] = None,
        use_cache: bool = False
    ) -> Tuple[torch.Tensor, Optional[Tuple[torch.Tensor, torch.Tensor]]]:
        # 1. Self Attention with Pre-Norm
        normed = self.input_layernorm(x)
        attn_out, new_kv_cache = self.self_attn(
            normed,
            rotary_emb=rotary_emb,
            kv_cache=kv_cache,
            use_cache=use_cache
        )
        x = x + attn_out

        # 2. Cognitive Cross-Attention (if biomechanics provided)
        if self.use_cognitive_attention and cognitive_features is not None:
            normed_cog = self.cognitive_norm(x)
            x = self.cognitive_attn(normed_cog, cognitive_features)

        # 3. SwiGLU MLP with Pre-Norm
        mlp_out = self.mlp(self.post_attention_layernorm(x))
        x = x + mlp_out

        return x, new_kv_cache

