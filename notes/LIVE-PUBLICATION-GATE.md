# Live publication proof and social release — operations #36

This executable gate supplements the existing protected publication contract;
it does not modify its validators, design, editorial slots or exceptions.

## Run before distribution

Fetch the repository's `main` branch, then run:

```bash
git fetch origin main
python scripts/publication_gate.py \
  --article-url 'https://sayd-magazine.com/posts/ARTICLE/' \
  --candidate-commit FULL_APPROVED_COMMIT_SHA \
  --payload social/queue/APPROVED-PAYLOAD.json \
  --output audit/publication-gate/ARTICLE
```

The candidate must already be an ancestor of fetched `origin/main`. The gate
reads only the published commit's rendered files, never PR working files. It
fetches the production URLs and checks AR/EN/FR, headlines, complete main
content, language navigation, images (binary hashes), homepage placements,
Updates listings, internal category and shared tickers. It also validates
internal article destinations and fragments. A live 200 alone is insufficient.
Any network error, source/live mismatch, absent translation, unmerged commit or
missing social reading link fails closed (exit 1). Reruns delete an earlier
released payload before checking so stale output cannot survive failure.

Payload JSON fields: `platform` (`facebook` or `instagram`), `article_url`
(canonical or existing same-domain short URL), `text` including that exact
reading link, `article_title` (Arabic article identity), `article_image` (hero
identity). Queue files also carry `canonical_article_url` and
`candidate_commit` for CI. This identity metadata does not require copying the
article headline verbatim into a social caption. The gate checks short URLs
against the published `docs/s/links.json` and their live canonical and redirect.

Do not use a queue file itself as a provider payload. Only a fresh
`released-payload.json`, created after verification, is the handoff output.
This artifact includes the validated payload and its publication proof. It
does not send, schedule, or authorize a post. Existing approval, explicit
no-social scopes, format rules and duplicate checks still govern distribution.
Run again immediately before the actual handoff; do not cache proof across
site or payload changes.

## Receipt and review

`receipt.json` records `PUBLISHED` only for the verified site article, never
for social distribution. Social status remains `READY_NOT_SENT` or
`NOT_REQUESTED`; failed attempts record `BLOCKED`. It contains the article's
three URLs, exact approved and candidate commits, timestamp, placements,
images, fetched-byte hashes and ticker state. A provider URL remains null
until a separate actual provider receipt is available. Attach that receipt in
the operations record; never infer it from an absent queue item or CI success.

Without `--review` the receipt explicitly states `NOT_AVAILABLE`. A review
record, if supplied, must name reviewer and evidence URL, report PASS, and
match the exact published commit. The gate records this evidence reference;
it does not authenticate reviewer identity or replace editorial review.

## Automated validation

`live-publication-gate.yml` tests adverse cases, verifies the existing live
European article without releasing any social payload, and rejects the PR
head as an unmerged candidate. Queue changes are validated using the same
code. Verification and blocked receipts are retained as Actions artifacts.
Manual workflow execution supports verify-only and explicit payload release.
The existing European post and repaired links are never modified or resent.

The current distribution service is a ChatGPT merge-event automation using
Metricool/native provider interfaces; it is not a repository-owned sender.
This gate can block its own executable release path. It cannot revoke direct
provider access or intercept a separate native-app publish action. Do not
claim universal prevention or close #36 as fully integrated until the
existing event automation's handoff is confirmed to require this executable
proof. Changing webhook subscriptions or protected contract rules is outside
this patch.
