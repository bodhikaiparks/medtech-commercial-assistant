# Evaluation

This project includes two levels of testing.

## 1. Deterministic unit tests

`tests/test_core.py` tests code that should behave consistently without calling Claude.

Examples:
- fenced JSON parsing
- filename sanitization
- multi-line CRM formatting
- promise-language normalization
- schema validation failures

Run:

```bash
pytest -q
```

## 2. Live behavioral evaluations

`evals/cases.json` contains fictional scenarios designed to test common failure modes.

The current suite includes cases for:
- customer request incorrectly becoming seller commitment
- explicit seller commitment being preserved
- unknown approver remaining unknown
- tentative trial interest not becoming a confirmed trial
- competitor usage not becoming an invented rejection
- customer request not becoming a customer action
- stated timing being preserved
- unnamed stakeholders remaining unnamed
- unsupported clinical claims not being invented
- explicit customer actions being captured

Run:

```bash
export ANTHROPIC_API_KEY="your_key_here"
python evals/run_evals.py
```

## What the live harness checks

The harness uses simple behavioral assertions, such as:
- commitment list should be empty when no commitment was documented
- forbidden promise phrases should not appear
- stated timing should appear in the timing field
- unsupported claims should not appear
- explicit customer actions should be preserved

These checks are intentionally transparent and easy to inspect.

## Limits of the evaluation

This is not a formal safety benchmark and does not prove correctness.

The suite is designed to:
- catch regressions
- document expected behavior
- demonstrate a repeatable testing approach
- provide a foundation for future evaluation expansion

Future work could add:
- larger eval sets
- scoring rubrics
- model-to-model comparisons
- human reviewer scoring
- precision/recall measures for extracted commitments
