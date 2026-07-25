See AGENTS.md for the operational guide to this repo.


<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Issue Tracking

This project uses **bd (beads)**. `bd prime` carries the workflow and session-close protocol —
the beads hooks inject it at session start, so this block is only the pointer.

```bash
bd ready                     # unblocked work
bd show <id>                 # detail
bd create "Title" --type=task --priority=2
bd close <id>                # complete
```

Track work in beads rather than TodoWrite/TaskCreate, and create the bead before the code.
<!-- END BEADS INTEGRATION -->
