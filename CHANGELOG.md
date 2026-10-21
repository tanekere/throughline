# Changelog

Throughline is alpha software, so versions are numbered 0.0.x. The first two
were called 0.1 and 0.2 while they were being written; they are 0.0.1 and
0.0.2 here and in the release tags.

Versions are released by pushing a tag `vX.Y.Z`; see Development in the README.

## 0.0.4 (2026-10-21)

- If your space has an older copy of Throughline under a different page name
  in `Library/`, remove it after installing this one, so only one copy loads.
- The test spaces use neutral example data.
- `throughline.lua`: the library's code on its own, for reading with syntax
  highlighting. EXPLAINER.md links into it.
- Fixed: reordering cards, posting an update or adding a projection to a
  project page dropped the page's last line when its text did not end with a
  newline.
- Board cards mark a date that is today in amber and say "Today", as the
  Focus list already did.
- Click a projection's icon, or its due date, to edit the task in place: a
  panel with its state, due and scheduled dates (with the browser's calendar)
  and progress. It replaces the state picker. Every change writes at once.
- Blocked by: choose the task that blocks this one from the panel or a card,
  or clear it. Stored as `[blockedBy: [[Tasks/…]]]`; board cards and Focus
  rows show "⛔ blocked by …", struck through once the blocker is finished.
- Projections show the task's due date after the link, red once past.
- Progress: a task's `[progress: n]`, else its share of done subtasks. Shown
  as a ring on the board card.
- An expanded board card has the same date and progress fields; its body is
  built when it is first opened, so boards draw faster.
- The board card's state dropdown is gone; change state by dragging, or from
  the task list.
- A state changed anywhere on the page (the task list, a Focus row) moves the
  board card at once, and icons no longer flip back to the old state for a
  few seconds after a change.
- Faster: projection icons appear about 0.1 s after a page opens instead of up
  to 1 s; the Focus list draws in about half the time on large spaces; a
  filtered Focus list no longer shows unfiltered first.
- Board: a New task button at the end of the To do column creates a task page
  for the project and adds its card at once.
- Board: Hide backlog, in the To do column's header of every board, hides
  backlog cards on all boards; the browser remembers the choice.
- The thin border SilverBullet draws round a widget no longer shows above and
  below the board, the projects overview and the Focus list.
- The Focus list's total in its header follows the filter, like the section
  counts.
- EXPLAINER.md: every feature, the code behind it, with screenshots.
- The code is reorganised and commented for reading; no other behaviour
  changed. The README is rewritten for people new to Throughline, with
  screenshots.

## 0.0.3 (2026-10-20)

Themes, settings in the Configuration menu, releases.

- Installs and updates come from the latest full GitHub release:
  `share.uri` is `ghr:tanekere/throughline/Throughline.md`.
- Theme setting in the Configuration menu (Throughline → Theme): `native`
  (default) or `lineish`.
- native: SilverBullet's own font, colours and buttons; no panel backgrounds or
  shadows; dotted rules and outlines; chips as plain words; the projects
  overview stays in the text column. Light and dark.
- lineish: the 0.0.2 look, unchanged.
- The done and completed icons and the progress ring now take the theme's
  colours instead of fixed ones.

## 0.0.2 (2026-10-19)

Projects, health and a Focus list, after Linear.

- State categories: backlog, planned, active, held, done, cancelled. The
  library acts on the category; every default state has one. 0.0.1
  configurations without categories still work.
- New state `[BACKLOG]` (dashed circle), sharing the To do column with `[ ]`,
  now labelled Planned. A card dropped into To do becomes `[ ]`.
- Project status from frontmatter `status:`: Active, Planned, Paused, Idea,
  Done, Dropped by default (`throughline.projectStatuses`), with categories.
- Project updates: `### <date> [health: on-track|at-risk|off-track]` under
  `## Updates`. Health shows stale after `throughline.updateDays`, and
  "Update missing" after twice that.
- `throughline.projects()`: project cards in sections by status, completed
  hidden behind a toggle. Health, progress ring, per-column counts. Expands
  into a stats sheet with the latest update, status selector, progress,
  overdue and upcoming counts, next due, time logged and last activity.
- Time logging: `[time: 2h30m]` on any item or task linking a project.
- `throughline.focus()`: Overdue, Doing, Today, On hold, Upcoming, Later,
  Backlog. Change state from the row; filter by project, state or category,
  date, tag and source; the browser remembers the filter per page.
- Commands: `Throughline: New project`, `Throughline: Post update`,
  `Throughline: Set project status`.
- Board column headers carry their state icon. New look throughout: Inter
  where installed, hairline borders, Linear's status shapes and colours.

## 0.0.1 (2026-10-18)

First version.

- Task states with icons: DOING, WAITING, BLOCKED, CANCELLED.
- Task pages as the source of a task; projections as links with live state.
- `throughline.board()`: Kanban with folded Done column, inline card
  expansion, drag to change state and to reorder, state dropdown for touch.
- Card order taken from, and written back to, the project page's task list.
- Commands: make task page, promote subtask, delete task page; `/task`.
- Configuration: task folder, project folder, states.
