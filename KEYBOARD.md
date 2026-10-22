# Throughline from the keyboard

Everything in Throughline is text on a page. From the keyboard you edit that
text. A few helpers cover what is hard to remember or awkward to type, and
nothing else: if typing does a job well, there is no shortcut for it.

## The idea in one minute

- A task is a line of text: `- [DOING] write the brief [due: 2026-11-01]`.
- The board and the Focus list are views for the mouse. Change the text and
  they follow.
- A projection, `- [[Tasks/x|title]]`, is a link to a task page. To edit that
  task, open it.

## Keys and commands

`Ctrl` is `Cmd` on a Mac. The palette is `Ctrl+/`.

| Action | Keys or command | Vim |
| --- | --- | --- |
| Command palette | `Ctrl+/` | normal or insert |
| Create a task, or give a task its page | `/task` | insert |
| Change a state | type inside the brackets; a list of states appears | `ci[`, then a letter |
| Due or scheduled date | `/due`, `/scheduled` | insert |
| Blocked by | `/blocked` | insert |
| Progress | `/progress` | insert |
| Open the task on this line | `Ctrl+.` then `o` | normal |
| Open the link under the cursor | `Ctrl+Enter` (SilverBullet) | normal |
| Back, forward | `Alt+Left`, `Alt+Right` | any |
| Move a task up or down | `Alt+Up`, `Alt+Down`, or `Ctrl+.` then `k` / `j` | any |
| Indent or outdent a subtask | `Tab`, `Shift+Tab`, or `Ctrl+.` then `l` / `h` | insert |
| Filter the Focus list | palette: Throughline: Filter Focus | |
| Post an update | palette: Throughline: Post update | |
| Set a project's status | palette: Throughline: Set project status | |
| New project | palette: Throughline: New project | |
| Delete a task page | palette: Throughline: Delete task page | |
| Find a page | `Ctrl+K` | |
| Vim mode on or off | palette: Editor: Toggle Vim Mode | |

## Create a task

`/task` is the preferred way to create a task. It works on any line:

- On an empty line it asks for the task's text.
- On plain text, or on `- `, the text becomes a task.
- On a task, `- [ ] text` or `- [DOING] text`, it keeps the state.

Then it asks for the task page's name. The field starts empty and the
suggested name is in the label: press Enter to take it, or type your own.
Escape cancels. The line becomes a projection, and on a project page the
task belongs to that project.

Throughline's `/task` replaces SilverBullet's own.

## Change a state

Put the cursor inside the brackets and type. SilverBullet lists the states as
soon as you type after `[`, so you don't have to remember their names.

On the line that holds the cursor the state shows as plain text, `[BLOCKED]`,
not as an icon, so you can select it and type over it. A click on a state only
places the cursor.

- Vim: `ci[`, a letter, pick from the list, Enter. Escape twice: the first
  closes the list, the second leaves insert mode.
- Don't use "Task: Cycle State" for Throughline's states. It only toggles
  `[ ]` and `[x]`, and on a projection line it writes a stray task.

## Dates, blocker, progress

Type these on a task line, after a space:

- `/due`, `/scheduled`: writes `[due: <today>]` with the date selected. Type
  the date you want over it. If the task has a date already, it stays and is
  selected.
- `/progress`: writes `[progress: ]` with the cursor where the number goes,
  0 to 100.
- `/blocked`: pick the blocking task by its title, among open tasks. It writes
  `[blockedBy: [[Tasks/…]]]`.

An attribute never appears twice: a snippet on a task that has the attribute
changes the one that is there. On a projection the snippets refuse. Open the
task first.

You can also type the attributes yourself. It is the same text.

## Open a task from a list

`Ctrl+.` then `o` on a projection, or on a line with a `blockedBy`, opens that
task with the cursor inside its state brackets, ready to type. `Alt+Left`
goes back.

## Order and columns

- Order: `Alt+Up` and `Alt+Down` on the project's task list. The board
  follows that order.
- Column: change the state. The column follows from it.

## Projects

Post update and Set project status are in the palette. Or edit `status:` in
the project's frontmatter.

## Focus list filters

Palette, then "Throughline: Filter Focus". Pick a filter, then a value. The
pickers come back for the next filter, so you can set several. Escape when
done. Reset goes back to the list's starting filter. The Focus list must be on
screen; with two on one page, the command asks which.

## Delete a task page

Palette, then "Throughline: Delete task page", on the task page or with the
cursor on a projection. Read the window: it says which projections go with it.
Ok is focused and red, so Enter deletes. When the task has subtasks, a first
window asks whether they become tasks of their own or are deleted too.

## Vim mode

- Turn it on from the palette: "Editor: Toggle Vim Mode". It is set per
  browser.
- Slash commands work in insert mode. `Ctrl+.` chords work in normal mode.
- After `/due` the date is selected and you are still in insert mode: type
  the new date.
- Enter in a list continues it with `- [ ] `. Type the state inside those
  brackets instead of typing a second `- [STATE]`.

## Things that look odd but are on purpose

- The line under the cursor shows its source: links, states and widget
  directives.
- Tab indents. It does not move between buttons.
- Enter on a projection starts a new list item. Use `Ctrl+.` then `o` to open
  it.
- The board, the projects overview and the Focus rows are for the mouse.
  Everything they change is text you can edit instead.
