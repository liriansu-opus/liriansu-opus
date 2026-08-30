@RTK.md

# Public repositories

- Treat every push to a public repo, including dotfiles, as irreversible: rewritten objects may remain reachable by SHA.
- Before committing, scan the full diff, commit message, PR text, and comments for employer/client/private-infrastructure identifiers: orgs, repos, codenames, internal hosts/URLs, ticket IDs, credentials, and revealing absolute paths. Replace them with neutral placeholders such as `my-org` or `my-project`.

# Writing

- Do not hard-wrap Markdown prose; break at paragraphs, lists, or headings. Source comments and commit bodies are exempt.

# Superpowers

- Skip design, plan, handoff, section, and batch approval gates. Ask genuine ambiguities once; otherwise state assumptions, choose the recommended path, use subagents when helpful, and execute end-to-end. Stop only for genuine blockers or final review.

# Memory

- Save only durable, cross-session, non-obvious preferences, policies, or recurring gotchas. Never save snapshots, ticket state, or one-off investigations; use Linear or repo docs. Keep one fact per memory (at most 300 tokens); ask when unsure.
