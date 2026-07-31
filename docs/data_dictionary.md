# Data dictionary

## File inventory

`file_name`, `full_path`, `relative_path`, `extension`, `size_bytes`, `modified_at`, `likely_category`, `classification_confidence`, `source_type`, `file_status`, `review_notes`, `is_readable`, `file_role`, `sha256`, and `inventory_run_at` describe each discovered file. `kmz_details` is compact JSON for KMZ validity, KML members, feature counts, and approximate bounds.

## Source register

One row per inventory item records its path, inferred category, source type, hash, role, and notes. Unknown provenance is never invented.

## Gap report

One row per configured category records required status, matched file count, screening status, and notes. Missing required categories are FAIL; missing optional categories and uncertain matches are REVIEW.

## Integrity report

Records before/after hashes, changed/missing/unreadable paths, and `source_changes_expected` (always zero). `integrity_confirmed` is true only when no source difference is detected.
