import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from assistant_core import generate_post_call


def combined_text(data):
    parts = [
        data.get("call_summary", ""),
        " ".join(data.get("stakeholders", [])),
        " ".join(data.get("needs_priorities", [])),
        " ".join(data.get("objections_blockers", [])),
        " ".join(data.get("documented_seller_commitments", [])),
        " ".join(data.get("recommended_seller_actions", [])),
        " ".join(data.get("customer_actions", [])),
        " ".join(data.get("dates_timing", [])),
        json.dumps(data.get("crm_note", {})),
        data.get("follow_up_email", ""),
    ]
    return " ".join(parts).lower()


def evaluate_case(case, data):
    checks = []
    expect = case.get("expect", {})
    full = combined_text(data)

    if "documented_commitments_empty" in expect:
        actual = len(data.get("documented_seller_commitments", [])) == 0
        checks.append(("documented_commitments_empty", actual == expect["documented_commitments_empty"]))

    if "customer_actions_empty" in expect:
        actual = len(data.get("customer_actions", [])) == 0
        checks.append(("customer_actions_empty", actual == expect["customer_actions_empty"]))

    if "timing_contains" in expect:
        timing = " ".join(data.get("dates_timing", [])).lower()
        checks.append(("timing_contains", expect["timing_contains"].lower() in timing))

    for phrase in expect.get("email_forbidden_phrases", []):
        checks.append((f"email_forbidden:{phrase}", phrase.lower() not in data.get("follow_up_email", "").lower()))

    for phrase in expect.get("forbidden_summary_phrases", []):
        checks.append((f"forbidden_anywhere:{phrase}", phrase.lower() not in full))

    for phrase in expect.get("forbidden_objection_phrases", []):
        objections = " ".join(data.get("objections_blockers", [])).lower()
        checks.append((f"forbidden_objection:{phrase}", phrase.lower() not in objections))

    if "crm_or_summary_contains_any" in expect:
        target = (
            data.get("call_summary", "")
            + " "
            + json.dumps(data.get("crm_note", {}))
        ).lower()
        ok = any(x.lower() in target for x in expect["crm_or_summary_contains_any"])
        checks.append(("crm_or_summary_contains_any", ok))

    if "customer_actions_contains_any" in expect:
        target = " ".join(data.get("customer_actions", [])).lower()
        ok = any(x.lower() in target for x in expect["customer_actions_contains_any"])
        checks.append(("customer_actions_contains_any", ok))

    return checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", help="Run a single case id.")
    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("Set ANTHROPIC_API_KEY before running live evals.")

    cases_path = Path(__file__).with_name("cases.json")
    cases = json.loads(cases_path.read_text())

    if args.case:
        cases = [c for c in cases if c["id"] == args.case]
        if not cases:
            raise SystemExit(f"No eval case found: {args.case}")

    total_checks = 0
    passed_checks = 0

    for case in cases:
        data = generate_post_call(
            api_key,
            account_name=case["account_name"],
            contact_role=case["contact_role"],
            product_focus=case["product_focus"],
            objective=case["objective"],
            tone=case["tone"],
            raw_notes=case["raw_notes"],
        )

        checks = evaluate_case(case, data)
        case_passed = all(ok for _, ok in checks)

        print(f"\n[{ 'PASS' if case_passed else 'FAIL' }] {case['id']}: {case['description']}")
        for name, ok in checks:
            print(f"  {'✓' if ok else '✗'} {name}")

        total_checks += len(checks)
        passed_checks += sum(1 for _, ok in checks if ok)

    print(f"\nResult: {passed_checks}/{total_checks} checks passed.")
    if passed_checks != total_checks:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
