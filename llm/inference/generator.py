"""
generator.py
High-throughput Autoregressive Text Generation Engine for NeuroSport-Cricket LLM.
Features:
- O(1) KV-Caching with RoPE support
- Top-p (nucleus) and Top-k filtering
- Temperature scaling and repetition penalty
- Token streaming generator interface
"""

from typing import Optional, List, Generator
import torch
import torch.nn.functional as F
from tokenizers import Tokenizer

from llm.architecture.model import NeuroSportCricketLM

class NeuroSportGenerator:
    """KV-Cached Text Generator for NeuroSport LLM."""
    def __init__(
        self,
        model: NeuroSportCricketLM,
        tokenizer: Tokenizer,
        device: str = "cuda"
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device
        self.model.to(device)
        self.model.eval()

        # Find EOS/stop token ids
        self.eos_token_id = tokenizer.token_to_id("<|endoftext|>") or tokenizer.token_to_id("<|eos|>") or 0

    @torch.no_grad()
    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 150,
        temperature: float = 0.7,
        top_k: int = 40,
        top_p: float = 0.9,
        repetition_penalty: float = 1.15
    ) -> str:
        """Generates complete text response for a given prompt."""
        result = []
        for token_text in self.stream_generate(
            prompt=prompt,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            repetition_penalty=repetition_penalty
        ):
            result.append(token_text)
        return "".join(result)

    @torch.no_grad()
    def stream_generate(
        self,
        prompt: str,
        max_new_tokens: int = 150,
        temperature: float = 0.7,
        top_k: int = 40,
        top_p: float = 0.9,
        repetition_penalty: float = 1.15
    ) -> Generator[str, None, None]:
        """Streams generated tokens one by one."""
        enc = self.tokenizer.encode(prompt)
        input_ids = torch.tensor([enc.ids], dtype=torch.long, device=self.device)

        generated_tokens: List[int] = []
        kv_caches = None

        for step in range(max_new_tokens):
            if step == 0:
                # First pass: Process full prompt
                out = self.model(input_ids=input_ids, use_cache=True)
            else:
                # Subsequent passes: Pass only the last generated token with existing KV cache
                next_in = torch.tensor([[generated_tokens[-1]]], dtype=torch.long, device=self.device)
                out = self.model(input_ids=next_in, kv_caches=kv_caches, use_cache=True)

            logits = out["logits"][:, -1, :] # [1, vocab_size]
            kv_caches = out["kv_caches"]

            # Apply repetition penalty
            if repetition_penalty != 1.0 and len(generated_tokens) > 0:
                for token_id in set(generated_tokens):
                    logits[0, token_id] /= repetition_penalty

            # Apply temperature
            if temperature > 0:
                logits = logits / temperature

                # Top-K filtering
                if top_k > 0:
                    v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                    logits[logits < v[:, [-1]]] = -float('Inf')

                # Top-P (nucleus) filtering
                if top_p < 1.0:
                    sorted_logits, sorted_indices = torch.sort(logits, descending=True)
                    cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)
                    sorted_indices_to_remove = cumulative_probs > top_p
                    sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
                    sorted_indices_to_remove[..., 0] = 0
                    indices_to_remove = sorted_indices_to_remove.scatter(1, sorted_indices, sorted_indices_to_remove)
                    logits[indices_to_remove] = -float('Inf')

                probs = F.softmax(logits, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1).item()
            else:
                next_token = torch.argmax(logits, dim=-1).item()

            if next_token == self.eos_token_id:
                break

            generated_tokens.append(next_token)
            token_str = self.tokenizer.decode([next_token])
            yield token_str

