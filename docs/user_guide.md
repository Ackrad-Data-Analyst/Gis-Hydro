# User guide

1. Keep approved source material in a dedicated read-only folder.
2. Choose a separate output folder; the CLI rejects output at or inside the source folder.
3. Review the JSON-compatible YAML rules in `config/` and retain the draft notice.
4. Run the command shown in `README.md`.
5. Check `source_integrity_report.json` first, then review every FAIL and REVIEW row.

PASS means only a readable file confidently matched a filename rule. It does **not** validate CRS, units, datum, accuracy, coverage, currency, or engineering suitability. Unknown provenance and all engineering conclusions are REVIEW REQUIRED. A dry run prints a summary and creates no folders or files. KMZ inspection occurs in memory without extracting content.
