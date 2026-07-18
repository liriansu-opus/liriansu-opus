@RTK.md

# Public repos

- Treat every push to a public repo as irreversible: a later history rewrite does not retract it, because the old objects stay reachable by commit SHA until the host garbage-collects them. The check belongs before the commit, not after.
- So before committing to a public repo — this dotfiles repo included — scan the whole diff for anything tied to my employer, clients, or private infrastructure: org and repo names, project codenames, internal hostnames or URLs, ticket IDs, credentials, and absolute paths that expose any of them. Substitute a neutral placeholder (`my-org`, `my-project`) rather than the real name, and apply the same check to commit messages, PR text, and code comments — an offhand example inside a comment is the easiest way to slip.

# Writing style

- Never hard-wrap Markdown prose; break only at paragraphs, lists, or headings. Source comments and commit-message bodies are exempt.

# Superpowers workflow

- For superpowers brainstorming, planning, and execution skills, skip design, plan, handoff, section, and batch approval gates. Ask genuine ambiguities once up front; otherwise state assumptions, choose the recommended path, prefer subagent-driven execution when available, and execute end-to-end. Stop only for genuine blockers or final review.

# Memory discipline

Save only durable, cross-session, non-obvious user preferences, policies, or recurring gotchas. Never save project snapshots, task or ticket state, or one-off investigations; use Linear or repo docs. Keep one fact per memory (at most about 300 tokens); when unsure, ask first.
