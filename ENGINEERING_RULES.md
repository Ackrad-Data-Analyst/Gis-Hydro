# Engineering and safety rules

## Screening states

- **PASS:** readable file confidently matches a configured expected category.
- **REVIEW:** readable, but category, source, units, CRS, purpose, or suitability is uncertain.
- **FAIL:** unreadable file or missing configured critical category.

An absent optional category is REVIEW, not project failure. These are draft intake rules,
not engineering validation. All engineering decisions are **REVIEW REQUIRED**.

## Source protection

Source files are opened in binary read mode. KMZ contents are read directly from the ZIP
without extraction. Output paths at or below the source root are rejected. Hashes are
calculated before and after analysis, and the integrity report expects zero changes.
The application does not write, rename, move, or delete sources and makes no network calls.
