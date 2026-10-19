# Throughline

A [SilverBullet](https://silverbullet.md) library for project tracking where
tasks, projects and the notes you take while doing them live in one place, as
plain markdown.

Requires SilverBullet 2.12 or later. Pure Space Lua and Space Style, no plug.

## Install

Run `Library: Install` and give it
`ghr:tanekere/throughline/Throughline.md`,
or copy `Throughline.md` to `Library/tanekere/Throughline.md` in your space and
reload.

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
- **A project is a page tagged `#project`**, with a `status:` in its
  frontmatter. A task belongs to the project its source links to,
  `[[Projects/Website]]`. Subtasks inherit it.

## States

| Markdown | Shown as | Category |
| --- | --- | --- |
| `[ ]` | checkbox | planned |
| `[BACKLOG]` | a dashed circle | backlog |
| `[DOING]` | a ring filling clockwise | active |
| `[WAITING]` | a clock | held |
| `[BLOCKED]` | a traffic cone | held |
| `[x]` | ticked | done |
| `[CANCELLED]` | a no-parking sign | cancelled |

Click a state in the editor to cycle it, or use the ▾ after it. Every state has
a **category**, set explicitly in the configuration. The library acts on the
category, so a state you add, say `[REVIEW]` with `category = "active"`, shows
up under Doing in the Focus list without further setup.

## The board

Put this on a project page:

```markdown
${throughline.board()}
```

One column per open state (Planned and Backlog share "To do", Waiting and
Blocked share "On hold") plus a folded Done column. A card is every task page of the project. Expand a card for its
subtasks and notes; tick subtasks right there. Drag a card to another column to change its state, or above and below
other cards to reorder. On touch screens, use the card's state dropdown.

**Card order lives in the project page.** The order in which the page lists its
task projections, usually under `## Tasks`, is the board's order. Reordering on
the board rewrites that list. Tasks not in the list follow, earliest due first.

## Projects overview

```markdown
${throughline.projects()}
```

Every `#project` page as a card, in sections by status: Active, Planned,
Paused, Idea. Done and Dropped are hidden behind **Show completed**. A card
shows the project's health, progress and how many tasks sit in each board
column. Click the card (anywhere but its name) to expand it into a stats sheet:
the latest update, status (changeable there), progress, overdue and upcoming
tasks, next due date, time logged and last activity. Click the name to open
the project.

Cards are in the order the page holding the widget links to the projects;
the rest follow by next due date.

**Status** is the `status:` line in the project's frontmatter: `active`,
`planned`, `paused`, `idea`, `done` or `dropped`. No line means active.

**Health** comes from the newest dated update under `## Updates` on the
project page:

```markdown
## Updates

### 2026-10-19 [health: at-risk]
Printer delivery slipped a week; the office setup waits on it.
```

Health is `on-track`, `at-risk` or `off-track`. When an active project's newest
update is older than a week (`throughline.updateDays`) its health shows dashed,
as stale; after two weeks it reads **Update missing**. `Throughline: Post
update` writes one for you. SilverBullet also files `health` as an attribute of
the page; Throughline reads the headings, not that attribute.

**Time** is any list item or task with a `[time: …]` attribute that links to
the project, e.g. `- about page [[Projects/Website]] [time: 2h30m]` in a
journal. `2h30m`, `1.5h`, `45m` and a bare number of hours all work. The day is
the item's `[date: …]`, else the date in its page's name.

## Focus

```markdown
${throughline.focus()}
```

The "what I have to do" list: every open task in the space, in sections, top
to bottom:

| Section | What lands there |
| --- | --- |
| Overdue | due or scheduled date has passed |
| Doing | active category |
| Today | due or scheduled today |
| On hold | held category |
| Upcoming | dated within the next 7 days (`throughline.upcomingDays`) |
| Later | planned, undated or dated further out (folded) |
| Backlog | backlog category, undated or far out (folded) |

A task goes to the first section that fits. Inside a section, active tasks come
first, then the earliest date. Empty sections are hidden. Click a row's icon to
change its state, its text to open it.

It includes the source of every task page, every task on other pages, and the
dated subtasks of task pages. `Library/` is left out.

**Filters.** The bar above the list filters by project, state or category,
date (overdue, today, next 7 or 30 days, no date), tag, and source (task pages,
other pages, or a top-level folder). The browser remembers the bar per page;
**Reset** goes back to the widget's own defaults, which you set as arguments:

```markdown
${throughline.focus { project = "this" }}
${throughline.focus { category = "held" }}
${throughline.focus { when = "week", source = "Journal" }}
```

Keys: `project` (a page name, `"this"`, or `"none"`), `state` (e.g. `"DOING"`),
`category`, `when` (`overdue`, `today`, `week`, `month`, `undated`), `tag`, and
`source` (a top-level folder, `"/"` for the top level, `"task-pages"` or
`"other-pages"`). Give `id = "…"` to two Focus lists on one page so each keeps
its own filter.

## Commands

| Command | Does |
| --- | --- |
| `Throughline: Make task page`, or `/task` | Moves the task under the cursor and its subtasks to a new task page, leaves a projection in its place, and adds the projection to the project's list |
| `Throughline: Promote subtask` | The same, on a subtask of a task page; the new page ends with `[partOf: [[Tasks/<parent>]]]` |
| `Throughline: Delete task page` | Removes the task page and every projection of it, after a confirmation listing them |
| `Throughline: New project` | Asks for a name and creates `Projects/<name>` with a board, `## Tasks` and `## Updates` (also on the overview) |
| `Throughline: Post update` | Asks for the health and a line of text, and adds a dated update under `## Updates` of the open project, or one you pick |
| `Throughline: Set project status` | Picks a status for the open project and writes it to the frontmatter |

Delete is also on each board card and at the bottom of a projection's state
picker.

## Configuration

In the Configuration Manager under **Throughline**, or in Space Lua:

```lua
config.set("throughline.taskFolder", "Tasks/")
config.set("throughline.projectFolder", "Projects/")
config.set("throughline.states", {
  { state = " ",         label = "Planned",   category = "planned",   column = "To do", drop = true },
  { state = "BACKLOG",   label = "Backlog",   category = "backlog",   column = "To do" },
  { state = "DOING",     label = "Doing",     category = "active" },
  { state = "WAITING",   label = "Waiting",   category = "held",      column = "On hold" },
  { state = "BLOCKED",   label = "Blocked",   category = "held",      column = "On hold", drop = true },
  { state = "x",         label = "Done",      category = "done" },
  { state = "CANCELLED", label = "Cancelled", category = "cancelled" },
})
config.set("throughline.projectStatuses", {
  { status = "active",  label = "Active",  category = "started" },
  { status = "planned", label = "Planned", category = "planned" },
  { status = "paused",  label = "Paused",  category = "paused" },
  { status = "idea",    label = "Idea",    category = "backlog" },
  { status = "done",    label = "Done",    category = "completed" },
  { status = "dropped", label = "Dropped", category = "canceled" },
})
config.set("throughline.updateDays", 7)
config.set("throughline.upcomingDays", 7)
```

States are listed in board order. Task categories are `backlog`, `planned`,
`active`, `held`, `done` and `cancelled`; project categories are `backlog`,
`planned`, `started`, `paused`, `completed` and `canceled`, after Linear. States
with the same `column` share a board column; a card dropped into it takes the
state marked `drop = true` (else the column's first). done and cancelled states
share the Done column. Icons exist for the default states; any other state
shows as SilverBullet's text. A 0.1 configuration without categories still works:
`closed = true` reads as done, the default state names (DOING, WAITING,
BLOCKED, BACKLOG, CANCELLED) keep their usual category, and any other state is
planned until you give it one.

## Known limits

- State icons on projections are drawn by the browser from the index, so they
  appear in the editor only, not in the page picker or completion.
- A deleted task page reaches the server with the client's next sync.
- Drag and drop needs a mouse; touch uses the card dropdown.
- Widgets render when the page renders. A change made elsewhere shows on the
  next visit or reload; changes made from the widget itself show at once.
- The Focus list's starting filter is applied on the next one-second tick, so a
  filtered list can show unfiltered for a moment.

## License

Licensed under either of [Apache License 2.0](LICENSE-APACHE) or
[MIT license](LICENSE-MIT), at your option.
