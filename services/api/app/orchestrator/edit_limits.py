"""Shared fixed source-edit capabilities; no orchestration or provider dependencies."""

MAX_EDITS = 40
MAX_NEW_LINES_PER_EDIT = 120
MAX_NEW_LINES = 600
MAX_EDIT_BYTES = 24_000

EDIT_BUDGET_DESCRIPTION = (
    f"Maximum {MAX_EDITS} edits, {MAX_NEW_LINES_PER_EDIT} new lines per edit, "
    f"{MAX_NEW_LINES} new lines and {MAX_EDIT_BYTES} UTF-8 bytes total."
)
