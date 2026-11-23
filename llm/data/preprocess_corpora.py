"""
preprocess_corpora.py
Cleans, filters, and standardizes raw datasets into pure cricket neuroscience corpora:
1. Extracts text from official ICC PDFs (Test, ODI, T20 conditions, Illegal bowling actions, Code of Conduct).
2. Filters out non-cricket sports from neurosport JSONL (extracts pure cricket batting/bowling/fielding neuro records).
3. Indexes 11,252 international and league match JSON files for continuous causal stream generation.
"""

import os
import subprocess
import json
import glob

def extract_icc_pdfs(raw_dir: str = "llm/raw_datasets", out_file: str = "llm/data/icc_official_rules.txt"):
    """Extracts text from all official ICC PDF rulebooks into a consolidated text corpus."""
    pdf_files = [
        "test_conditions.pdf",
        "odi_conditions.pdf",
        "t20_conditions.pdf",
        "illegal_actions.pdf",
        "code_of_conduct.pdf"
    ]
    
    extracted_text = []
    print("-> Extracting authoritative text from ICC PDF documents...")
    
    for pdf_name in pdf_files:
        p = os.path.join(raw_dir, pdf_name)
        if os.path.exists(p):
            try:
                txt = subprocess.check_output(["pdftotext", p, "-"]).decode("utf-8", errors="ignore")
                format_header = f"\n<|{pdf_name.replace('.pdf', '')}|> OFFICIAL ICC REGULATION: {pdf_name}\n"
                extracted_text.append(format_header + txt + "\n<|endoftext|>\n")
                print(f"   ✓ Extracted {pdf_name}: {len(txt):,} characters ({len(txt.split()):,} words).")
            except Exception as e:
                print(f"   ✗ Error extracting {pdf_name}: {e}")

    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(extracted_text))
    print(f"✓ Saved consolidated ICC Playing Conditions to {out_file} ({os.path.getsize(out_file)/(1024*1024):.2f} MB).")

def filter_cricket_neuro_jsonl(raw_dir: str = "llm/raw_datasets", out_file: str = "llm/data/cricket_neuro_filtered.jsonl"):
    """Filters legacy multi-sport neuro dataset to retain only cricket-specific records."""
    in_file = os.path.join(raw_dir, "neurosport_train_clean.jsonl")
    if not os.path.exists(in_file):
        print(f"Notice: {in_file} not found, skipping JSONL filtering.")
        return

    print("-> Filtering legacy multi-sport JSONL (removing snowboard, hockey, ski noise)...")
    cricket_keywords = [
        "cricket", "bowling", "batsman", "batter", "wicket", "pitch",
        "crease", "stump", "seam", "swing", "spin", "slips", "gully",
        "cover drive", "yorker", "bouncer"
    ]

    kept = 0
    total = 0
    with open(in_file, "r", encoding="utf-8") as inf, open(out_file, "w", encoding="utf-8") as outf:
        for line in inf:
            total += 1
            data = json.loads(line)
            full_text = " ".join(str(v) for v in data.values()).lower()
            if any(kw in full_text for kw in cricket_keywords):
                outf.write(json.dumps(data) + "\n")
                kept += 1

    print(f"✓ Cleaned JSONL: Extracted {kept:,} pure cricket records out of {total:,} ({kept/total*100:.1f}%).")
    print(f"  Discarded {total - kept:,} non-cricket sports records.")
    print(f"  Saved to {out_file} ({os.path.getsize(out_file)/(1024*1024):.2f} MB).")

def index_match_datasets(raw_dir: str = "llm/raw_datasets"):
    """Summarizes available match ball-by-ball JSON datasets."""
    folders = ["tests_json", "odis_json", "t20s_json", "ipl_json"]
    total_matches = 0
    print("\n-> Indexing ball-by-ball match JSON datasets:")
    for f in folders:
        p = os.path.join(raw_dir, f)
        if os.path.exists(p):
            count = len([x for x in os.listdir(p) if x.endswith(".json")])
            total_matches += count
            print(f"   • {f:12s}: {count:,} matches")
    print(f"✓ Total indexed matches: {total_matches:,} international and league matches ready for streaming ingestion.")

if __name__ == "__main__":
    print("======================================================================")
    print("🏏 NEUROSPORT-CRICKET DATASET PRE-PROCESSING & FILTERING")
    print("======================================================================")
    extract_icc_pdfs()
    filter_cricket_neuro_jsonl()
    index_match_datasets()

