import streamlit as st

from assistant_core import (
    AssistantError,
    MODEL,
    bullet_list,
    clean_filename,
    format_post_crm,
    format_pre_crm,
    generate_post_call,
    generate_pre_call,
)

st.set_page_config(
    page_title="MedTech Commercial Assistant",
    page_icon="🩺",
    layout="wide",
)

def render_copyable(label, content):
    st.markdown(f"**{label}**")
    st.code(content, language=None, wrap_lines=True)

st.title("🩺 MedTech Commercial Assistant")
st.markdown(
    "A portfolio project using the **Claude API** for structured "
    "**pre-call planning** and **post-call documentation** in MedTech sales."
)

with st.expander("About this project"):
    st.markdown(
        """
This project explores a practical use of generative AI in MedTech commercialization.

It is designed to:
- separate **known account facts** from **hypotheses**
- separate **documented commitments** from **recommended next actions**
- avoid inventing account-specific people, contracts, dates, or commitments
- keep human review in the loop before CRM entry or customer communication

**Do not enter PHI, patient-identifiable information, confidential customer data,
proprietary pricing, or information you are not authorized to process.**
"""
    )

with st.sidebar:
    st.header("Setup")
    api_key = st.text_input(
        "Anthropic API key",
        type="password",
        value="",
        help="Keep this private. Never commit an API key to GitHub.",
    )
    st.caption(f"Model: {MODEL}")
    st.divider()
    st.caption("Python · Streamlit · Anthropic SDK · Claude API")
    st.warning(
        "Do not enter PHI, patient-identifiable information, confidential customer data, "
        "proprietary pricing, or information you are not authorized to process."
    )

pre_tab, post_tab = st.tabs(["📋 Pre-Call Prep", "📝 Post-Call Notes"])

with pre_tab:
    st.subheader("Pre-Call Account Preparation")

    c1, c2 = st.columns(2)

    with c1:
        account_name = st.text_input("Account / organization", key="pre_account")
        account_type = st.selectbox(
            "Account type",
            ["Hospital", "ASC", "Physician Practice", "Health System", "Other"],
            key="pre_type",
        )
        specialty = st.text_input("Specialty / department", key="pre_specialty")
        product_focus = st.text_input("Product / solution focus", key="pre_product")

    with c2:
        current_context = st.text_area("What do you already know?", height=120, key="pre_context")
        objective = st.text_area("Objective for the call", height=120, key="pre_objective")

    notes = st.text_area("Optional previous notes", height=110, key="pre_notes")

    if st.button("Generate pre-call brief", type="primary", use_container_width=True):
        if not account_name.strip():
            st.error("Enter an account or organization name.")
        else:
            try:
                with st.spinner("Building pre-call brief..."):
                    st.session_state["pre_data"] = generate_pre_call(
                        api_key,
                        account_name=account_name,
                        account_type=account_type,
                        specialty=specialty,
                        product_focus=product_focus,
                        current_context=current_context,
                        objective=objective,
                        notes=notes,
                    )
            except AssistantError as exc:
                st.error(str(exc))

    if st.session_state.get("pre_data"):
        d = st.session_state["pre_data"]
        st.success("Pre-call brief generated.")

        st.markdown("# 1. ACCOUNT SNAPSHOT")
        st.markdown(bullet_list(d.get("account_snapshot", [])))

        st.markdown("# 2. LIKELY STAKEHOLDER ROLES")
        st.markdown(bullet_list(d.get("stakeholder_roles", [])))

        st.markdown("# 3. HYPOTHESES TO VALIDATE")
        hypotheses = d.get("hypotheses", [])
        st.markdown(
            "\n".join(f"- **Hypothesis:** {h}" for h in hypotheses)
            if hypotheses
            else "- None generated."
        )

        st.markdown("# 4. DISCOVERY QUESTIONS")
        questions = d.get("discovery_questions", [])
        st.markdown("\n".join(f"{i + 1}. {q}" for i, q in enumerate(questions)))

        st.markdown("# 5. CALL PLAN")
        cp = d.get("call_plan", {})
        st.markdown(f"**Opening:** {cp.get('opening', '')}")
        st.markdown(f"**Middle:** {cp.get('middle', '')}")
        st.markdown(f"**Close:** {cp.get('close', '')}")
        st.markdown(f"**Desired next step:** {cp.get('desired_next_step', '')}")

        st.markdown("# 6. RISKS / INFORMATION GAPS")
        st.markdown(bullet_list(d.get("risks_information_gaps", [])))

        st.markdown("# 7. CRM-READY PRE-CALL NOTE")
        crm_text = format_pre_crm(d.get("crm_note", {}))
        render_copyable("CRM-ready pre-call note", crm_text)

        full_report = (
            "# 1. ACCOUNT SNAPSHOT\n" + bullet_list(d.get("account_snapshot", []))
            + "\n\n# 2. LIKELY STAKEHOLDER ROLES\n" + bullet_list(d.get("stakeholder_roles", []))
            + "\n\n# 3. HYPOTHESES TO VALIDATE\n"
            + ("\n".join(f"- Hypothesis: {h}" for h in hypotheses) if hypotheses else "- None generated.")
            + "\n\n# 4. DISCOVERY QUESTIONS\n"
            + "\n".join(f"{i + 1}. {q}" for i, q in enumerate(questions))
            + "\n\n# 5. CALL PLAN\n"
            + f"Opening: {cp.get('opening', '')}\n"
            + f"Middle: {cp.get('middle', '')}\n"
            + f"Close: {cp.get('close', '')}\n"
            + f"Desired next step: {cp.get('desired_next_step', '')}\n\n"
            + "# 6. RISKS / INFORMATION GAPS\n" + bullet_list(d.get("risks_information_gaps", []))
            + "\n\n# 7. CRM-READY PRE-CALL NOTE\n" + crm_text
        )

        st.download_button(
            "⬇️ Download full pre-call brief",
            full_report,
            file_name=f"{clean_filename(account_name)}_pre_call_brief.md",
            mime="text/markdown",
            use_container_width=True,
        )

with post_tab:
    st.subheader("Post-Call Documentation")

    c1, c2 = st.columns(2)

    with c1:
        post_account = st.text_input("Account / organization", key="post_account")
        contact_role = st.text_input("Primary contact / role", key="post_contact")
        product_focus_post = st.text_input("Product / solution focus", key="post_product")

    with c2:
        call_objective = st.text_area("Original call objective", height=110, key="post_objective")
        tone = st.selectbox(
            "Follow-up email tone",
            ["Professional and concise", "Warm and conversational", "Direct and action-oriented"],
            key="post_tone",
        )

    raw_notes = st.text_area("Paste your rough call notes", height=230, key="post_notes")

    if st.button("Process post-call notes", type="primary", use_container_width=True):
        if not post_account.strip():
            st.error("Enter an account or organization name.")
        elif not raw_notes.strip():
            st.error("Paste your rough call notes.")
        else:
            try:
                with st.spinner("Structuring call notes..."):
                    st.session_state["post_data"] = generate_post_call(
                        api_key,
                        account_name=post_account,
                        contact_role=contact_role,
                        product_focus=product_focus_post,
                        objective=call_objective,
                        tone=tone,
                        raw_notes=raw_notes,
                    )
            except AssistantError as exc:
                st.error(str(exc))

    if st.session_state.get("post_data"):
        d = st.session_state["post_data"]
        documented = d.get("documented_seller_commitments", [])
        recommended = d.get("recommended_seller_actions", [])
        email_text = d.get("follow_up_email", "")

        st.success("Post-call documentation generated.")

        st.markdown("# 1. CALL SUMMARY")
        st.markdown(d.get("call_summary", ""))

        st.markdown("# 2. STAKEHOLDERS / ROLES IDENTIFIED")
        st.markdown(bullet_list(d.get("stakeholders", []), "None identified."))

        st.markdown("# 3. NEEDS / PRIORITIES")
        st.markdown(bullet_list(d.get("needs_priorities", []), "None documented."))

        st.markdown("# 4. OBJECTIONS / BLOCKERS")
        st.markdown(bullet_list(d.get("objections_blockers", []), "No explicit blockers documented."))

        st.markdown("# 5. COMMITMENTS / NEXT STEPS")
        st.markdown("## Documented seller commitments")
        st.markdown(bullet_list(documented, "None documented."))

        st.markdown("## Recommended seller actions")
        st.markdown(bullet_list(recommended, "No recommendations generated."))

        st.markdown("## Customer actions")
        st.markdown(bullet_list(d.get("customer_actions", []), "None documented."))

        st.markdown("## Dates / timing mentioned")
        st.markdown(bullet_list(d.get("dates_timing", []), "None documented."))

        st.markdown("# 6. CRM-READY POST-CALL NOTE")
        crm_text = format_post_crm(d.get("crm_note", {}))
        render_copyable("CRM-ready post-call note", crm_text)

        st.markdown("# 7. FOLLOW-UP EMAIL")
        st.markdown(email_text)

        st.divider()
        st.subheader("Quick Copy")

        q1, q2 = st.columns(2)

        with q1:
            render_copyable("CRM-ready post-call note", crm_text)

        with q2:
            render_copyable("Follow-up email", email_text)

        full_report = (
            "# 1. CALL SUMMARY\n" + d.get("call_summary", "")
            + "\n\n# 2. STAKEHOLDERS / ROLES IDENTIFIED\n" + bullet_list(d.get("stakeholders", []), "None identified.")
            + "\n\n# 3. NEEDS / PRIORITIES\n" + bullet_list(d.get("needs_priorities", []), "None documented.")
            + "\n\n# 4. OBJECTIONS / BLOCKERS\n" + bullet_list(d.get("objections_blockers", []), "No explicit blockers documented.")
            + "\n\n# 5. COMMITMENTS / NEXT STEPS\n\n"
            + "## Documented seller commitments\n" + bullet_list(documented, "None documented.")
            + "\n\n## Recommended seller actions\n" + bullet_list(recommended, "No recommendations generated.")
            + "\n\n## Customer actions\n" + bullet_list(d.get("customer_actions", []), "None documented.")
            + "\n\n## Dates / timing mentioned\n" + bullet_list(d.get("dates_timing", []), "None documented.")
            + "\n\n# 6. CRM-READY POST-CALL NOTE\n" + crm_text
            + "\n\n# 7. FOLLOW-UP EMAIL\n" + email_text
        )

        st.download_button(
            "⬇️ Download full post-call report",
            full_report,
            file_name=f"{clean_filename(post_account)}_post_call_report.md",
            mime="text/markdown",
            use_container_width=True,
        )

st.divider()
st.caption(
    "Built with Python, Streamlit, and the Claude API. "
    "Human review is required before CRM entry or customer communication."
)
