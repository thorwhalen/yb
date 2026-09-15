# yb.podcast.shownotes

Podcast show notes — the human-readable episode description block.

Same content as a YouTube description, formatted for podcast directories:
title, body, then a chapters list (`M:SS Title`) when chapters are present.

### Functions

| [`format_show_notes`](#yb.podcast.shownotes.format_show_notes)(content, \*[, include_chapters])   | Render show notes (title + description + optional chapters) as text.   |
|-------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------|

### yb.podcast.shownotes.format_show_notes(content, , include_chapters=True)

Render show notes (title + description + optional chapters) as text.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
