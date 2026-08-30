# RTK - Rust Token Killer

Token-optimized CLI proxy (60-90% savings on dev operations). A Claude Code hook
rewrites commands transparently — `git status` runs as `rtk git status` at zero
token overhead, so never prefix `rtk` by hand.

The exceptions, which must be typed as-is:

```bash
rtk gain              # token savings analytics (--history for per-command)
rtk discover          # scan Claude Code history for missed opportunities
rtk proxy <cmd>       # run raw, unfiltered — for debugging or exact output
```

Setup, verification, and the full command reference live in RTK's own CLAUDE.md.
