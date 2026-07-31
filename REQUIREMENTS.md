# Module 1 requirements

The CLI accepts project folder/name, configuration folder, output folder, dry-run, and
verbose options. It inventories supported and unknown files, hashes every readable file,
classifies by external configuration, inspects KMZ safely, evaluates configured data
gaps, logs actions, and verifies hashes after processing.

Required reports are inventory, source register, gap report, summary, integrity report,
and run log. CSV and JSON are mandatory. XLSX is conditional on an already available
`openpyxl` installation. Dry-run performs analysis but writes nothing.

The implementation must be cross-platform Python, typed and understandable, use
synthetic tests, perform no network activity, and never write below the scanned source
folder. Full acceptance tests are documented in `docs/test_plan.md`.
