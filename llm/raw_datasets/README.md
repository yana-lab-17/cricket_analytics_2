# 📂 NeuroSport-Cricket Raw Datasets Directory

This directory holds the raw input datasets for continuous pre-training.

### Included in Repository:
- **`test_conditions.pdf`**: Official ICC Men's Test Match Playing Conditions.
- **`odi_conditions.pdf`**: Official ICC Men's ODI Playing Conditions.
- **`t20_conditions.pdf`**: Official ICC Men's T20I Playing Conditions.
- **`illegal_actions.pdf`**: ICC Regulations for the Review of Bowlers with Suspected Illegal Bowling Actions.
- **`code_of_conduct.pdf`**: ICC Official Code of Conduct for Players and Support Personnel.

### Ignored / External Large Datasets:
The heavy raw ball-by-ball JSON match archives and multi-sport logs are excluded from git history to keep the repository lightweight:
- `tests_json/`: Ball-by-ball Test match JSON files (downloadable from [Cricsheet](https://cricsheet.org/downloads/)).
- `odis_json/`: Ball-by-ball ODI match JSON files (downloadable from Cricsheet).
- `t20s_json/`: Ball-by-ball T20 International JSON files (downloadable from Cricsheet).
- `ipl_json/`: Ball-by-ball Indian Premier League JSON files (downloadable from Cricsheet).

The compiled clean corpora:
- `llm/data/icc_official_rules.txt`: Extracted consolidated text from the ICC PDFs.
- `llm/data/cricket_neuro_filtered.jsonl`: 33,300 pure cricket neuroscience coaching telemetry records.
are automatically ingested by `llm/data/dataset_builder.py`.
