# Throughline

A [SilverBullet](https://silverbullet.md) library for project tracking where
tasks, projects and the notes you take while doing them live in one place, as
plain markdown.

Requires SilverBullet 2.12 or later. Pure Space Lua and Space Style, no plug.

## How it works

- **A task is an ordinary markdown task**: `- [DOING] rerun the load test [due: 2026-10-25]`.
- **A task that needs room gets a task page**, `Tasks/<name>`. The first task on
  that page is the task's single source of truth: its state, dates, project and
  subtasks. Everything else on the page is its notebook.
- **Everywhere else the task is a projection**: a plain link,
  `- [[Tasks/rerun-load-test|rerun the load test]]`, drawn with the task's live state
  icon. Click the icon to change the state with SilverBullet's picker. Click the
  text to open the task page. Nothing but the source is ever written for a state
  change.
- **A project is a page tagged `#project`.** A task belongs to the project its
  source links to, `[[Projects/Website]]`. Subtasks inherit it.

## States

| Markdown | Shown as |
| --- | --- |
| `[ ]` | checkbox |
| `[DOING]` | a ring filling clockwise |
| `[WAITING]` | a clock |
| `[BLOCKED]` | a traffic cone |
| `[x]` | ticked |
| `[CANCELLED]` | a no-parking sign |

Click a state in the editor to cycle it, or use the ▾ after it.

## The board

Put this on a project page:

```markdown
${throughline.board()}
```

One column per open state (WAITING and BLOCKED share "On hold") plus a folded
Done column. A card is every task page of the project. Expand a card for its
subtasks and notes; tick subtasks right there. Drag a card to another column to change its state, or above and below
other cards to reorder. On touch screens, use the card's state dropdown.

**Card order lives in the project page.** The order in which the page lists its
task projections, usually under `## Tasks`, is the board's order. Reordering on
the board rewrites that list. Tasks not in the list follow, earliest due first.

## Commands

| Command | Does |
| --- | --- |
| `Throughline: Make task page`, or `/task` | Moves the task under the cursor and its subtasks to a new task page, leaves a projection in its place, and adds the projection to the project's list |
| `Throughline: Promote subtask` | The same, on a subtask of a task page; the new page ends with `[partOf: [[Tasks/<parent>]]]` |
| `Throughline: Delete task page` | Removes the task page and every projection of it, after a confirmation listing them |

Delete is also on each board card and at the bottom of a projection's state
picker.

## Configuration

In the Configuration Manager under **Throughline**, or in Space Lua:

```lua
config.set("throughline.taskFolder", "Tasks/")
config.set("throughline.projectFolder", "Projects/")
config.set("throughline.states", {
  { state = " ",         label = "To do" },
  { state = "DOING",     label = "Doing" },
  { state = "WAITING",   label = "Waiting",   column = "On hold" },
  { state = "BLOCKED",   label = "Blocked",   column = "On hold", drop = true },
  { state = "x",         label = "Done",      closed = true },
  { state = "CANCELLED", label = "Cancelled", closed = true },
})
```

States are listed in board order. States with the same `column` share a board
column; a card dropped into it takes the state marked `drop = true` (else the
column's first). `closed` states share the Done column. Icons
exist for the default states; any other state shows as SilverBullet's text.

## Known limits

- State icons on projections are drawn by the browser from the index, so they
  appear in the editor only, not in the page picker or completion.
- A deleted task page reaches the server with the client's next sync.
- Drag and drop needs a mouse; touch uses the card dropdown.

## License

Licensed under either of [Apache License 2.0](LICENSE-APACHE) or
[MIT license](LICENSE-MIT), at your option.
