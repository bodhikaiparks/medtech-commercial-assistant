import json
import re
from typing import Any, Dict, List

import anthropic


MODEL = "claude-sonnet-5"


PRE_CALL_SYSTEM = """
You are an AI assistant for ethical B2B medical technology account preparation.

Use only information supplied by the user as known facts.
Do not invent account-specific people, contracts, purchasing arrangements, volumes, or clinical circumstances.
Clearly label assumptions as hypotheses.
Do not provide medical advice.
Do not request or use protected health information.

Return ONLY valid JSON with exactly this structure:

{
  "account_snapshot": ["string"],
  "stakeholder_roles": ["string"],
  "hypotheses": ["string"],
  "discovery_questions": ["string"],
  "call_plan": {
    "opening": "string",
    "middle": "string",
    "close": "string",
    "desired_next_step": "string"
  },
  "risks_information_gaps": ["string"],
  "crm_note": {
    "account": "string",
    "status": "string",
    "objective": "string",
    "plan": "string",
    "next_step": "string",
    "open_risks": "string"
  }
}

Do not wrap the JSON in Markdown fences.
""".strip()


POST_CALL_SYSTEM = """
You are an AI assistant for ethical B2B medical technology sales documentation.

Work only from the user's supplied notes.
Do not invent names, dates, commitments, objections, evaluation requirements, product claims, or account facts.
If something is unclear, mark it unclear or unknown.
Do not provide medical advice.
Do not request or use protected health information.
Do not include unsupported clinical claims.

A customer request is NOT a seller commitment unless the notes explicitly say the seller agreed or promised to do it.

Return ONLY valid JSON with exactly this structure:

{
  "call_summary": "string",
  "stakeholders": ["string"],
  "needs_priorities": ["string"],
  "objections_blockers": ["string"],
  "documented_seller_commitments": ["string"],
  "recommended_seller_actions": ["string"],
  "customer_actions": ["string"],
  "dates_timing": ["string"],
  "crm_note": {
    "contact_role": "string",
    "summary": "string",
    "key_issue": "string",
    "next_step": "string",
    "timing": "string"
  },
  "follow_up_email": "string"
}

Rules:
- documented_seller_commitments: include ONLY explicit seller promises from the notes. Otherwise return [].
- recommended_seller_actions: reasonable inferred next steps, clearly as recommendations.
- customer_actions: only actions explicitly stated, agreed, or requested of the customer. Do not turn a request made by the customer into a customer action.
- follow_up_email: do not invent promises. If an action is only recommended and not documented as a seller commitment, use language such as "I can send", "I can provide", or "I can coordinate".
- Do not use "I will", "I'll", "we will", or "we'll" for any action that is not explicitly documented as a seller commitment.
- Do not wrap JSON in Markdown fences.
""".strip()


class AssistantError(Exception):
    """User-safe application error."""


def clean_filename(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", (value or "account").strip())
    return value.strip("_") or "account"


def parse_json_response(text: str) -> Dict[str, Any]:
    text = (text or "").strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError as exc:
                raise AssistantError("Claude returned malformed structured output. Please try again.") from exc

    raise AssistantError("Claude returned an unexpected format. Please try again.")


def _require_dict(data: Dict[str, Any], key: str) -> Dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise AssistantError(f"Structured output is missing '{key}'. Please try again.")
    return value


def _require_list(data: Dict[str, Any], key: str) -> List[Any]:
    value = data.get(key)
    if not isinstance(value, list):
        raise AssistantError(f"Structured output is missing '{key}'. Please try again.")
    return value


def validate_pre_call(data: Dict[str, Any]) -> Dict[str, Any]:
    for key in [
        "account_snapshot",
        "stakeholder_roles",
        "hypotheses",
        "discovery_questions",
        "risks_information_gaps",
    ]:
        _require_list(data, key)

    call_plan = _require_dict(data, "call_plan")
    crm_note = _require_dict(data, "crm_note")

    for key in ["opening", "middle", "close", "desired_next_step"]:
        if key not in call_plan:
            raise AssistantError(f"Structured output is missing call-plan field '{key}'.")

    for key in ["account", "status", "objective", "plan", "next_step", "open_risks"]:
        if key not in crm_note:
            raise AssistantError(f"Structured output is missing CRM field '{key}'.")

    return data


def validate_post_call(data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(data.get("call_summary"), str):
        raise AssistantError("Structured output is missing the call summary.")

    for key in [
        "stakeholders",
        "needs_priorities",
        "objections_blockers",
        "documented_seller_commitments",
        "recommended_seller_actions",
        "customer_actions",
        "dates_timing",
    ]:
        _require_list(data, key)

    crm_note = _require_dict(data, "crm_note")
    for key in ["contact_role", "summary", "key_issue", "next_step", "timing"]:
        if key not in crm_note:
            raise AssistantError(f"Structured output is missing CRM field '{key}'.")

    if not isinstance(data.get("follow_up_email"), str):
        raise AssistantError("Structured output is missing the follow-up email.")

    return data


def call_claude(
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    model: str = MODEL,
) -> str:
    if not api_key:
        raise AssistantError("Add your Anthropic API key in the sidebar first.")

    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except anthropic.AuthenticationError as exc:
        raise AssistantError("Anthropic rejected the API key. Check the key and try again.") from exc
    except anthropic.RateLimitError as exc:
        raise AssistantError("Anthropic rate limit reached. Wait briefly and try again.") from exc
    except anthropic.APIConnectionError as exc:
        raise AssistantError("Could not connect to the Anthropic API. Check your internet connection and try again.") from exc
    except anthropic.APIStatusError as exc:
        request_id = getattr(exc, "request_id", None)
        suffix = f" Request ID: {request_id}" if request_id else ""
        raise AssistantError(
            f"Anthropic API error ({getattr(exc, 'status_code', 'unknown status')}).{suffix}"
        ) from exc

    return "\n".join(
        block.text
        for block in response.content
        if getattr(block, "type", None) == "text"
    )


def normalize_email(email_text: str, has_documented_commitments: bool) -> str:
    email_text = (email_text or "").strip()

    if not has_documented_commitments:
        replacements = [
            (r"\bI will send\b", "I can send"),
            (r"\bI'll send\b", "I can send"),
            (r"\bI will provide\b", "I can provide"),
            (r"\bI'll provide\b", "I can provide"),
            (r"\bI will share\b", "I can share"),
            (r"\bI'll share\b", "I can share"),
            (r"\bI will coordinate\b", "I can coordinate"),
            (r"\bI'll coordinate\b", "I can coordinate"),
            (r"\bwe will send\b", "we can send"),
            (r"\bwe'll send\b", "we can send"),
            (r"\bwe will provide\b", "we can provide"),
            (r"\bwe'll provide\b", "we can provide"),
        ]
        for pattern, replacement in replacements:
            email_text = re.sub(pattern, replacement, email_text, flags=re.IGNORECASE)

    return email_text


def build_pre_call_prompt(
    account_name: str,
    account_type: str,
    specialty: str,
    product_focus: str,
    current_context: str,
    objective: str,
    notes: str,
) -> str:
    return f"""
<account>
<name>{account_name}</name>
<type>{account_type}</type>
<specialty>{specialty}</specialty>
<product_focus>{product_focus}</product_focus>
</account>

<context>{current_context}</context>
<objective>{objective}</objective>
<previous_notes>{notes}</previous_notes>

Create the pre-call output.
""".strip()


def build_post_call_prompt(
    account_name: str,
    contact_role: str,
    product_focus: str,
    objective: str,
    tone: str,
    raw_notes: str,
) -> str:
    return f"""
<account>
<name>{account_name}</name>
<primary_contact_or_role>{contact_role}</primary_contact_or_role>
<product_focus>{product_focus}</product_focus>
</account>

<original_objective>{objective}</original_objective>
<requested_email_tone>{tone}</requested_email_tone>

<raw_call_notes>
{raw_notes}
</raw_call_notes>

Create the structured post-call output.
""".strip()


def generate_pre_call(api_key: str, **kwargs) -> Dict[str, Any]:
    prompt = build_pre_call_prompt(**kwargs)
    raw = call_claude(api_key, PRE_CALL_SYSTEM, prompt, max_tokens=2200)
    return validate_pre_call(parse_json_response(raw))


def generate_post_call(api_key: str, **kwargs) -> Dict[str, Any]:
    prompt = build_post_call_prompt(**kwargs)
    raw = call_claude(api_key, POST_CALL_SYSTEM, prompt, max_tokens=2400)
    data = validate_post_call(parse_json_response(raw))
    documented = data.get("documented_seller_commitments", [])
    data["follow_up_email"] = normalize_email(
        data.get("follow_up_email", ""),
        bool(documented),
    )
    return data


def bullet_list(items, empty_text="None documented."):
    if not items:
        return f"- {empty_text}"
    return "\n".join(f"- {item}" for item in items)


def format_pre_crm(crm: Dict[str, Any]) -> str:
    return "\n".join([
        f"Account: {crm.get('account', '')}",
        f"Status: {crm.get('status', '')}",
        f"Objective: {crm.get('objective', '')}",
        f"Plan: {crm.get('plan', '')}",
        f"Next step: {crm.get('next_step', '')}",
        f"Open risks: {crm.get('open_risks', '')}",
    ])


def format_post_crm(crm: Dict[str, Any]) -> str:
    return "\n".join([
        f"Contact / role: {crm.get('contact_role', '')}",
        f"Summary: {crm.get('summary', '')}",
        f"Key issue: {crm.get('key_issue', '')}",
        f"Next step: {crm.get('next_step', '')}",
        f"Timing: {crm.get('timing', '')}",
    ])
