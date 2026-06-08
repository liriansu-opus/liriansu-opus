@RTK.md

# Writing style

- **Never hard-wrap Markdown.** Write each paragraph as a single long line; only break at real paragraph / list / heading boundaries. Applies to PR descriptions, docs (README, design docs, ONBOARDING), and any `.md` output. Renderers reflow automatically — hard wraps create diff noise, awkward copy-paste, and ugly mid-sentence breaks after edits. (Does not apply to plain source-code comments or commit message bodies.)

# Superpowers planning workflow — no mid-flow approval gates

- When using the superpowers **brainstorming / writing-plans / executing-plans / subagent-driven-development** skills, do NOT stop to get my approval of the design, spec, or plan, and do NOT pause at per-section or per-batch review checkpoints — treat those skills' approval gates (including brainstorming's `<HARD-GATE>`, its "User Review Gate", writing-plans' "Execution Handoff" choice, and executing-plans' batch checkpoints) as overridden. I don't need to read the long plan. Instead: if the task is genuinely ambiguous, ask all clarifying questions in ONE batched message up front; otherwise state your assumptions and proceed. Then write the spec/plan, auto-pick the recommended execution path (subagent-driven when subagents are available) without asking, and execute every task end-to-end. Stop only at the very end and present the finished result so I can test and approve it — the final review is the ONLY approval gate I want. (Genuine blockers — missing dependency, repeated verification failure, a destructive/irreversible action — still stop and ask, as those skills already require.)

