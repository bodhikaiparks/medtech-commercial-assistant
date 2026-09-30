# Design Decisions

## 1. Structured JSON instead of free-form Markdown

Early versions asked Claude to produce final Markdown sections directly. During testing, the model occasionally renamed headings or collapsed distinctions such as "documented seller commitments" versus "recommended seller actions."

The final architecture asks Claude for structured JSON and lets the application render the final interface.

**Why:** better consistency, easier testing, clearer separation of model behavior from UI behavior.

## 2. Facts and hypotheses remain separate

Pre-call preparation can easily drift into unsupported account assumptions. The prompt therefore treats supplied information as known facts and requires plausible but unverified ideas to remain hypotheses.

## 3. Requests are not commitments

A customer asking for pricing does not mean the seller promised to send pricing. The post-call workflow explicitly separates:
- documented seller commitments
- recommended seller actions
- customer actions
- dates and timing

This distinction was added after adversarial testing exposed the risk of inference-to-commitment drift.

## 4. Human review remains required

The application does not automatically write to a CRM or send an email.

That is deliberate. The generated output is decision support, not an autonomous customer-facing action.

## 5. Public account research is excluded from the first release

External research could make the project more capable, but it also adds:
- source-quality questions
- stale-data risk
- entity-matching risk
- privacy considerations
- citation requirements

It is kept on the roadmap until those controls are designed explicitly.
