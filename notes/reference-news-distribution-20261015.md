# Editorial distribution decision — 15 October 2026

Approved by Nayef: encyclopaedia entries and hunting-law explainers must be published only in their dedicated category, never automatically promoted to **Updates** or the news ticker. Science & Discoveries studies remain in Science unless Nayef explicitly approves that specific item for a specific featured, Updates or ticker placement; such approval must be recorded in `content/homepage.json -> editorial_distribution_policy.approved_science_news`.

The 15 October legal explainers about Lebanon, Qatar and Oman were removed from the eight Updates slots and retained in the Laws archive. The vacated three positions now show separately published hunting/protection news with their original dates; no bird encyclopaedia entry or scientific study was added.

Safeguards:
- `scripts/editorial_distribution_policy.py`: classify only the MAIN category listing, never globally replicated ticker links; categorization falls back to `primary_door`.
- `scripts/refresh_homepage_doors.py` and `scripts/check_publication_contract.py`: reject prohibited placements.
- `scripts/homepage_demotion.py`: filter reference content when an approved production config is supplied.
- `.github/workflows/reference-news-guard.yml`: check that the gate refuses laws, bird encyclopaedia and unapproved science news, while allowing explicitly whitelisted science.

No magazine article was deleted, and no social-platform post is authorized by this change.
