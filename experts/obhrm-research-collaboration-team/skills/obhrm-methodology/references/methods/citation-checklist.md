# Final Citation and Submission Audit

Use `citation-workflow.md` for discovery and metadata verification. Use this file only for the final audit.

## Citation Audit

- Every LaTeX citation key exists exactly once in the declared BibTeX file.
- Every cited key has a row in `citation_verification.md` with status `verified`, `software-doc`, or `repository-verified`.
- Title, first author, year, venue/preprint source, and DOI/arXiv identifier agree with authoritative metadata.
- The paper or abstract supports the sentence-level relation recorded as `direct`, `background`, `contrast`, or `software`.
- Strong claims do not rely on `background`, `weak`, `metadata-only`, or placeholder records.
- Concurrent work and secondary sources are described with appropriately scoped language.

Run:

```bash
python3 ../../scripts/format_citation_report.py main.tex --crossref crossref.json
```

This checks internal keys and input completeness. Metadata and claim support still require the verification workflow and human review.

## Venue Checklist

Use the checklist matching the actual venue/template. Cover applicable items explicitly:

- limitations and failure modes;
- datasets, splits, metrics, baselines, seeds, uncertainty, and compute;
- code/data/model availability and licenses;
- ethics, privacy, human subjects, safety, and broader impacts;
- LLM or AI-assistance disclosure;
- maintenance and consent for newly released assets.

An honest `No` plus a concrete limitation is better than an unsupported `Yes`.

## Final Commands

```bash
python3 ../../scripts/format_citation_report.py main.tex --crossref crossref.json
```

Before commit or push, inspect Git status, staged files, generated binary sizes, and confidential material.
