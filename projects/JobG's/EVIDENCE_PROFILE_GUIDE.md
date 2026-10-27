# Evidence profile: the first data model

JobG's stores each candidate statement as a **claim** with a short note about its supporting evidence. This gives a future matcher traceable facts to work with instead of treating a skill word in a job description as proof of experience.

## What each field means

| Field | Plain-language meaning | Example to fill in yourself |
|---|---|---|
| `competency` | The skill or capability this supports | `[cloud architecture]` |
| `claim` | A truthful statement about what you did | `I [action you personally performed] for [project/context].` |
| `context` | Where and when the work happened | `[project or role and approximate dates]` |
| `evidence_summary` | What could help you substantiate the claim | `[deliverable, review, metric, or specific example]` |
| `impact_metric` | A measured result, if you have one | `[number and unit, or leave blank]` |
| `source_reference` | A private reminder of where you can check the detail | `[resume section, personal note, or document title]` |
| `evidence_status` | What you have recorded about support for the claim | `self_reported`, `reference_added`, or `supporting_material_noted` |
| `confidentiality` | How cautiously JobG should treat the note | `private` by default; use `confidential` when appropriate |

The evidence status is self-reported metadata. JobG's does not verify that a document exists or that a claim is true. Confidentiality labels are descriptive only: the local app has no login and its SQLite database is not encrypted. Do not paste confidential company documents, customer details, personal information about colleagues, or secrets into the evidence notes. Keep sensitive source materials where they already belong and store only a short description or a reference you can understand later.

## Safe placeholder example

This is a template, not a claim about the candidate. Replace every bracketed part with accurate information or leave optional fields empty:

```python
from evidence_profile import EvidenceClaim, add_evidence_claim

claim = EvidenceClaim(
    competency="[capability]",
    claim="I [specific action] during [project or responsibility].",
    context="[role/project and approximate dates]",
    evidence_summary="[What you can point to or recall to substantiate the claim.]",
    impact_metric="",  # Add only a result you can support.
    source_reference="[Private reminder; do not paste the source document.]",
    evidence_status="self_reported",
    confidentiality="private",
)

claim_id = add_evidence_claim(claim)
print(f"Saved evidence claim {claim_id}")
```

Run `python database.py` first to create the new table. Then run the example from the `jobgs-engine` folder with its virtual environment active. The database and profile stay local and are already excluded from Git.

## Why use Pydantic here?

Pydantic checks the shape of the information before it is saved. For example, it requires a competency, claim, and evidence note; limits how long each field can be; and rejects unknown status values. This is input validation. It does **not** fact-check the candidate's statement.

## Next step

Once the candidate has reviewed and entered accurate claims, a future AI analysis can return each strength or gap with the IDs of supporting claims—or say that it has insufficient evidence. The AI should not upgrade a self-reported claim into an independently verified fact.
