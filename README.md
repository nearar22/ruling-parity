# RulingParity

Two decisions can cite the same rule and still pull materially similar people in opposite directions. RulingParity makes that inconsistency inspectable: it freezes one governing rule and two published decisions, binds the decisive facts and outcomes to exact quotations, then records whether the pair contains a precedent fork.

The model never supplies the final verdict. Validators agree on the rule criterion, normalized dispositions, and rule-relevant factual similarity. Contract code derives `CONSISTENT`, `PRECEDENT_FORK`, or `INCONCLUSIVE` and seals the result with source digests.

## Lifecycle

`READY → EVALUATED → FINAL`

Evaluation and finalization are permissionless, so a creator cannot strand a review. Missing pages, ambiguous dispositions, forged quotations, or unclear similarity fail closed.

## Check it

```bash
python -m pytest tests -q
genvm-lint lint contracts/ruling_parity.py --json
```

The documents in `docs/` are synthetic smoke-test records, not real rulings or legal advice. Target network: GenLayer Studio Next, chain `61997`.

## Recorded run

- Contract: `0x8a6d6c6d700610FF917cc595F9e836544Bc3BBa6`
- Deployed source equals reviewed source: `true`
- Final review: `parity-demo-mv4a9402`
- Stored result: `PRECEDENT_FORK` / `MATERIALLY_SIMILAR`

`deployment.json` contains the deployment and complete lifecycle transaction hashes.
