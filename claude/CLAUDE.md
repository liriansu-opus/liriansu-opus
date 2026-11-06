# Public repositories

- Treat every push to a public repo, including dotfiles, as irreversible: rewritten objects may remain reachable by SHA.
- Before committing, scan the full diff, commit message, PR text, and comments for employer/client/private-infrastructure identifiers: orgs, repos, codenames, internal hosts/URLs, ticket IDs, credentials, and revealing absolute paths. Replace them with neutral placeholders such as `my-org` or `my-project`.

# Writing

- Do not hard-wrap Markdown prose; break at paragraphs, lists, or headings. Source comments and commit bodies are exempt.

# Memory

- Save only durable, cross-session, non-obvious preferences, policies, or recurring gotchas. Never save snapshots, ticket state, or one-off investigations; use Linear or repo docs. Keep one fact per memory (at most 300 tokens); ask when unsure.

# Second opinions

- When I say "问一下 gemini" or "问一下 codex", ask through the local CLI and relay the reply as that model's answer: `agy -p "<question>"` for Gemini, `codex exec "<question>"` for Codex. Put the needed context in the prompt, and run from a neutral directory unless the question is about the code.

# Peer sessions

- When another session may be touching the same work, run `ListAgents` and use `SendMessage` to ask what it is changing. Agree who owns what before continuing. Discussions makes perfect.
- Session-to-session traffic is not for me. When a peer message needs nothing from me, handle it silently: reply to the peer if it needs a reply, then end the turn with no text. Don't summarize the exchange, report that nothing was needed, or repeat my open questions.
