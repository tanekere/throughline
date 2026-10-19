# Changelog

## 0.2.0 (2026-10-19)

Projects, health and a Focus list, after Linear.

- State categories: backlog, planned, active, held, done, cancelled. The
  library acts on the category; every default state has one. 0.1
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

## 0.1.0 (unreleased)

First version.

- Task states with icons: DOING, WAITING, BLOCKED, CANCELLED.
- Task pages as the source of a task; projections as links with live state.
- `throughline.board()`: Kanban with folded Done column, inline card
  expansion, drag to change state and to reorder, state dropdown for touch.
- Card order taken from, and written back to, the project page's task list.
- Commands: make task page, promote subtask, delete task page; `/task`.
- Configuration: task folder, project folder, states.
