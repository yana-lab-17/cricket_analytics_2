"""
dataset_builder.py
Continuous pre-training dataset builder and data loader for NeuroSport-Cricket LLM.
Implements packed sequence chunking with zero padding waste, multi-worker caching,
and integration with external user datasets (Cricsheet JSONs, rules text, previous datasets).
"""

import os
import glob
import json
from typing import List, Generator, Optional, Dict, Any
import torch
from torch.utils.data import Dataset, DataLoader
from tokenizers import Tokenizer

from llm.data.rules_corpus import get_complete_rules_corpus
from llm.data.neuro_corpus import get_complete_neuro_corpus
from llm.data.match_parser import stream_matches_from_directory
from llm.tokenizer.build_tokenizer import train_and_save_tokenizer, build_cricket_neuro_tokenizer

class PackedPretrainDataset(Dataset):
    """
    Memory-efficient PyTorch Dataset for continuous causal language modeling.
    Tokenizes raw text documents, concatenates them into a continuous stream,
    and slices into non-overlapping blocks of `max_seq_len`.
    """
    def __init__(self, token_ids: List[int], seq_len: int = 1024):
        self.seq_len = seq_len
        # Drop the remainder tokens that don't fit a full sequence
        num_blocks = len(token_ids) // (seq_len + 1)
        if num_blocks == 0:
            # If total tokens less than seq_len, pad to seq_len + 1
            padded = token_ids + [0] * (seq_len + 1 - len(token_ids))
            self.data = torch.tensor([padded], dtype=torch.long)
        else:
            total_elements = num_blocks * (seq_len + 1)
            self.data = torch.tensor(token_ids[:total_elements], dtype=torch.long).view(num_blocks, seq_len + 1)

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        chunk = self.data[idx]
        x = chunk[:-1]
        y = chunk[1:]
        return {"input_ids": x, "labels": y}


class NeuroSportDataPipeline:
    """Orchestrates corpus assembly, tokenization, and streaming dataset creation."""
    def __init__(
        self,
        raw_data_dir: str = "llm/raw_datasets",
        tokenizer_path: str = "llm/tokenizer/cricket_tokenizer.json",
        vocab_size: int = 16384,
        max_seq_len: int = 1024
    ):
        self.raw_data_dir = raw_data_dir
        self.tokenizer_path = tokenizer_path
        self.vocab_size = vocab_size
        self.max_seq_len = max_seq_len
        self.tokenizer: Optional[Tokenizer] = None

    def collect_all_text_streams(
        self,
        limit_matches: Optional[int] = None,
        limit_neuro: Optional[int] = None
    ) -> List[str]:
        """Gathers text from built-in corpora, external match JSONs, rules, and previous datasets."""
        documents: List[str] = []

        # 1. Official Extracted ICC Rules & Playing Conditions
        icc_rules_file = "llm/data/icc_official_rules.txt"
        if os.path.exists(icc_rules_file):
            print(f"-> Ingesting official ICC Playing Conditions from {icc_rules_file}...")
            with open(icc_rules_file, "r", encoding="utf-8") as f:
                documents.append(f.read())
        else:
            print("-> Loading foundational ICC Rules & MCC Laws corpus...")
            documents.append(get_complete_rules_corpus())

        # 2. Neuroscience & Biomechanics Foundational Corpus
        print("-> Loading foundational Neuroscience & Biomechanics corpus...")
        documents.append(get_complete_neuro_corpus())

        # 3. Cleaned Pure-Cricket Neuroscience Records
        cricket_neuro_file = "llm/data/cricket_neuro_filtered.jsonl"
        if os.path.exists(cricket_neuro_file):
            print(f"-> Ingesting pure cricket neuroscience records from {cricket_neuro_file}...")
            count = 0
            with open(cricket_neuro_file, "r", encoding="utf-8") as f:
                for line in f:
                    if limit_neuro and count >= limit_neuro:
                        break
                    try:
                        rec = json.loads(line)
                        cue = rec.get("output_coaching_cue", "")
                        state = rec.get("athlete_voice", "")
                        metrics = rec.get("input_metrics", "")
                        stream_text = f"<|biomechanical_breakdown|>\nTelemetry: {metrics}\nContext: {state}\nCoaching Directive: {cue}\n<|endoftext|>\n"
                        documents.append(stream_text)
                        count += 1
                    except:
                        pass
            print(f"   ✓ Ingested {count:,} cricket neuroscience coaching streams.")

        # 4. Ball-by-Ball Match Streams (Tests, ODIs, T20s, IPL)
        match_folders = ["tests_json", "odis_json", "t20s_json", "ipl_json", "matches"]
        for mf in match_folders:
            p = os.path.join(self.raw_data_dir, mf)
            if os.path.exists(p) and os.path.isdir(p):
                match_count = 0
                print(f"-> Ingesting match stream sequences from {p}...")
                for match_stream in stream_matches_from_directory(p):
                    documents.append(match_stream)
                    match_count += 1
                    if limit_matches and match_count >= limit_matches:
                        break
                print(f"   ✓ Ingested {match_count:,} matches from {mf}.")

        # 3. User Custom Rules / Playing Conditions Text Files
        rules_dir = os.path.join(self.raw_data_dir, "rules")
        if os.path.exists(rules_dir):
            for f in glob.glob(os.path.join(rules_dir, "*.*")):
                if f.endswith((".txt", ".md", ".json")):
                    try:
                        with open(f, "r", encoding="utf-8") as rf:
                            content = rf.read()
                            documents.append(content + "\n<|endoftext|>\n")
                    except Exception as e:
                        print(f"Skipping {f}: {e}")

        # 4. Previous Model Datasets (JSON / JSONL)
        prev_dir = os.path.join(self.raw_data_dir, "previous")
        if os.path.exists(prev_dir):
            for f in glob.glob(os.path.join(prev_dir, "*.*")):
                if f.endswith(".jsonl"):
                    print(f"-> Ingesting previous dataset from {f}...")
                    try:
                        with open(f, "r", encoding="utf-8") as jlf:
                            for line in jlf:
                                line = line.strip()
                                if not line: continue
                                try:
                                    item = json.loads(line)
                                    text = item.get("text") or item.get("prompt", "") + " " + item.get("completion", "")
                                    if text:
                                        documents.append(text + "\n<|endoftext|>\n")
                                except:
                                    pass
                    except Exception as e:
                        print(f"Skipping previous jsonl {f}: {e}")

        return documents

    def prepare_tokenizer(self, documents: List[str]) -> Tokenizer:
        """Trains or loads tokenizer using the collected documents."""
        if os.path.exists(self.tokenizer_path):
            print(f"-> Loading existing tokenizer from {self.tokenizer_path}...")
            self.tokenizer = Tokenizer.from_file(self.tokenizer_path)
        else:
            print("-> Training fresh NeuroSport BPE Tokenizer from corpus...")
            temp_corpus_path = "llm/tokenizer/_temp_corpus.txt"
            with open(temp_corpus_path, "w", encoding="utf-8") as f:
                for doc in documents:
                    f.write(doc + "\n\n")

            self.tokenizer = train_and_save_tokenizer(
                [temp_corpus_path],
                output_path=self.tokenizer_path,
                vocab_size=self.vocab_size
            )
            if os.path.exists(temp_corpus_path):
                os.remove(temp_corpus_path)

        return self.tokenizer

    def build_dataloader(
        self,
        batch_size: int = 4,
        shuffle: bool = True,
        num_workers: int = 0,
        limit_matches: Optional[int] = None,
        limit_neuro: Optional[int] = None
    ) -> DataLoader:
        """Builds continuous packed token DataLoader ready for training."""
        documents = self.collect_all_text_streams(limit_matches=limit_matches, limit_neuro=limit_neuro)
        tokenizer = self.prepare_tokenizer(documents)

        print("-> Tokenizing multi-corpus documents into continuous token stream...")
        all_token_ids: List[int] = []
        for doc in documents:
            encoded = tokenizer.encode(doc)
            all_token_ids.extend(encoded.ids)

        print(f"   ✓ Total Tokens Packed: {len(all_token_ids):,} tokens.")
        dataset = PackedPretrainDataset(all_token_ids, seq_len=self.max_seq_len)
        print(f"   ✓ Generated {len(dataset):,} sequence blocks of length {self.max_seq_len}.")

        loader = DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=shuffle,
            num_workers=num_workers,
            pin_memory=torch.cuda.is_available()
        )
        return loader
