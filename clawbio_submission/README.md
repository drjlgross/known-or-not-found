# ClawBio submission (staging copy, not registered)

`skills/literature-triage/` is laid out exactly as it would be in a ClawBio fork (`ClawBio/skills/literature-triage/`).
It has **not** been submitted or registered: nothing here touches the real ClawBio repo.

To submit (a human step):
1. Fork ClawBio and copy `skills/literature-triage/` into the fork's `skills/`.
2. Add the test path to `pytest.ini`, register the alias in `clawbio.py` (SKILLS dict), and run `python scripts/generate_catalog.py`.
3. `python -m pytest skills/literature-triage/tests/ -v` and `python skills/literature-triage/literature_triage.py --demo --output /tmp/lit_triage_demo`.
4. Open a **draft** PR with ClawBio's PR template. Flag: (a) live mode depends on the authenticated Paperclip service
   (CONTRIBUTING says network calls only for public databases), and (b) bins are provisional until hand grading finishes.
