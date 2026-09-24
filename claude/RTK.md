# Shell output

- Run shell commands directly by default. Use RTK explicitly for routine test, build, lint, and dependency-install output when a summary is sufficient.
- Keep source/config reads, diffs, structured data, process/CI/runtime status, and searches or listings used for counts or exhaustive coverage unfiltered. Scope queries at the source; never parse or count RTK-filtered output.
- Use native commands or `rtk proxy <cmd>` when exact output matters. Capture raw logs on the original run when replay would repeat mutations or paid work.
