"""
attention.py
High-performance Grouped-Query Attention (GQA) with Rotary Position Embeddings (RoPE)
and Cognitive Biomechanical Cross-Attention for the NeuroSport-Cricket LLM.
"""

import math
from typing import Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F

class RotaryEmbedding(nn.Module):
    """Rotary Position Embedding (RoPE) with frequency precomputation and extrapolation."""
    def __init__(self, dim: int, max_seq_len: int = 8192, theta: float = 500000.0):
        super().__init__()
        self.dim = dim
        self.theta = theta
        self.max_seq_len = max_seq_len
        
        # Precompute inv_freq
        inv_freq = 1.0 / (theta ** (torch.arange(0, dim, 2).float() / dim))
        self.register_buffer("inv_freq", inv_freq, persistent=False)
        self._build_cache(max_seq_len)

    def _build_cache(self, seq_len: int):
        t = torch.arange(seq_len, device=self.inv_freq.device, dtype=self.inv_freq.dtype)
        freqs = torch.outer(t, self.inv_freq)
        emb = torch.cat((freqs, freqs), dim=-1)
        self.register_buffer("cos_cached", emb.cos(), persistent=False)
        self.register_buffer("sin_cached", emb.sin(), persistent=False)

    def forward(self, x: torch.Tensor, seq_len: int) -> Tuple[torch.Tensor, torch.Tensor]:
        if seq_len > self.cos_cached.shape[0]:
            self._build_cache(seq_len)
        return (
            self.cos_cached[:seq_len].to(dtype=x.dtype),
            self.sin_cached[:seq_len].to(dtype=x.dtype)
        )

def _rotate_half(x: torch.Tensor) -> torch.Tensor:
    x1 = x[..., : x.shape[-1] // 2]
    x2 = x[..., x.shape[-1] // 2 :]
    return torch.cat((-x2, x1), dim=-1)

def apply_rotary_pos_emb(q: torch.Tensor, k: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
    # q, k shape: [batch, heads, seq_len, head_dim]
    # cos, sin shape: [seq_len, head_dim] -> unsqueeze to [1, 1, seq_len, head_dim]
    cos = cos.unsqueeze(0).unsqueeze(1)
    sin = sin.unsqueeze(0).unsqueeze(1)
    q_embed = (q * cos) + (_rotate_half(q) * sin)
    k_embed = (k * cos) + (_rotate_half(k) * sin)
    return q_embed, k_embed

class GroupedQueryAttention(nn.Module):
    """
    Grouped-Query Attention (GQA) with RoPE and PyTorch native Scaled Dot-Product Attention (SDPA).
    Reduces KV cache memory by factor of num_heads / num_kv_heads for ultra-fast generation.
    """
    def __init__(
        self,
        hidden_dim: int,
        num_heads: int,
        num_kv_heads: int,
        head_dim: int,
        attn_dropout: float = 0.0,
        resid_dropout: float = 0.0
    ):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_heads = num_heads
        self.num_kv_heads = num_kv_heads
        self.head_dim = head_dim
        self.num_queries_per_kv = num_heads // num_kv_heads
        self.attn_dropout = attn_dropout

        self.q_proj = nn.Linear(hidden_dim, num_heads * head_dim, bias=False)
        self.k_proj = nn.Linear(hidden_dim, num_kv_heads * head_dim, bias=False)
        self.v_proj = nn.Linear(hidden_dim, num_kv_heads * head_dim, bias=False)
        self.o_proj = nn.Linear(num_heads * head_dim, hidden_dim, bias=False)
        self.resid_dropout = nn.Dropout(resid_dropout) if resid_dropout > 0 else nn.Identity()

    def forward(
        self,
        x: torch.Tensor,
        rotary_emb: RotaryEmbedding,
        kv_cache: Optional[Tuple[torch.Tensor, torch.Tensor]] = None,
        use_cache: bool = False
    ) -> Tuple[torch.Tensor, Optional[Tuple[torch.Tensor, torch.Tensor]]]:
        batch_size, seq_len, _ = x.shape

        q = self.q_proj(x)
        k = self.k_proj(x)
        v = self.v_proj(x)

        # Reshape to [batch, num_heads, seq_len, head_dim]
        q = q.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        k = k.view(batch_size, seq_len, self.num_kv_heads, self.head_dim).transpose(1, 2)
        v = v.view(batch_size, seq_len, self.num_kv_heads, self.head_dim).transpose(1, 2)

        # Calculate position offset if KV cache exists
        past_len = kv_cache[0].shape[-2] if kv_cache is not None else 0
        total_len = past_len + seq_len

        # Apply RoPE
        cos, sin = rotary_emb(x, total_len)
        cos = cos[past_len:total_len]
        sin = sin[past_len:total_len]
        q, k = apply_rotary_pos_emb(q, k, cos, sin)

        # Update KV cache
        if kv_cache is not None:
            k = torch.cat([kv_cache[0], k], dim=-2)
            v = torch.cat([kv_cache[1], v], dim=-2)

        new_kv_cache = (k, v) if use_cache else None

        # Repeat KV heads for GQA if num_kv_heads < num_heads
        if self.num_queries_per_kv > 1:
            k = k.repeat_interleave(self.num_queries_per_kv, dim=1)
            v = v.repeat_interleave(self.num_queries_per_kv, dim=1)

        # Causal mask is applied when training or when sequence length > 1
        is_causal = (seq_len > 1 and past_len == 0)

        # Fast Scaled Dot-Product Attention (Hardware-accelerated FlashAttention / CuDNN)
        out = F.scaled_dot_product_attention(
            q, k, v,
            attn_mask=None,
            dropout_p=self.attn_dropout if self.training else 0.0,
            is_causal=is_causal
        )

        out = out.transpose(1, 2).contiguous().view(batch_size, seq_len, self.num_heads * self.head_dim)
        out = self.o_proj(out)
        out = self.resid_dropout(out)

        return out, new_kv_cache


class CognitiveCrossAttention(nn.Module):
    """
    NeuroSport Domain Innovation: Biomechanical Cognitive Cross-Attention.
    Directly aligns linguistic tokens with numerical kinetic telemetry
    (ballistic release velocity, foveal saccade window, decision latency, pitch wear).
    """
    def __init__(self, hidden_dim: int, cognitive_dim: int, num_heads: int = 4):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.cognitive_dim = cognitive_dim
        self.num_heads = num_heads
        self.head_dim = hidden_dim // num_heads

        self.q_proj = nn.Linear(hidden_dim, hidden_dim, bias=False)
        self.k_proj = nn.Linear(cognitive_dim, hidden_dim, bias=False)
        self.v_proj = nn.Linear(cognitive_dim, hidden_dim, bias=False)
        self.o_proj = nn.Linear(hidden_dim, hidden_dim, bias=False)
        self.gate = nn.Parameter(torch.zeros(1))  # Zero-initialized residual gate

    def forward(self, token_hidden: torch.Tensor, cognitive_features: Optional[torch.Tensor]) -> torch.Tensor:
        if cognitive_features is None:
            return token_hidden

        batch_size, seq_len, _ = token_hidden.shape
        _, cog_len, _ = cognitive_features.shape

        q = self.q_proj(token_hidden).view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(cognitive_features).view(batch_size, cog_len, self.num_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(cognitive_features).view(batch_size, cog_len, self.num_heads, self.head_dim).transpose(1, 2)

        attn_out = F.scaled_dot_product_attention(q, k, v, is_causal=False)
        attn_out = attn_out.transpose(1, 2).contiguous().view(batch_size, seq_len, self.hidden_dim)
        attn_out = self.o_proj(attn_out)

        # Gated residual connection to preserve stability during initial pre-training
        return token_hidden + torch.tanh(self.gate) * attn_out

