---
name: Library/tanekere/Throughline
tags: meta/library
share.uri: "ghr:tanekere/throughline/Throughline.md"
share.mode: pull
---
# Throughline

Tasks, projects and the notes you take while working, in one place. Full
documentation: https://github.com/tanekere/throughline

* A **task** is an ordinary markdown task. One that needs room for notes gets
  its own **task page** in `Tasks/`; the first task on that page is the task.
* Anywhere else, a task appears as a **projection**: a plain link,
  `- [[Tasks/rerun-load-test|rerun the load test]]`, drawn with the task's live
  state and due date. Click the icon or the date to edit the task (state,
  dates, blocked by, progress), the text to open the page.
* A **project** is a page tagged `#project` with a `status:` in its
  frontmatter. `${throughline.board()}` on it shows a board of its tasks.
* `${throughline.projects()}` shows every project as a card, grouped by status.
* `${throughline.focus()}` lists what needs doing: Overdue, Doing, Today, On
  hold, Upcoming, then Later and Backlog.

Commands start with `Throughline:`. Settings are under Throughline in
Configuration: Open.

## How it fits together

1. **Overview.** One page, usually your index, holds the projects overview and
   the Focus list: every project as a card, and every open task in the order
   to work through it.
2. **Projects.** Each project is a page tagged `#project`, with its board, its
   task list under `## Tasks`, and dated updates under `## Updates`.
3. **Tasks.** Each task that needs room has a task page in `Tasks/`. Its first
   task line is the task; the rest of the page is notes and subtasks.

On the levels above it, a task appears as a link with its live state. Change
it anywhere and its task page is what changes.

## Quick tutorial

About five minutes, on any space.

1. **Make a main page.** Open your index page and add these two lines:

   ```markdown
   ${throughline.projects()}

   ${throughline.focus()}
   ```

   That is your main board: the projects overview above, the Focus list below.
   Everything else is reachable from it.

2. **Create a project.** Press **New project** in the overview's toolbar and
   give it a name, say "Website". Throughline creates `Projects/Website` with
   a board and opens it.

3. **Create tasks.** The preferred way is `/task`: under the project's
   `## Tasks` heading, type `/task` on an empty line and press Enter. Type what
   needs doing, press Enter, and Enter again to take the suggested page name. Each one gets a task page and a card. Add a few. With
   the mouse, **New task** at the bottom of the board's To do column does the
   same.

4. **Set dates, a blocker and progress.** Under the board, the project's task
   list shows each task as a link. Click a task's icon to open its panel: pick
   a state, set a due date with the calendar, choose the task it is blocked
   by, or drag Progress. Open a card on the board for the same fields. From
   the keyboard, type `/due`, `/scheduled`, `/blocked` or `/progress` on the
   task's line instead.

5. **Move work along.** Drag a card to Doing when you start it, and to Done
   when it is finished. Drag cards up and down to set their order.

6. **Say how the project is going.** In the overview, click the project's card
   (not its name) to open it, press **Post update**, pick On track, At risk or
   Off track, and write a line. The card shows that health from then on.

7. **Work from the Focus list.** Back on the main page, Focus lists what is
   overdue, what you are doing, what is due today and what is coming up. Click
   a row's icon to change its state, or its text to open it.

Tasks you write anywhere else, in a journal for example, show up in Focus too.
To give one a page and a card, put the cursor on it and type `/task`.
For the keyboard and vim, see KEYBOARD.md in the
[repository](https://github.com/tanekere/throughline/blob/main/KEYBOARD.md).

```space-lua
-- priority: 10
--
-- How this file is laid out
--
--   Configuration     settings shown in Configuration: Open
--   Helpers           strings, dates, durations, pickers
--   States            what each task state means (its category) and where it
--                     goes on a board
--   Pages             reading and writing pages safely while one is open
--   Task pages        finding each task page's task; changing its state and
--                     its attributes
--   Task details      progress, blocked by, and the form that edits them
--   Board             ${throughline.board()}: columns, cards, drag and drop
--   Projects          status, dated updates, health, ${throughline.projects()}
--                     and the project commands
--   Focus             ${throughline.focus()}: sections, rows, the filter bar
--   Projections       live state and due date on links to task pages, and
--                     the panel for editing a task from its link
--   Background tick   work that runs once a second
--   Task commands     make, promote and delete task pages; /task
--
-- Two facts shape most of the code:
--
-- * Widgets are plain HTML built once, when the page renders. When the user
--   acts in one (drops a card, changes a status), the code updates the HTML in
--   place and writes the page; nothing re-renders until the page is reloaded.
--   tl.syncWidgets keeps cards and Focus rows in step with state changes made
--   elsewhere on the page.
-- * The index is the source for reading, but positions and fields in it can
--   lag behind the text. Every write therefore re-reads the page and checks
--   that the line it is about to change is the one it expects, and states
--   Throughline just wrote are remembered until the index shows them.
--
-- Everything public hangs off the global `throughline` table (`tl` here), so
-- that widget directives and event handlers can reach it.

throughline = throughline or {}
local tl = throughline

---------------------------------------------------------------------------
-- Configuration
---------------------------------------------------------------------------

config.defineCategory {
  name = "Throughline",
  description = "Tasks, projects and task pages.",
}

config.define("throughline.taskFolder", {
  description = "Folder holding task pages, with a trailing slash.",
  type = "string",
  default = "Tasks/",
  ui = { category = "Throughline", label = "Task folder", priority = 5 },
})

config.define("throughline.projectFolder", {
  description = "Folder holding project pages, with a trailing slash.",
  type = "string",
  default = "Projects/",
  ui = { category = "Throughline", label = "Project folder", priority = 4 },
})

config.define("throughline.states", {
  description = "Task states in board order. Each has a `category`: backlog, planned, active, held, done or cancelled. States with the same `column` share a board column; a card dropped there takes the one marked `drop`. done and cancelled states share the Done column.",
  type = "array",
  default = {
    { state = " ",         label = "Planned",   category = "planned",   column = "To do", drop = true },
    { state = "BACKLOG",   label = "Backlog",   category = "backlog",   column = "To do" },
    { state = "DOING",     label = "Doing",     category = "active" },
    { state = "WAITING",   label = "Waiting",   category = "held",      column = "On hold" },
    { state = "BLOCKED",   label = "Blocked",   category = "held",      column = "On hold", drop = true },
    { state = "x",         label = "Done",      category = "done" },
    { state = "CANCELLED", label = "Cancelled", category = "cancelled" },
  },
  ui = { category = "Throughline", label = "States" },
})

config.define("throughline.projectStatuses", {
  description = "Project statuses, in the order the projects overview shows them. Each has a `category`: backlog, planned, started, paused, completed or canceled. A project page without `status:` counts as the first started status.",
  type = "array",
  default = {
    { status = "active",  label = "Active",  category = "started" },
    { status = "planned", label = "Planned", category = "planned" },
    { status = "paused",  label = "Paused",  category = "paused" },
    { status = "idea",    label = "Idea",    category = "backlog" },
    { status = "done",    label = "Done",    category = "completed" },
    { status = "dropped", label = "Dropped", category = "canceled" },
  },
  ui = { category = "Throughline", label = "Project statuses" },
})

config.define("throughline.updateDays", {
  description = "Days between project updates. An active project whose latest update is older shows as stale; older than twice this, as update missing.",
  type = "number",
  default = 7,
  ui = { category = "Throughline", label = "Update cadence (days)", priority = 3 },
})

config.define("throughline.upcomingDays", {
  description = "How many days ahead the Focus list's Upcoming section reaches.",
  type = "number",
  default = 7,
  ui = { category = "Throughline", label = "Upcoming (days)", priority = 2 },
})

config.define("throughline.theme", {
  description = "How the widgets look: native (SilverBullet's own colours and font, dotted lines) or lineish (cards and panels in the style of Linear).",
  type = "string",
  enum = { "native", "lineish" },
  default = "native",
  ui = { category = "Throughline", label = "Theme", priority = 6 },
})

function tl.taskFolder() return config.get("throughline.taskFolder", "Tasks/") end
function tl.projectFolder() return config.get("throughline.projectFolder", "Projects/") end
function tl.states() return config.get("throughline.states", {}) end
function tl.projectStatuses() return config.get("throughline.projectStatuses", {}) end
function tl.updateDays() return config.get("throughline.updateDays", 7) end
function tl.upcomingDays() return config.get("throughline.upcomingDays", 7) end
function tl.theme() return config.get("throughline.theme", "native") end

-- Defining the custom states gives completion and SilverBullet's state picker.
for _, st in ipairs(tl.states()) do
  if st.state ~= " " and st.state ~= "x" then
    local cat = st.category or (st.closed and "done") or "planned"
    taskState.define { name = st.state, done = cat == "done" or cat == "cancelled" }
  end
end

---------------------------------------------------------------------------
-- Helpers
---------------------------------------------------------------------------

local function escapePattern(s)
  return (string.gsub(s, "%p", "%%%0"))
end

local function trim(s)
  return (string.gsub(string.gsub(s, "^%s+", ""), "%s+$", ""))
end

local function startsWith(s, prefix)
  return string.sub(s or "", 1, #prefix) == prefix
end

local function contains(list, value)
  for _, x in ipairs(list or {}) do
    if x == value then return true end
  end
  return false
end

local function basename(name)
  return string.match(name, "([^/]+)$") or name
end

-- Seconds, with milliseconds, since the page loaded; for measuring ages.
local function clock() return js.window.performance.now() / 1000 end

-- Text split into lines, without the empty string a final newline leaves.
local function splitLines(text)
  local ls = {}
  for line in string.gmatch((text or "") .. "\n", "([^\n]*)\n") do table.insert(ls, line) end
  if ls[#ls] == "" then table.remove(ls) end
  return ls
end

-- Per-browser memory (clientStore) for view choices: whether completed
-- projects and backlog cards show, and each Focus list's filter. Failures are ignored, since
-- losing a view choice is harmless.
local function storeGet(key)
  local ok, v = pcall(clientStore.get, key)
  if ok then return v end
end

local function storeSet(key, value)
  pcall(clientStore.set, key, value)
end

-- SilverBullet's picker over a list of { name = ..., description = ... }
-- rows (description optional); returns the chosen row, or nil when dismissed.
local function pick(title, rows)
  local row = { primary = "name" }
  for _, r in ipairs(rows) do
    if r.description then row.description = "description"; break end
  end
  return view.pick {
    title = title,
    source = function() return rows end,
    presentation = { row = row },
  }
end

local function pageExists(name)
  local ok, meta = pcall(space.getPageMeta, name)
  return ok and meta ~= nil
end

local function today()
  local ok, d = pcall(function() return os.date("%Y-%m-%d") end)
  if ok and d then return d end
  return "0000-00-00"
end

local months = { "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec" }
local function shortDate(iso)
  local _, m, d = string.match(iso, "^(%d+)-(%d+)-(%d+)")
  if not m then return iso end
  return months[tonumber(m)] .. " " .. tonumber(d)
end

-- Days since 1970-01-01 for an ISO date, and back. Plain arithmetic, so it
-- does not depend on what os.time supports.
local function dayNumber(iso)
  local y, m, d = string.match(tostring(iso or ""), "^(%d%d%d%d)-(%d%d)-(%d%d)")
  if not y then return nil end
  y, m, d = tonumber(y), tonumber(m), tonumber(d)
  if m <= 2 then y = y - 1 end
  local era = math.floor(y / 400)
  local yoe = y - era * 400
  local doy = math.floor((153 * ((m + 9) % 12) + 2) / 5) + d - 1
  local doe = yoe * 365 + math.floor(yoe / 4) - math.floor(yoe / 100) + doy
  return era * 146097 + doe - 719468
end

local function isoOf(n)
  n = n + 719468
  local era = math.floor(n / 146097)
  local doe = n - era * 146097
  local yoe = math.floor((doe - math.floor(doe / 1460) + math.floor(doe / 36524) - math.floor(doe / 146096)) / 365)
  local doy = doe - (365 * yoe + math.floor(yoe / 4) - math.floor(yoe / 100))
  local mp = math.floor((5 * doy + 2) / 153)
  local d = doy - math.floor((153 * mp + 2) / 5) + 1
  local m = mp < 10 and mp + 3 or mp - 9
  local y = yoe + era * 400
  if m <= 2 then y = y + 1 end
  return string.format("%04d-%02d-%02d", y, m, d)
end

local function addDays(iso, n) return isoOf(dayNumber(iso) + n) end

-- the Monday on or before a date
local function weekStart(iso)
  local n = dayNumber(iso)
  return isoOf(n - ((n + 3) % 7))
end

local function daysAgo(iso, now)
  local a, b = dayNumber(iso), dayNumber(now)
  if not a or not b then return nil end
  return b - a
end

local function ago(iso, now)
  local n = daysAgo(string.sub(tostring(iso or ""), 1, 10), now)
  if not n then return "never" end
  if n <= 0 then return "today" end
  if n == 1 then return "yesterday" end
  if n < 14 then return n .. " days ago" end
  if n < 60 then return math.floor(n / 7) .. " weeks ago" end
  return math.floor(n / 30) .. " months ago"
end

-- "2h30m", "1.5h", "45m", "2" (hours) -> minutes
local function minutesOf(s)
  s = string.lower(tostring(s or ""))
  local total, found = 0, false
  for num, unit in string.gmatch(s, "(%d+%.?%d*)%s*([hm])") do
    found = true
    total = total + tonumber(num) * (unit == "h" and 60 or 1)
  end
  if not found then
    local n = tonumber(s)
    if n then return n * 60 end
  end
  return total
end

local function fmtMinutes(m)
  m = math.floor((m or 0) + 0.5)
  if m <= 0 then return "–" end
  local h, r = math.floor(m / 60), m % 60
  if h == 0 then return r .. "m" end
  if r == 0 then return h .. "h" end
  return h .. "h " .. r .. "m"
end

---------------------------------------------------------------------------
-- States
--
-- A state is the text between the brackets of a task: " ", "x", "DOING".
-- What the library does with a state depends only on its category (backlog,
-- planned, active, held, done, cancelled), never on its name, so states can
-- be renamed or added in the configuration.
---------------------------------------------------------------------------

local categoryLabels = {
  backlog = "Backlog", planned = "Planned", active = "Active",
  held = "On hold", done = "Done", cancelled = "Cancelled",
}
local categoryOrder = { "backlog", "planned", "active", "held", "done", "cancelled" }

-- The configured states by name, and each state's category, cached until
-- the background tick clears the cache (once a second, so a changed
-- configuration shows within a second). The widgets ask for a state's
-- category several times per task, and reading the configuration each time
-- made the Focus list take most of a second to draw on a space with a few
-- hundred tasks.
function tl.stateTables()
  if not tl.stateCache then
    local by = {}
    for _, st in ipairs(tl.states()) do by[st.state] = st end
    tl.stateCache = { by = by, cat = {} }
  end
  return tl.stateCache
end
local stateTables = tl.stateTables

local function stateEntry(state)
  return stateTables().by[state]
end

-- for states configured without a category (a 0.0.1 configuration) or not
-- configured at all: the default states keep their usual meaning
local defaultCategories = {
  [" "] = "planned", x = "done", X = "done", BACKLOG = "backlog", DOING = "active",
  WAITING = "held", BLOCKED = "held", CANCELLED = "cancelled",
}

-- The category a state belongs to, as configured. A configuration without
-- categories still works: `closed = true` reads as done, a default state name
-- as its default category, anything else as planned.
local function categoryFromConfig(state)
  local st = stateEntry(state)
  if st then
    if st.category then return st.category end
    if st.closed then return defaultCategories[state] == "cancelled" and "cancelled" or "done" end
  end
  return defaultCategories[state] or "planned"
end

function tl.categoryOf(state)
  local cache = stateTables().cat
  local cat = cache[state]
  if not cat then
    cat = categoryFromConfig(state)
    cache[state] = cat
  end
  return cat
end

-- The index's own `done` flag covers [x] only; taskState.define { done = true }
-- does not set it, so closed states come from the configuration.
function tl.isClosedState(state)
  local cat = tl.categoryOf(state)
  return cat == "done" or cat == "cancelled"
end

function tl.labelOf(state)
  local st = stateEntry(state)
  if st then return st.label or st.state end
  return state
end

-- The board column a state belongs to: "closed" for closed states, else its
-- `column`, else its own label.
function tl.columnOf(state)
  if tl.isClosedState(state) then return "closed" end
  local st = stateEntry(state)
  if st then return st.column or st.label end
  return state
end

-- the state a card takes when dropped into a column from another one: the
-- column's state marked `drop = true`, else its first
function tl.columnState(column)
  if column == "closed" then return "x" end
  local first
  for _, st in ipairs(tl.states()) do
    if not tl.isClosedState(st.state) and (st.column or st.label) == column then
      if st.drop then return st.state end
      first = first or st.state
    end
  end
  return first
end

-- whether an index task object is finished (done or cancelled)
local function isClosed(t)
  return t.done or tl.isClosedState(t.state)
end

-- The name the stylesheet knows a state by, for data-tl-state attributes:
-- " " and "x" are awkward in CSS selectors.
local function shownState(state)
  if state == " " then return "todo" end
  if state == "x" or state == "X" then return "done" end
  return state
end

-- SilverBullet's picker over the configured states. `extra` rows go last.
local function pickState(title, extra)
  local rows = {}
  for _, st in ipairs(tl.states()) do table.insert(rows, { name = st.label, state = st.state }) end
  for _, r in ipairs(extra or {}) do table.insert(rows, r) end
  return pick(title, rows)
end

---------------------------------------------------------------------------
-- Pages
---------------------------------------------------------------------------

-- Read and write a page through the editor when it is the open one: writing an
-- open page behind the editor's back leaves a stale buffer that a later save
-- writes over the change.
function tl.read(page)
  if page == editor.getCurrentPage() then return editor.getText() end
  return space.readPage(page)
end

function tl.write(page, text)
  if page == editor.getCurrentPage() then
    if editor.getText() ~= text then editor.setText(text) end
  else
    space.writePage(page, text)
  end
end

-- task text without attributes and links, for titles, aliases and slugs
function tl.plainText(text)
  text = text or ""
  -- most task text has no brackets at all; skip the patterns then
  if not string.find(text, "[", 1, true) then return trim(string.gsub(text, "%s+", " ")) end
  local s = string.gsub(text, "%[[%w_]+:%s*%[%[[^%]]*%]%]%]", "")
  s = string.gsub(s, "%[[%w_]+:[^%]]*%]", "")
  s = string.gsub(s, "%[%[[^%]|]*|([^%]]*)%]%]", "%1")
  s = string.gsub(s, "%[%[[^%]]*%]%]", "")
  return trim(string.gsub(s, "%s+", " "))
end

-- What a new task page starts with: task pages stay out of the page tree, as
-- the projects are where they show.
local TASK_PAGE_FRONTMATTER = "---\npageDecoration:\n  tree:\n    hide: true\n---\n"

-- The pattern matching a link to a project page, capturing the page name.
local function projectLinkPattern()
  return "%[%[(" .. escapePattern(tl.projectFolder()) .. "[^%]|]+)"
end

---------------------------------------------------------------------------
-- Task pages
--
-- A task page's task is the first top-level task on it; the rest of the page
-- is notes and subtasks. In the code that task is the page's "source": every
-- projection of the page shows the source's state. Reading and writing its
-- state and its `[key: value]` attributes happens here.
---------------------------------------------------------------------------

-- States Throughline wrote in the last few seconds: page -> { state, at }.
-- SilverBullet's index catches up with a write only after a moment. Until it
-- shows the new state, or 20 seconds pass, these win over the index; without
-- them an icon flips back to the old state right after a change.
tl.pending = tl.pending or {}
-- the same for due dates set from the task form: page -> { due, at }
tl.pendingDue = tl.pendingDue or {}

local function pendingState(page, indexed)
  local p = tl.pending[page]
  if not p then return indexed end
  if indexed == p.state or clock() - p.at > 20 then
    tl.pending[page] = nil
    return indexed
  end
  return p.state
end

-- The source task of every task page, optionally only those linking to
-- `project`, with states just written by Throughline already applied. Inside
-- query[[...]] a bare name resolves to the object's own field first, so
-- filtering by folder and project happens in Lua instead.
function tl.sources(project)
  local folder = tl.taskFolder()
  local first = {}
  for _, t in ipairs(query[[from index.tasks() where not _.parent]]) do
    if startsWith(t.page, folder) then
      local seen = first[t.page]
      if not seen or t.pos < seen.pos then first[t.page] = t end
    end
  end
  local out = {}
  for _, t in pairs(first) do
    if not project or contains(t.links, project) then
      t.state = pendingState(t.page, t.state)
      table.insert(out, t)
    end
  end
  return out
end

-- Where the task page's task line is in `text`: its first and last
-- character, or nil when the page has no top-level task.
local function taskLineIn(text)
  local s = string.find(text, "^[-*] %[")
  if not s then
    s = string.find(text, "\n[-*] %[")
    if s then s = s + 1 end
  end
  if not s then return nil end
  local e = (string.find(text, "\n", s, true) or (#text + 1)) - 1
  return s, e
end

-- The page a link-valued attribute points to. In the page text it is
-- "[[Tasks/x|alias]]"; the index hands it back in its own wrapping, so take
-- a page field from a table, else strip brackets, braces, quotes and the
-- alias from the text.
local function linkTarget(v)
  if v == nil then return nil end
  if type(v) == "table" then v = v.page or v.toPage or v.ref or v.name or v[1] end
  if v == nil then return nil end
  v = tostring(v)
  v = string.match(v, "%[%[([^%]|]+)") or v
  v = string.gsub(v, "|.*$", "")
  v = trim((string.gsub(v, "[%[%]{}\"']", "")))
  return v ~= "" and v or nil
end

-- The attributes on a task page's task line, read from the page text, so
-- they are current even before the index catches up:
-- { due = "2026-11-01", blockedBy = "Tasks/x" }. A link value gives the page.
function tl.taskAttrs(page)
  local text = tl.read(page) or ""
  local s, e = taskLineIn(text)
  local attrs = {}
  if not s then return attrs end
  local line = string.sub(text, s, e)
  for k, v in string.gmatch(line, "%[([%w_]+):%s*%[%[([^%]|]+)[^%]]*%]%]%]") do attrs[k] = v end
  line = string.gsub(line, "%[[%w_]+:%s*%[%[[^%]]*%]%]%]", "")
  for k, v in string.gmatch(line, "%[([%w_]+):%s*([^%]]-)%s*%]") do attrs[k] = v end
  return attrs
end

-- Set the state of a task page's task: the first task line on the page.
function tl.setTaskPageState(page, state)
  local text = tl.read(page)
  local s = taskLineIn(text)
  if not s then
    editor.flashNotification("No task found on " .. page, "error")
    return
  end
  local open = string.find(text, "[", s, true)
  local close = string.find(text, "]", open + 1, true)
  tl.write(page, string.sub(text, 1, open) .. state .. string.sub(text, close))
  tl.noteState(page, state)
end

-- Set attribute `key` on a task page's task to `value`, writing
-- `[key: value]` at the end of the task line, or replacing the one there.
-- An empty or nil value removes the attribute.
function tl.setTaskAttr(page, key, value)
  local text = tl.read(page)
  local s, e = taskLineIn(text)
  if not s then
    editor.flashNotification("No task found on " .. page, "error")
    return
  end
  local line = string.sub(text, s, e)
  local set = value ~= nil and tostring(value) ~= ""
  local new
  if string.find(line, "%[" .. key .. ":") then
    -- a link value ends in "]]]", any other value at the first "]"
    local replacement = set and (" [" .. key .. ": " .. value .. "]") or ""
    local n
    new, n = string.gsub(line, "%s*%[" .. key .. ":%s*%[%[[^%]]*%]%]%]", function() return replacement end, 1)
    if n == 0 then
      new = string.gsub(line, "%s*%[" .. key .. ":%s*[^%]]*%]", function() return replacement end, 1)
    end
  elseif set then
    new = line .. " [" .. key .. ": " .. value .. "]"
  else
    return
  end
  tl.write(page, string.sub(text, 1, s - 1) .. new .. string.sub(text, e + 1))
  if key == "due" then
    local due = set and tostring(value) or false
    tl.pendingDue[page] = { due = due, at = clock() }
    if tl.dueMap then tl.dueMap[page] = due end
  end
end

---------------------------------------------------------------------------
-- Task details
--
-- Progress, blocked by, and the form that edits a task page's dates,
-- blocker and progress. The projection panel and the expanded board card
-- both use the form.
---------------------------------------------------------------------------

-- A task's progress in percent: its `[progress: n]` attribute if it has one,
-- else the share of its subtasks that are done (cancelled ones left out),
-- else nil.
local function taskProgress(progressAttr, subs)
  local n = tonumber(progressAttr)
  if n then return math.max(0, math.min(100, math.floor(n + 0.5))) end
  local done, total = 0, 0
  for _, s in ipairs(subs or {}) do
    local cat = tl.categoryOf(s.state)
    if cat ~= "cancelled" then
      total = total + 1
      if cat == "done" then done = done + 1 end
    end
  end
  if total == 0 then return nil end
  return math.floor(done * 100 / total + 0.5)
end

-- The small ring and percentage shown for a task's progress.
local function progressChip(pct)
  return dom.span {
    class = "tl-chip tl-tprog",
    title = pct .. "% done",
    style = "--tl-pct:" .. pct,
    dom.span { class = "tl-ring" },
    pct .. "%",
  }
end

-- "⛔ blocked by <task>" for a task whose `blockedBy` names another task
-- page; struck through once that task is finished.
local function blockedChip(blocker)
  blocker = linkTarget(blocker)
  if not blocker then return nil end
  local st = tl.stateOf(blocker)
  local done = st and tl.isClosedState(st)
  return dom.span {
    class = done and "tl-chip tl-blocked tl-unblocked" or "tl-chip tl-blocked",
    title = "Blocked by " .. blocker .. (done and " (finished)" or ""),
    "⛔ " .. tl.titleOf(blocker),
  }
end

-- The form for a task page's dates and progress, used in the projection
-- popover and in an expanded board card. Every field writes as soon as it
-- changes. `attrs` holds the current attribute values (tl.taskAttrs);
-- `subs` the task's subtasks, for progress without a value of its own;
-- `onChange(key, value)` runs after each write.
-- The open tasks other than page `except`, by title, for a "Blocked by" picker:
-- the panel's Choose… and /blocked use the same list.
local function openTaskRows(except)
  local rows = {}
  for _, t in ipairs(tl.sources(nil)) do
    if t.page ~= except and not tl.isClosedState(t.state) then
      table.insert(rows, { name = tl.plainText(t.name), description = t.page, page = t.page })
    end
  end
  table.sort(rows, function(a, b) return a.name < b.name end)
  return rows
end

local function attrForm(page, attrs, subs, onChange)
  local function changed(key, value)
    tl.setTaskAttr(page, key, value)
    if onChange then onChange(key, value) end
  end
  local function dateRow(key, label)
    local input
    input = dom.input {
      type = "date",
      class = "tl-date",
      value = attrs[key] or "",
      onchange = function(e) changed(key, e.target.value) end,
    }
    return dom.label {
      class = "tl-attr",
      dom.span { class = "tl-attr-label", label },
      input,
      dom.button {
        class = "tl-attr-clear",
        title = "Clear " .. string.lower(label),
        onclick = function(e)
          e.preventDefault()
          input.value = ""
          changed(key, nil)
        end,
        "×",
      },
    }
  end
  local auto = taskProgress(nil, subs)
  local pct = taskProgress(attrs.progress, subs) or 0
  local shown
  shown = dom.span { class = "tl-attr-value", attrs.progress and (pct .. "%") or (auto and (pct .. "% · subtasks") or "not set") }
  local range = dom.input {
    type = "range", min = "0", max = "100", step = "5", value = tostring(pct),
    class = "tl-range",
    oninput = function(e) shown.textContent = e.target.value .. "%" end,
    onchange = function(e) changed("progress", e.target.value) end,
  }
  -- Blocked by: another task page, chosen from the open ones
  -- shown as a link to the blocking task; "nothing" when there is none
  local blocker = linkTarget(attrs.blockedBy)
  local blockerName
  local function showBlocker(target, name)
    blocker = target
    blockerName.textContent = target and name or "nothing"
    if target then blockerName.setAttribute("title", name) else blockerName.removeAttribute("title") end
    if target then
      blockerName.setAttribute("href", "/" .. target)
      blockerName.classList.remove("tl-blocker-none")
    else
      blockerName.removeAttribute("href")
      blockerName.classList.add("tl-blocker-none")
    end
  end
  blockerName = dom.a {
    class = "tl-attr-value tl-blocker",
    onclick = function(e)
      e.preventDefault()
      if blocker then tl.closePopover(); editor.navigate(blocker) end
    end,
    "nothing",
  }
  showBlocker(blocker, blocker and tl.titleOf(blocker))
  local function chooseBlocker(e)
    e.preventDefault()
    local rows = openTaskRows(page)
    -- the picker is outside the panel; keep the panel open while it shows
    tl.picking = true
    local choice = pick("Blocked by which task?", rows)
    -- closing the picker refocuses and scrolls the editor a moment later;
    -- keep the panel open through that too
    js.window.setTimeout(function() tl.picking = false end, 400)
    if not choice then return end
    showBlocker(choice.page, choice.name)
    changed("blockedBy", "[[" .. choice.page .. "]]")
  end
  -- a div, not a label: a click on a label's text would press its first button
  local blockedRow = dom.div {
    class = "tl-attr",
    dom.span { class = "tl-attr-label", "Blocked by" },
    blockerName,
    dom.button { class = "tl-attr-pick", onclick = chooseBlocker, "Choose…" },
    dom.button {
      class = "tl-attr-clear",
      title = "Clear blocked by",
      onclick = function(e)
        e.preventDefault()
        showBlocker(nil)
        changed("blockedBy", nil)
      end,
      "×",
    },
  }
  return dom.div {
    class = "tl-attrs",
    dateRow("due", "Due"),
    dateRow("scheduled", "Scheduled"),
    blockedRow,
    dom.label {
      class = "tl-attr",
      dom.span { class = "tl-attr-label", "Progress" },
      range,
      shown,
      dom.button {
        class = "tl-attr-clear",
        title = auto and "Use subtasks" or "Clear progress",
        onclick = function(e)
          e.preventDefault()
          range.value = tostring(auto or 0)
          shown.textContent = auto and (auto .. "% · subtasks") or "not set"
          changed("progress", nil)
        end,
        "×",
      },
    },
  }
end

---------------------------------------------------------------------------
-- Board
--
-- One column per distinct `column` of the open states, plus a folded Done
-- column. Each card is a <details>: the summary is the card, the body holds
-- subtasks and notes. Card order is the order in which the project page lists
-- its projections; dragging a card rewrites that list.
---------------------------------------------------------------------------

-- The ⚑ due and ▸ scheduled chips of a task, red when past and amber when
-- today, unless the task is finished. Shared with the Focus list.
local function dateChips(t, now)
  local closed = isClosed(t)
  local chips = {}
  local function chip(date, mark, what)
    if not date then return end
    date = tostring(date)
    local cls = "tl-chip"
    if not closed and date < now then cls = cls .. " tl-overdue"
    elseif not closed and date == now then cls = cls .. " tl-today" end
    local text = date == now and "Today" or shortDate(date)
    table.insert(chips, dom.span { class = cls, title = what .. " " .. date, mark .. " " .. text })
  end
  chip(t.due, "⚑", "due")
  chip(t.scheduled, "▸", "scheduled")
  return chips
end

-- the first project the task links to, by folder; used for the card's chip
local function projectOf(t)
  local folder = tl.projectFolder()
  for _, l in ipairs(t.links or {}) do
    if startsWith(l, folder) then return l end
  end
end

-- Subtasks come from the index, not from the page text: markdown rendered in a
-- widget is attributed to the page it is shown on, so a checkbox drawn from raw
-- text would write into the project page instead of the task page.
local function subtasksByPage()
  local by = {}
  for _, s in ipairs(query[[from index.tasks() where _.parent]]) do
    by[s.page] = by[s.page] or {}
    table.insert(by[s.page], s)
  end
  for _, list in pairs(by) do
    table.sort(list, function(a, b) return a.pos < b.pos end)
  end
  return by
end

-- The chips under a card's title: project, dates, progress, blocked by.
local function cardChips(t, now, subs)
  local chips = {}
  local proj = projectOf(t)
  if proj then
    table.insert(chips, dom.span { class = "tl-chip", title = proj, basename(proj) })
  end
  for _, c in ipairs(dateChips(t, now)) do table.insert(chips, c) end
  local pct = taskProgress(t.progress, subs)
  if pct then table.insert(chips, progressChip(pct)) end
  local blocked = blockedChip(t.blockedBy)
  if blocked then table.insert(chips, blocked) end
  return chips
end

-- A board card for source task `t`, with its subtasks `subs`. Open, it shows
-- the task's dates, blocker and progress, and a button to the task page; the
-- task's notes and subtasks stay on that page. The form is built the first
-- time the card opens, so drawing a board reads no task page.
local function card(t, now, subs)
  local chips = cardChips(t, now, subs)
  local page = t.page
  local title = tl.plainText(t.name)
  local filled = false
  return dom.details {
    class = "tl-card",
    draggable = "true",
    ["data-page"] = page,
    ["data-state"] = t.state,
    ["data-cat"] = tl.categoryOf(t.state),
    ["data-project"] = projectOf(t) or "",
    -- progress from subtasks, kept for tl.refreshCard, which has no subtasks
    ["data-auto"] = tostring(taskProgress(nil, subs) or ""),
    ["data-title"] = title,
    ontoggle = function(e)
      if filled or not e.target.open then return end
      filled = true
      local slot = e.target.querySelector(".tl-card-notes")
      -- after a date or progress change, redraw the card's chips in place
      slot.appendChild(attrForm(page, tl.taskAttrs(page), subs, function()
        tl.refreshCard(page)
        tl.refreshStates()
      end))
    end,
    ondragstart = function(e)
      e.dataTransfer.setData("text/plain", page)
      e.target.classList.add("tl-dragging")
    end,
    ondragend = function(e)
      e.target.classList.remove("tl-dragging")
      tl.clearMarker()
    end,
    dom.summary {
      class = "tl-card-head",
      dom.span { class = "tl-icon", ["data-tl-state"] = shownState(t.state) },
      dom.span { class = "tl-title", title = title, title },
      dom.span { class = "tl-chips", table.unpack(chips) },
    },
    dom.div {
      class = "tl-card-body",
      dom.div { class = "tl-card-notes" },
      dom.div {
        class = "tl-actions",
        dom.button { class = "tl-button", onclick = function() editor.navigate(page) end, "View full task" },
        dom.button { class = "tl-button tl-delete", onclick = function() tl.deleteTaskPage(page) end, "Delete" },
      },
    },
  }
end

-- Update a column's count after cards moved in or out of it, and the number
-- of backlog cards its Show backlog button reports.
function tl.recount(col)
  if not col then return end
  local n = col.querySelectorAll(".tl-card").length
  col.querySelector(".tl-count").textContent = tostring(n)
  local fold = col.querySelector(".tl-fold-head")
  if fold then fold.textContent = tostring(n) .. " closed" end
  local toggle = col.querySelector(".tl-bl-toggle")
  if toggle then
    toggle.setAttribute("data-n", tostring(col.querySelectorAll('.tl-card[data-cat="backlog"]').length))
  end
end

-- Show card `el` in `state`: move it to that state's column on its board if
-- the column changes, and redraw its icon and counts. The page is not
-- written. A drop has already placed the card and passes the column it came
-- from.
local function placeCard(el, state, fromCol)
  local board = el.closest(".tl-board")
  local key = tl.columnOf(state)
  local target = board and board.querySelector('.tl-col[data-col="' .. key .. '"] .tl-cards')
  if not target then return end
  if not fromCol then
    fromCol = el.closest(".tl-col")
    if fromCol.getAttribute("data-col") ~= key then target.appendChild(el) end
  end
  el.querySelector(".tl-icon").setAttribute("data-tl-state", shownState(state))
  el.setAttribute("data-state", state)
  el.setAttribute("data-cat", tl.categoryOf(state))
  tl.recount(fromCol)
  tl.recount(target.closest(".tl-col"))
end

-- Redraw the chips of task page `page`'s card on screen, from the page's
-- current attributes: after its dates or progress changed in a form.
function tl.refreshCard(page)
  local el = js.window.document.querySelector('.tl-card[data-page="' .. page .. '"]')
  if not el then return end
  local attrs = tl.taskAttrs(page)
  local auto = el.getAttribute("data-auto")
  local project = el.getAttribute("data-project")
  local t = {
    page = page,
    state = el.getAttribute("data-state"),
    due = attrs.due, scheduled = attrs.scheduled,
    progress = attrs.progress or (auto ~= "" and auto or nil),
    blockedBy = attrs.blockedBy,
    links = { project },
  }
  local span = el.querySelector(".tl-chips")
  span.innerHTML = ""
  for _, c in ipairs(cardChips(t, today(), nil)) do span.appendChild(c) end
end

-- Move a card to its state's column at once, then write the task page.
function tl.moveCard(page, state, fromCol)
  local el = js.window.document.querySelector('.tl-card[data-page="' .. page .. '"]')
  if el then placeCard(el, state, fromCol) end
  tl.setTaskPageState(page, state)
end

-- the order in which the project page lists its task projections
local function listOrder(project)
  local rank, n = {}, 0
  local ok, text = pcall(tl.read, project)
  if not ok or not text then return rank end
  local pattern = "^%s*[-*] %[%[(" .. escapePattern(tl.taskFolder()) .. "[^%]|]+)"
  for _, line in ipairs(splitLines(text)) do
    local p = string.match(line, pattern)
    if p and not rank[p] then n = n + 1; rank[p] = n end
  end
  return rank
end

-- Append a projection to the end of the project page's task list, or start a
-- `## Tasks` list.
local function appendToList(lines, projection)
  local last
  local pattern = "^%s*[-*] %[%[" .. escapePattern(tl.taskFolder())
  for j, l in ipairs(lines) do
    if string.match(l, pattern) then last = j end
  end
  if last then
    table.insert(lines, last + 1, projection)
  else
    while #lines > 0 and string.match(lines[#lines], "^%s*$") do table.remove(lines) end
    table.insert(lines, "")
    table.insert(lines, "## Tasks")
    table.insert(lines, "")
    table.insert(lines, projection)
  end
end

-- Move a projection in the project page's list to just before `beforePage`,
-- else just after `afterPage`, else to the end of the list.
function tl.reorder(project, page, alias, beforePage, afterPage)
  local ls = splitLines(tl.read(project))
  local function find(p)
    if not p then return nil end
    local pattern = "^%s*[-*] %[%[" .. escapePattern(p) .. "[|%]]"
    for i, l in ipairs(ls) do
      if string.match(l, pattern) then return i end
    end
  end
  local at = find(page)
  if not beforePage and not afterPage and at then return end
  local moved = at and table.remove(ls, at) or ("- [[" .. page .. "|" .. (alias or page) .. "]]")
  local i = find(beforePage)
  if not i then
    i = find(afterPage)
    if i then i = i + 1 end
  end
  if i then table.insert(ls, i, moved) else appendToList(ls, moved) end
  tl.write(project, table.concat(ls, "\n") .. "\n")
end

-- Drag and drop. While a card is dragged over a column, a marker line shows
-- where it will land; the drop puts the card there, changes its state if the
-- column changed, and moves its projection on the project page to match.
function tl.clearMarker()
  local m = js.window.document.querySelector(".tl-drop-marker")
  if m then m.remove() end
end

-- put the marker before the first card whose middle is below the pointer
function tl.placeMarker(list, y)
  local doc = js.window.document
  local m = doc.querySelector(".tl-drop-marker")
  if not m then
    m = doc.createElement("div")
    m.className = "tl-drop-marker"
  end
  local cards = list.querySelectorAll(".tl-card")
  for i = 0, cards.length - 1 do
    local c = cards.item(i)
    if not c.classList.contains("tl-dragging") then
      local r = c.getBoundingClientRect()
      if y < r.top + r.height / 2 then
        list.insertBefore(m, c)
        return
      end
    end
  end
  list.appendChild(m)
end

-- Land the dragged card `page` in column `columnKey` at the marker.
function tl.dropCard(page, columnKey, project)
  local doc = js.window.document
  local el = doc.querySelector('.tl-card[data-page="' .. page .. '"]')
  local m = doc.querySelector(".tl-drop-marker")
  if not el then tl.clearMarker(); return end
  el.classList.remove("tl-dragging")
  local fromCol = el.closest(".tl-col")
  local fromKey = fromCol.getAttribute("data-col")
  local state = tl.columnState(columnKey)
  local beforePage, afterPage
  if m then
    local n = m.nextElementSibling
    if n and n.getAttribute("data-page") == page then n = n.nextElementSibling end
    local p = m.previousElementSibling
    if p and p.getAttribute("data-page") == page then p = p.previousElementSibling end
    beforePage = n and n.getAttribute("data-page")
    afterPage = p and p.getAttribute("data-page")
    m.parentNode.insertBefore(el, m)
    m.remove()
    if fromKey ~= columnKey then tl.moveCard(page, state, fromCol) end
  elseif fromKey ~= columnKey then
    tl.moveCard(page, state)
  end
  if project then tl.reorder(project, page, el.getAttribute("data-title"), beforePage, afterPage) end
end

-- The Hide backlog button: hides backlog-category cards on every board, and
-- remembers that in this browser, for all projects.
local HIDE_BACKLOG_KEY = "throughline.hideBacklog"

function tl.toggleBacklog(el)
  local hide = not el.closest(".tl-board").classList.contains("tl-hide-backlog")
  local boards = js.window.document.querySelectorAll(".tl-board")
  for i = 0, boards.length - 1 do
    local b = boards.item(i)
    if hide then b.classList.add("tl-hide-backlog") else b.classList.remove("tl-hide-backlog") end
  end
  storeSet(HIDE_BACKLOG_KEY, hide and "1" or "0")
end

-- The New task button at the end of the To do column. Asks for the task,
-- writes its task page (linked to the project, in the column's state), adds
-- the projection to the project page's list, and puts the card on the board.
function tl.newTaskCard(project, columnKey, el)
  local text = editor.prompt("New task in " .. basename(project), "")
  if not text or trim(text) == "" then return end
  text = trim(text)
  local state = tl.columnState(columnKey) or " "
  local target = tl.taskFolder() .. tl.slugFor(text)
  space.writePage(target, TASK_PAGE_FRONTMATTER .. "- [" .. state .. "] " .. text .. " [[" .. project .. "]]\n")
  local ls = splitLines(tl.read(project))
  appendToList(ls, "- [[" .. target .. "|" .. tl.plainText(text) .. "]]")
  tl.write(project, table.concat(ls, "\n") .. "\n")
  tl.noteState(target, state)
  local col = el.closest(".tl-col")
  local t = { page = target, ref = target, name = text, state = state, links = { project } }
  col.querySelector(".tl-cards").appendChild(card(t, today(), {}))
  tl.recount(col)
  editor.flashNotification("Created " .. target)
end

-- A board column. opts: `closed` folds its cards under a "N closed" summary;
-- `iconState` is the state whose icon heads the column; `backlog` adds the
-- Hide backlog button; `newTask` adds the New task button.
local function column(title, columnKey, cards, project, opts)
  local closed = opts.closed
  local list = dom.div { class = "tl-cards", table.unpack(cards) }
  if closed then
    list = dom.details {
      class = "tl-fold",
      dom.summary { class = "tl-fold-head", tostring(#cards) .. " closed" },
      list,
    }
  end
  return dom.div {
    class = closed and "tl-col tl-col-closed" or "tl-col",
    ["data-col"] = columnKey,
    ondragover = function(e)
      e.preventDefault()
      local l = js.window.document.querySelector('.tl-col[data-col="' .. columnKey .. '"] .tl-cards')
      -- a folded Done column shows no line; the card lands at its end
      if l and l.offsetParent then tl.placeMarker(l, e.clientY) end
    end,
    ondrop = function(e)
      e.preventDefault()
      local page = e.dataTransfer.getData("text/plain")
      if not page or page == "" then tl.clearMarker(); return end
      tl.dropCard(page, columnKey, project)
    end,
    dom.div {
      class = "tl-col-head",
      dom.span { class = "tl-icon", ["data-tl-state"] = shownState(opts.iconState or "x") },
      dom.span { class = "tl-col-title", title },
      dom.span { class = "tl-count", tostring(#cards) },
      opts.backlog and dom.button {
        class = "tl-bl-toggle",
        title = "Hide or show backlog tasks",
        ["data-n"] = tostring(opts.backlog),
        onclick = function(e) tl.toggleBacklog(e.target) end,
        dom.span { class = "tl-bl-hide", "Hide backlog" },
        dom.span { class = "tl-bl-show", "Show backlog" },
      } or dom.span {},
    },
    list,
    opts.newTask and dom.button {
      class = "tl-newtask",
      onclick = function(e) tl.newTaskCard(project, columnKey, e.target) end,
      "New task",
    } or dom.span {},
  }
end

-- ${throughline.board()}: the board of the page it is on, or of `project`.
-- Cards follow the page's list of projections; unlisted ones go last, by due.
function tl.board(project)
  project = project or editor.getCurrentPage()
  local now = today()
  local tasks = tl.sources(project)
  local rank = listOrder(project)
  table.sort(tasks, function(a, b)
    local ra, rb = rank[a.page], rank[b.page]
    if ra and rb then return ra < rb end
    if ra or rb then return ra ~= nil end
    return (a.due or "9999") < (b.due or "9999")
  end)
  local subs = subtasksByPage()
  -- columns holding a backlog state get the Hide backlog button; the column
  -- of the first planned state gets New task
  local backlogCols, newTaskCol = {}, nil
  for _, st in ipairs(tl.states()) do
    local cat = tl.categoryOf(st.state)
    if cat == "backlog" then backlogCols[tl.columnOf(st.state)] = true end
    if cat == "planned" and not newTaskCol then newTaskCol = tl.columnOf(st.state) end
  end
  -- one column per distinct `column` (or label) of the open states, in order
  local cols, seen = {}, {}
  for _, st in ipairs(tl.states()) do
    local key = st.column or st.label
    if not tl.isClosedState(st.state) and not seen[key] then
      seen[key] = true
      local cards, backlog = {}, 0
      for _, t in ipairs(tasks) do
        if not isClosed(t) and tl.columnOf(t.state) == key then
          table.insert(cards, card(t, now, subs[t.page]))
          if tl.categoryOf(t.state) == "backlog" then backlog = backlog + 1 end
        end
      end
      table.insert(cols, column(key, key, cards, project, {
        iconState = st.state,
        backlog = backlogCols[key] and backlog or nil,
        newTask = key == newTaskCol,
      }))
    end
  end
  local closed = {}
  for _, t in ipairs(tasks) do
    if isClosed(t) then table.insert(closed, card(t, now, subs[t.page])) end
  end
  table.insert(cols, column("Done", "closed", closed, project, { closed = true, iconState = "x" }))
  local hideBacklog = storeGet(HIDE_BACKLOG_KEY) == "1"
  return widget.html(dom.div { class = hideBacklog and "tl-board tl-hide-backlog" or "tl-board", table.unpack(cols) })
end

---------------------------------------------------------------------------
-- Projects
--
-- A project is a page tagged #project. Its `status:` frontmatter names one of
-- the configured project statuses; each status has a category (backlog,
-- planned, started, paused, completed, canceled) that decides where the
-- overview puts it. Health comes from dated update headings on the page:
--
--   ## Updates
--   ### 2026-10-19 [health: at-risk]
--   Waiting on a delivery.
---------------------------------------------------------------------------

local healthLabels = { ["on-track"] = "On track", ["at-risk"] = "At risk", ["off-track"] = "Off track" }

-- "On track", "on_track" and "ontrack" all become "on-track"
local function normHealth(h)
  h = string.gsub(string.lower(trim(tostring(h or ""))), "[%s_]+", "-")
  if h == "ontrack" then h = "on-track" end
  if h == "atrisk" then h = "at-risk" end
  if h == "offtrack" then h = "off-track" end
  return h
end

-- every page tagged #project, outside Library/
function tl.projectList()
  local out = {}
  for _, p in ipairs(query[[from index.tag "page"]]) do
    if contains(p.tags, "project") and not startsWith(p.name, "Library/") then
      table.insert(out, p)
    end
  end
  return out
end

-- the configured status a project page's `status:` names, matched on the
-- status key or its label; no status means the first started one
function tl.statusOf(p)
  local statuses = tl.projectStatuses()
  local want = p.status and string.lower(trim(tostring(p.status))) or nil
  if not want or want == "" then
    for _, s in ipairs(statuses) do
      if s.category == "started" then return s end
    end
    return statuses[1] or { status = "active", label = "Active", category = "started" }
  end
  for _, s in ipairs(statuses) do
    if string.lower(s.status) == want or string.lower(s.label or "") == want then return s end
  end
  -- an unknown status gets its own section, treated as started
  return { status = want, label = tostring(p.status), category = "started", unknown = true }
end

-- `### 2026-10-19 [health: at-risk]` headings and the text under each, newest
-- first. Read from the page text: SilverBullet also files the attribute as a
-- page attribute, but only one per page.
function tl.updatesOf(text)
  local ups, cur = {}, nil
  for _, line in ipairs(splitLines(text)) do
    local date, health = string.match(line, "^#+%s+(%d%d%d%d%-%d%d%-%d%d)[^%[]*%[health:%s*([^%]]+)%]")
    if date then
      cur = { date = date, health = normHealth(health), lines = {} }
      table.insert(ups, cur)
    elseif string.match(line, "^#") then
      cur = nil
    elseif cur then
      table.insert(cur.lines, line)
    end
  end
  for _, u in ipairs(ups) do u.text = trim(table.concat(u.lines, "\n")) end
  table.sort(ups, function(a, b) return a.date > b.date end)
  return ups
end

-- what the health pill shows: the latest health, or stale or missing when an
-- active project's latest update is older than the cadence; nothing for
-- finished projects
function tl.healthOf(status, ups, now)
  if status.category == "completed" or status.category == "canceled" then
    return { key = "none", label = "No update expected" }
  end
  local u = ups[1]
  if not u then return { key = "none", label = "No updates" } end
  local age = daysAgo(u.date, now) or 0
  local days = tl.updateDays()
  local label = healthLabels[u.health] or u.health
  if status.category == "started" then
    if age > 2 * days then
      return { key = "missing", label = "Update missing", health = u.health, age = age }
    end
    if age > days then
      return { key = u.health, label = label, stale = true, age = age }
    end
  end
  return { key = u.health, label = label, age = age }
end

-- `text` with frontmatter `key` set to `value`, adding the key, or the whole
-- frontmatter block, when missing
local function frontmatterSet(text, key, value)
  local fm = string.match(text, "^%-%-%-\n(.-\n)%-%-%-\n")
  local line = key .. ": " .. value .. "\n"
  if fm then
    local body = string.sub(text, #fm + 9)
    local newFm, n = string.gsub("\n" .. fm, "\n" .. escapePattern(key) .. ":[^\n]*\n", function() return "\n" .. line end, 1)
    if n == 0 then newFm = "\n" .. fm .. line end
    return "---\n" .. string.sub(newFm, 2) .. "---\n" .. body
  end
  return "---\n" .. line .. "---\n" .. text
end

function tl.setProjectStatus(project, status)
  tl.write(project, frontmatterSet(tl.read(project), "status", status))
end

-- Page name -> position of its first [[link]] in `text`. Orders the overview's
-- cards the way the page it sits on links to the projects, if it does.
local function mentionOrder(text)
  local rank, n = {}, 0
  for name in string.gmatch(text or "", "%[%[([^%]|]+)") do
    if not rank[name] then n = n + 1; rank[name] = n end
  end
  return rank
end

-- Time logged against a project: `[time: 2h30m]` on any list item or task
-- that links to it. The day is the item's own `date`, else the ISO date in
-- its page's name (journal pages).
local function timeEntries()
  local out, seen = {}, {}
  local function add(o)
    if o.time and not seen[o.ref] then
      seen[o.ref] = true
      local day = o.date and tostring(o.date) or string.match(o.page or "", "(%d%d%d%d%-%d%d%-%d%d)")
      table.insert(out, { links = o.links or {}, minutes = minutesOf(o.time), day = day })
    end
  end
  for _, o in ipairs(query[[from index.tag "item" where _.time]]) do add(o) end
  for _, o in ipairs(query[[from index.tasks() where _.time]]) do add(o) end
  return out
end

-- How many days ahead the "Due in 7 days" stat looks.
local SOON_DAYS = 7

-- Everything the overview shows, per project, gathered once per render:
-- status, updates, health, its tasks counted per board column, progress,
-- overdue and due-soon counts, the next due task, time logged and the latest
-- change to the project page or any of its task pages.
local function projectData(now)
  local sources = tl.sources(nil)
  local pageMeta = {}
  for _, p in ipairs(query[[from index.tag "page"]]) do pageMeta[p.name] = p end
  local times = timeEntries()
  local wk = weekStart(now)
  local monthAgo = addDays(now, -27)
  local out = {}
  for _, p in ipairs(tl.projectList()) do
    local d = { page = p, name = p.name, title = basename(p.name), status = tl.statusOf(p) }
    local ok, text = pcall(tl.read, p.name)
    d.updates = tl.updatesOf(ok and text or "")
    d.health = tl.healthOf(d.status, d.updates, now)
    d.tasks = {}
    for _, t in ipairs(sources) do
      if contains(t.links, p.name) then table.insert(d.tasks, t) end
    end
    local counts, open, done, cancelled, overdue, soon = {}, 0, 0, 0, 0, 0
    local nextDue, nextTask
    local last = tostring(p.lastModified or "")
    local soonEnd = addDays(now, SOON_DAYS)
    for _, t in ipairs(d.tasks) do
      local cat = tl.categoryOf(t.state)
      local col = tl.columnOf(t.state)
      counts[col] = (counts[col] or 0) + 1
      if cat == "done" then done = done + 1
      elseif cat == "cancelled" then cancelled = cancelled + 1
      else
        open = open + 1
        if t.due then
          local due = tostring(t.due)
          if due < now then overdue = overdue + 1 elseif due <= soonEnd then soon = soon + 1 end
          if not nextDue or due < nextDue then nextDue, nextTask = due, t end
        end
      end
      local m = pageMeta[t.page]
      if m and tostring(m.lastModified or "") > last then last = tostring(m.lastModified) end
    end
    d.counts, d.open, d.done, d.overdue, d.soon = counts, open, done, overdue, soon
    d.total = #d.tasks - cancelled
    d.progress = d.total > 0 and math.floor(done * 100 / d.total + 0.5) or nil
    d.nextDue, d.nextTask, d.lastActivity = nextDue, nextTask, last
    local week, month, all = 0, 0, 0
    for _, e in ipairs(times) do
      if contains(e.links, p.name) then
        all = all + e.minutes
        if e.day and e.day >= wk then week = week + e.minutes end
        if e.day and e.day >= monthAgo then month = month + e.minutes end
      end
    end
    d.time = { week = week, month = month, all = all }
    table.insert(out, d)
  end
  return out
end

-- the board columns, in board order, with the state whose icon stands for each
local function boardColumns()
  local cols, seen = {}, {}
  for _, st in ipairs(tl.states()) do
    local key = tl.isClosedState(st.state) and "closed" or (st.column or st.label)
    if not seen[key] then
      seen[key] = true
      table.insert(cols, { key = key, label = key == "closed" and "Done" or key, state = key == "closed" and "x" or st.state })
    end
  end
  return cols
end

-- the coloured dot and word for a health from tl.healthOf
local function healthPill(h)
  local cls = "tl-health"
  if h.stale then cls = cls .. " tl-stale" end
  local title = h.label
  if h.age then title = title .. ", updated " .. ago(addDays(today(), -h.age), today()) end
  return dom.span { class = cls, ["data-health"] = h.key, title = title, dom.span { class = "tl-health-dot" }, h.label }
end

-- a ring filled to `pct` percent; the stylesheet draws it from --tl-pct
local function progressRing(pct)
  if not pct then return dom.span { class = "tl-progress tl-progress-none", "No tasks" } end
  return dom.span {
    class = "tl-progress",
    title = pct .. "% of tasks done",
    style = "--tl-pct:" .. pct,
    dom.span { class = "tl-ring" },
    pct .. "%",
  }
end

-- the status dropdown on an expanded card; changing it moves the card
local function statusSelect(d)
  local options = {}
  for _, s in ipairs(tl.projectStatuses()) do
    local o = { value = s.status, s.label }
    if s.status == d.status.status then o.selected = "selected" end
    table.insert(options, dom.option(o))
  end
  if d.status.unknown then
    table.insert(options, dom.option { value = d.status.status, selected = "selected", d.status.label })
  end
  local name = d.name
  return dom.select {
    class = "tl-pstatus",
    title = "Project status",
    onclick = function(e) e.stopPropagation() end,
    onchange = function(e) tl.changeProjectStatus(name, e.target.value, e.target) end,
    table.unpack(options),
  }
end

-- one label and value in the expanded card's grid of numbers
local function stat(label, value, cls)
  return dom.div { class = "tl-stat " .. (cls or ""), dom.span { class = "tl-stat-label", label }, dom.span { class = "tl-stat-value", value } }
end

-- A project card. Collapsed: name, health, progress, overdue count and tasks
-- per board column. Expanded: the latest update and the numbers. Clicking the
-- name opens the project; clicking anywhere else expands the card.
local function projectCard(d, now, cols)
  local counts = {}
  for _, c in ipairs(cols) do
    local n = d.counts[c.key] or 0
    table.insert(counts, dom.span {
      class = n == 0 and "tl-ccount tl-zero" or "tl-ccount",
      title = c.label .. ": " .. n,
      dom.span { class = "tl-icon", ["data-tl-state"] = shownState(c.state) },
      tostring(n),
    })
  end
  local u = d.updates[1]
  local latest
  if u then
    latest = dom.div {
      class = "tl-update",
      dom.div {
        class = "tl-update-head",
        dom.span { class = "tl-update-date", shortDate(u.date) .. " · " .. ago(u.date, now) },
        healthPill({ key = u.health, label = healthLabels[u.health] or u.health }),
      },
      dom.div { class = "tl-update-text", u.text ~= "" and u.text or "_No text._" },
    }
  else
    latest = dom.div { class = "tl-update tl-update-empty", "No updates yet. Post one with “Post update”." }
  end
  local nextDue = "–"
  if d.nextDue then nextDue = shortDate(d.nextDue) .. " · " .. tl.plainText(d.nextTask.name) end
  local name = d.name
  return dom.details {
    class = "tl-pcard",
    ["data-project"] = name,
    ["data-cat"] = d.status.category,
    dom.summary {
      class = "tl-pcard-head",
      dom.div {
        class = "tl-pcard-top",
        dom.span { class = "tl-picon", ["data-cat"] = d.status.category, title = d.status.label },
        dom.a {
          class = "tl-pname",
          href = "/" .. name,
          onclick = function(e) e.preventDefault(); e.stopPropagation(); editor.navigate(name) end,
          d.title,
        },
        dom.span { class = "tl-chev", "▾" },
      },
      dom.div {
        class = "tl-pcard-line",
        healthPill(d.health),
        progressRing(d.progress),
        d.overdue > 0 and dom.span { class = "tl-chip tl-overdue", d.overdue .. " overdue" } or dom.span {},
      },
      #d.tasks > 0 and dom.div { class = "tl-pcard-counts", table.unpack(counts) } or dom.span {},
    },
    dom.div {
      class = "tl-pcard-body",
      latest,
      dom.div {
        class = "tl-stats",
        dom.div { class = "tl-stat", dom.span { class = "tl-stat-label", "Status" }, statusSelect(d) },
        stat("Progress", d.total > 0 and (d.done .. " of " .. d.total .. " done") or "No task pages"),
        stat("Open", tostring(d.open)),
        stat("Overdue", tostring(d.overdue), d.overdue > 0 and "tl-bad" or nil),
        stat("Due in " .. SOON_DAYS .. " days", tostring(d.soon)),
        stat("Next due", nextDue),
        stat("Time this week", fmtMinutes(d.time.week)),
        stat("Time, 4 weeks", fmtMinutes(d.time.month)),
        stat("Time, total", fmtMinutes(d.time.all)),
        stat("Updates", #d.updates > 0 and (#d.updates .. ", last " .. ago(d.updates[1].date, now)) or "none"),
        stat("Last activity", ago(d.lastActivity, now)),
      },
      dom.div {
        class = "tl-actions",
        dom.button { class = "tl-button", onclick = function() editor.navigate(name) end, "Open project" },
        dom.button { class = "tl-button", onclick = function() tl.postUpdate(name) end, "Post update" },
      },
    },
  }
end

-- the order of the overview's sections, by status category
local categoryRank = { started = 1, planned = 2, paused = 3, backlog = 4, completed = 5, canceled = 6 }

-- Move a card to its new status's section at once, then write the page.
function tl.changeProjectStatus(project, status, el)
  tl.setProjectStatus(project, status)
  local cat
  for _, s in ipairs(tl.projectStatuses()) do
    if s.status == status then cat = s.category end
  end
  local card = el and el.closest(".tl-pcard")
  local root = el and el.closest(".tl-projects")
  if card and root and cat then
    card.setAttribute("data-cat", cat)
    local icon = card.querySelector(".tl-picon")
    if icon then icon.setAttribute("data-cat", cat) end
    local grid = root.querySelector('.tl-psection[data-status="' .. status .. '"] .tl-pgrid')
    if grid then
      grid.appendChild(card)
      tl.recountSections(root)
    end
  end
  editor.flashNotification(basename(project) .. ": " .. status)
end

-- Update section counts, hide empty sections and update the number on the
-- "Show completed" button after a card moved.
function tl.recountSections(root)
  local secs = root.querySelectorAll(".tl-psection")
  local hidden = 0
  for i = 0, secs.length - 1 do
    local s = secs.item(i)
    local n = s.querySelectorAll(".tl-pcard").length
    s.querySelector(".tl-count").textContent = tostring(n)
    if n == 0 then s.classList.add("tl-empty") else s.classList.remove("tl-empty") end
    if s.classList.contains("tl-psection-closed") then hidden = hidden + n end
  end
  local b = root.querySelector(".tl-toggle-closed")
  if b then b.setAttribute("data-n", tostring(hidden)) end
end

-- the "Show completed" button: remembered per page in this browser
function tl.toggleClosed(el)
  local root = el.closest(".tl-projects")
  local on = not root.classList.contains("tl-show-closed")
  if on then root.classList.add("tl-show-closed") else root.classList.remove("tl-show-closed") end
  storeSet("throughline.showClosed:" .. editor.getCurrentPage(), on and "1" or "0")
end

-- ${throughline.projects()}: every project as a card, in sections by status.
-- opts.status limits it to some statuses, e.g. { status = { "active" } }.
function tl.projects(opts)
  opts = opts or {}
  local now = today()
  local cols = boardColumns()
  local data = projectData(now)
  local host = editor.getCurrentPage()
  local okHost, hostText = pcall(tl.read, host)
  local rank = mentionOrder(okHost and hostText or "")
  table.sort(data, function(a, b)
    local ra, rb = rank[a.name], rank[b.name]
    if ra and rb then return ra < rb end
    if ra or rb then return ra ~= nil end
    local da, db = a.nextDue or "9999", b.nextDue or "9999"
    if da ~= db then return da < db end
    return a.title < b.title
  end)
  -- sections: configured statuses, then unknown ones, ordered by category
  local sections, byStatus = {}, {}
  local function section(s)
    if not byStatus[s.status] then
      byStatus[s.status] = { status = s, cards = {} }
      table.insert(sections, byStatus[s.status])
    end
    return byStatus[s.status]
  end
  for _, s in ipairs(tl.projectStatuses()) do section(s) end
  local only = opts.status
  if type(only) == "string" then only = { only } end
  local hiddenCount = 0
  for _, d in ipairs(data) do
    if not only or contains(only, d.status.status) then
      table.insert(section(d.status).cards, projectCard(d, now, cols))
    end
  end
  local order = {}
  for i, s in ipairs(sections) do order[s] = i end
  table.sort(sections, function(a, b)
    local ca, cb = categoryRank[a.status.category] or 9, categoryRank[b.status.category] or 9
    if ca ~= cb then return ca < cb end
    return order[a] < order[b]
  end)
  local nodes = {}
  for _, s in ipairs(sections) do
    local closed = s.status.category == "completed" or s.status.category == "canceled"
    if closed then hiddenCount = hiddenCount + #s.cards end
    local cls = "tl-psection"
    if closed then cls = cls .. " tl-psection-closed" end
    if #s.cards == 0 then cls = cls .. " tl-empty" end
    table.insert(nodes, dom.div {
      class = cls,
      ["data-status"] = s.status.status,
      dom.div {
        class = "tl-psection-head",
        dom.span { class = "tl-picon", ["data-cat"] = s.status.category },
        dom.span { class = "tl-psection-title", s.status.label },
        dom.span { class = "tl-count", tostring(#s.cards) },
      },
      dom.div { class = "tl-pgrid", table.unpack(s.cards) },
    })
  end
  local show = opts.showCompleted or storeGet("throughline.showClosed:" .. host) == "1"
  return widget.html(dom.div {
    class = show and "tl-projects tl-show-closed" or "tl-projects",
    dom.div {
      class = "tl-ptoolbar",
      dom.span { class = "tl-ptoolbar-title", "Projects" },
      dom.span { class = "tl-ptoolbar-count", tostring(#data) },
      dom.span { class = "tl-spacer" },
      dom.button {
        class = "tl-toggle-closed",
        ["data-n"] = tostring(hiddenCount),
        onclick = function(e) tl.toggleClosed(e.target) end,
        dom.span { class = "tl-when-hidden", "Show completed" },
        dom.span { class = "tl-when-shown", "Hide completed" },
      },
      dom.button { class = "tl-button", onclick = function() tl.newProject() end, "New project" },
    },
    table.unpack(nodes),
  })
end

-- The project a command acts on: the one given, else the open page if it is
-- a project, else one the user picks.
local function chooseProject(project, question)
  project = project or editor.getCurrentPage()
  local rows = {}
  for _, p in ipairs(tl.projectList()) do
    if p.name == project then return project end
    table.insert(rows, { name = p.name })
  end
  if #rows == 0 then
    editor.flashNotification("No projects yet: tag a page #project, or run Throughline: New project", "error")
    return nil
  end
  local choice = pick(question, rows)
  return choice and choice.name
end

-- Throughline: Post update. Asks for a health and a line of text, and puts
-- the update first under `## Updates`, adding the heading if needed.
function tl.postUpdate(project)
  project = chooseProject(project, "Post an update for which project?")
  if not project then return end
  local h = pick("How is " .. basename(project) .. " going?", {
    { name = "On track", value = "on-track" },
    { name = "At risk", value = "at-risk" },
    { name = "Off track", value = "off-track" },
  })
  if not h then return end
  local text = editor.prompt("Update for " .. basename(project) .. " (" .. h.name .. ")", "")
  if text == nil then return end
  local block = "### " .. today() .. " [health: " .. h.value .. "]\n" .. trim(text) .. "\n"
  local ls = splitLines(tl.read(project))
  local at
  for i, l in ipairs(ls) do
    if string.match(l, "^##%s+Updates%s*$") then at = i; break end
  end
  if not at then
    while #ls > 0 and string.match(ls[#ls], "^%s*$") do table.remove(ls) end
    table.insert(ls, "")
    table.insert(ls, "## Updates")
    at = #ls
  end
  -- newest first: right under the heading, one blank line on either side
  while ls[at + 1] and string.match(ls[at + 1], "^%s*$") do table.remove(ls, at + 1) end
  local ins = { "" }
  for _, l in ipairs(splitLines(block)) do table.insert(ins, l) end
  if ls[at + 1] then table.insert(ins, "") end
  for j, l in ipairs(ins) do table.insert(ls, at + j, l) end
  tl.write(project, table.concat(ls, "\n") .. "\n")
  editor.flashNotification("Update posted to " .. basename(project))
end

-- Throughline: Set project status
function tl.pickProjectStatus(project)
  project = chooseProject(project, "Set the status of which project?")
  if not project then return end
  local rows = {}
  for _, s in ipairs(tl.projectStatuses()) do table.insert(rows, { name = s.label, status = s.status }) end
  local choice = pick("Status of " .. basename(project), rows)
  if choice then
    tl.setProjectStatus(project, choice.status)
    editor.flashNotification(basename(project) .. ": " .. choice.name)
  end
end

-- Throughline: New project, and the overview's New project button
function tl.newProject()
  local name = editor.prompt("New project name", "")
  if not name or trim(name) == "" then return end
  local page = tl.projectFolder() .. trim(name)
  if pageExists(page) then
    editor.flashNotification(page .. " already exists", "error")
    return
  end
  space.writePage(page, "---\ntags: project\nstatus: active\n---\n${throughline.board()}\n\n## Tasks\n\n## Updates\n")
  editor.navigate(page)
end

command.define { name = "Throughline: New project", run = function() throughline.newProject() end }
command.define { name = "Throughline: Post update", run = function() throughline.postUpdate() end }
command.define { name = "Throughline: Set project status", run = function() throughline.pickProjectStatus() end }

---------------------------------------------------------------------------
-- Focus
--
-- Every open task in the space, sorted into fixed sections. The list is
-- built once with every row; the filter bar only hides and shows rows, using
-- the data- attributes each row carries.
---------------------------------------------------------------------------

local focusSections = {
  { key = "overdue",  label = "Overdue" },
  { key = "doing",    label = "Doing" },
  { key = "today",    label = "Today" },
  { key = "held",     label = "On hold" },
  { key = "upcoming", label = "Upcoming" },
  { key = "later",    label = "Later",   folded = true },
  { key = "backlog",  label = "Backlog", folded = true },
}

local function earliest(a, b)
  if a and b then return a < b and a or b end
  return a or b
end

-- The section a task belongs to. Dates come first, so a backlog task that is
-- due still shows up when it is due. `horizon` is the end of Upcoming.
local function focusSection(t, now, horizon)
  local cat = tl.categoryOf(t.state)
  local due = t.due and tostring(t.due) or nil
  local sch = t.scheduled and tostring(t.scheduled) or nil
  if (due and due < now) or (sch and sch < now) then return "overdue" end
  if cat == "active" then return "doing" end
  if due == now or sch == now then return "today" end
  if cat == "held" then return "held" end
  local d = earliest(due, sch)
  if d and d <= horizon then return "upcoming" end
  if cat == "backlog" then return "backlog" end
  return "later"
end

-- Every open task in the space: task-page sources, every task on other
-- pages, and dated subtasks on task pages. Library pages are left out.
local function focusTasks()
  local folder = tl.taskFolder()
  local sources, sourceOf = {}, {}
  for _, t in ipairs(tl.sources(nil)) do sources[t.ref] = true; sourceOf[t.page] = t end
  local out = {}
  for _, t in ipairs(query[[from index.tasks()]]) do
    if not startsWith(t.page, "Library/") and not isClosed(t) then
      local onTaskPage = startsWith(t.page, folder)
      if not onTaskPage or sources[t.ref] or t.due or t.scheduled then
        table.insert(out, t)
      end
    end
  end
  return out, sourceOf
end

-- the top-level folder of a page, "" for a page at the top level
local function folderOf(page)
  return string.match(page, "^([^/]+)/") or ""
end

-- The date ranges a task falls in, as space-separated words for the "when"
-- filter: overdue, today, week, month, or undated.
-- `ends` holds the last day of the next 7 and 30 days, worked out once per
-- render: { week =, month = }.
local function whenTokens(t, now, ends)
  local d = t._date
  if not d then return "undated" end
  local tok = {}
  if d < now then table.insert(tok, "overdue") end
  if d == now then table.insert(tok, "today") end
  if d <= ends.week then table.insert(tok, "week") end
  if d <= ends.month then table.insert(tok, "month") end
  return table.concat(tok, " ")
end

-- Set the state of the task at `pos` on `page`, for tasks that are not a task
-- page's own. The position comes from the index and goes stale once an
-- earlier line on the page changes length, so the line must still hold the
-- task's text; otherwise the task is looked up by its text.
function tl.setTaskStateAt(page, pos, name, state)
  local text = tl.read(page)
  local plain = tl.plainText(name or "")
  local probe = string.sub(plain, 1, 30)
  local function taskLine(s)
    return string.match(s, "^%s*[-*] %[[^%]]*%]")
  end
  local function lineAt(p)
    local st = p + 1
    while st > 1 and string.sub(text, st - 1, st - 1) ~= "\n" do st = st - 1 end
    local en = string.find(text, "\n", st, true) or (#text + 1)
    return st, en
  end
  local st, en = lineAt(pos or 0)
  local line = string.sub(text, st, en - 1)
  if not taskLine(line) or (probe ~= "" and not string.find(tl.plainText(line), probe, 1, true)) then
    st = nil
    local p = 1
    while p <= #text do
      local e = string.find(text, "\n", p, true) or (#text + 1)
      local l = string.sub(text, p, e - 1)
      if taskLine(l) and string.find(tl.plainText(l), probe, 1, true) then st, en, line = p, e, l; break end
      p = e + 1
    end
  end
  if not st then
    editor.flashNotification("Could not find that task on " .. page, "error")
    return false
  end
  local pre, post = string.match(line, "^(%s*[-*] %[)[^%]]*(%].*)$")
  tl.write(page, string.sub(text, 1, st - 1) .. pre .. state .. post .. string.sub(text, en))
  return true
end

-- Show Focus row `row` in `state`: its icon, the attributes the filter uses,
-- and struck-through text once closed. The row stays in its section until
-- the next render.
local function markRow(row, state)
  row.querySelector(".tl-icon").setAttribute("data-tl-state", shownState(state))
  row.setAttribute("data-cat", tl.categoryOf(state))
  row.setAttribute("data-state", state)
  if tl.isClosedState(state) then row.classList.add("tl-row-closed") else row.classList.remove("tl-row-closed") end
end

-- A click on a Focus row's icon: pick a state, write it, and update the row
-- in place.
function tl.pickRowState(el)
  local row = el.closest(".tl-row")
  if not row then return end
  local page = row.getAttribute("data-page")
  local choice = pickState("State: " .. row.getAttribute("data-title"))
  if not choice then return end
  local ok
  if row.getAttribute("data-source") == "1" then
    tl.setTaskPageState(page, choice.state)
    ok = true
  else
    ok = tl.setTaskStateAt(page, tonumber(row.getAttribute("data-pos")), row.getAttribute("data-title"), choice.state)
  end
  if ok then
    markRow(row, choice.state)
    tl.refreshStates()
  end
end

-- A filter is a table { project =, state =, when =, tag =, source = }. It is
-- stored, and kept in the widget's data-defaults, as "key=value" lines.
local filterKeys = { "project", "state", "when", "tag", "source" }

local function encodeFilter(f)
  local parts = {}
  for _, k in ipairs(filterKeys) do table.insert(parts, k .. "=" .. (f[k] or "")) end
  return table.concat(parts, "\n")
end

local function decodeFilter(s)
  local f = {}
  for k, v in string.gmatch(s or "", "([%w]+)=([^\n]*)") do
    if v ~= "" then f[k] = v end
  end
  return f
end

-- whether a Focus row passes filter `f`
local function rowMatches(row, f)
  if f.project and f.project ~= "" then
    local p = row.getAttribute("data-project") or ""
    if f.project == "none" then
      if p ~= "" then return false end
    elseif p ~= f.project then return false end
  end
  if f.state and f.state ~= "" then
    local kind, v = string.match(f.state, "^(%a):(.*)$")
    if kind == "c" and row.getAttribute("data-cat") ~= v then return false end
    if kind == "s" and row.getAttribute("data-state") ~= v then return false end
  end
  if f.when and f.when ~= "" then
    local w = " " .. (row.getAttribute("data-when") or "") .. " "
    if not string.find(w, " " .. f.when .. " ", 1, true) then return false end
  end
  if f.tag and f.tag ~= "" then
    local tags = " " .. (row.getAttribute("data-tags") or "") .. " "
    if not string.find(tags, " " .. f.tag .. " ", 1, true) then return false end
  end
  if f.source and f.source ~= "" then
    if f.source == "task-pages" then
      if row.getAttribute("data-taskpage") ~= "1" then return false end
    elseif f.source == "other-pages" then
      if row.getAttribute("data-taskpage") == "1" then return false end
    else
      local folder = row.getAttribute("data-folder") or ""
      if f.source == "/" then
        if folder ~= "" then return false end
      elseif folder ~= f.source then return false end
    end
  end
  return true
end

-- Read the filter bar of Focus list `root`, hide the rows and sections that
-- do not match, and update the counts. `remember` saves the filter for this
-- page in this browser.
function tl.applyFocusFilter(root, remember)
  local f = {}
  local selects = root.querySelectorAll(".tl-filter")
  for i = 0, selects.length - 1 do
    local s = selects.item(i)
    local v = s.value
    if v ~= "" then f[s.getAttribute("data-key")] = v end
    if v ~= "" then s.classList.add("tl-filter-on") else s.classList.remove("tl-filter-on") end
  end
  local shown = 0
  local secs = root.querySelectorAll(".tl-fsection")
  for i = 0, secs.length - 1 do
    local sec = secs.item(i)
    local rows = sec.querySelectorAll(".tl-row")
    local n = 0
    for j = 0, rows.length - 1 do
      local r = rows.item(j)
      if rowMatches(r, f) then r.classList.remove("tl-hide"); n = n + 1 else r.classList.add("tl-hide") end
    end
    sec.querySelector(".tl-count").textContent = tostring(n)
    if n == 0 then sec.classList.add("tl-hide") else sec.classList.remove("tl-hide") end
    shown = shown + n
  end
  local count = root.querySelector(".tl-ptoolbar-count")
  if count then count.textContent = tostring(shown) end
  local empty = root.querySelector(".tl-focus-empty")
  if empty then
    if shown == 0 then empty.classList.remove("tl-hide") else empty.classList.add("tl-hide") end
  end
  if remember then
    storeSet("throughline.focus:" .. root.getAttribute("data-key"), encodeFilter(f))
  end
end

-- the Reset button: back to the placement's starting filter, forgetting the
-- remembered one
function tl.resetFocusFilter(el)
  local root = el.closest(".tl-focus")
  local defaults = decodeFilter(root.getAttribute("data-defaults"))
  local selects = root.querySelectorAll(".tl-filter")
  for i = 0, selects.length - 1 do
    local s = selects.item(i)
    s.value = defaults[s.getAttribute("data-key")] or ""
  end
  storeSet("throughline.focus:" .. root.getAttribute("data-key"), nil)
  tl.applyFocusFilter(root, false)
end

-- Throughline: Filter Focus, the filter bar from the keyboard. Pick a Focus
-- list on screen, a filter, then one of that dropdown's own options; repeat
-- until Escape. The values and the remembered filter are the widget's own.
local FILTER_NAMES = { project = "Project", state = "State", when = "When", tag = "Tag", source = "Pages" }

local function focusRoot(key)
  local roots = js.window.document.querySelectorAll("#sb-main .tl-focus")
  for i = 0, roots.length - 1 do
    local r = roots.item(i)
    if r.getAttribute("data-key") == key then return r end
  end
end

function tl.filterFocus()
  local roots = js.window.document.querySelectorAll("#sb-main .tl-focus")
  if roots.length == 0 then
    editor.flashNotification("No Focus list on screen: scroll it into view first", "error")
    return
  end
  local key = roots.item(0).getAttribute("data-key")
  if roots.length > 1 then
    local rows = {}
    for i = 0, roots.length - 1 do
      local k = roots.item(i).getAttribute("data-key")
      table.insert(rows, { name = "Focus list " .. (i + 1), description = k, key = k })
    end
    local c = pick("Which Focus list?", rows)
    if not c then return end
    key = c.key
  end
  while true do
    -- the widget may have redrawn since the last round
    local root = focusRoot(key)
    if not root then return end
    local rows = {}
    local selects = root.querySelectorAll(".tl-filter")
    for i = 0, selects.length - 1 do
      local s = selects.item(i)
      local k = s.getAttribute("data-key")
      table.insert(rows, { name = FILTER_NAMES[k] or k, description = s.options.item(s.selectedIndex).textContent, key = k })
    end
    table.insert(rows, { name = "Reset", description = "back to this list's starting filter", key = "" })
    local f = pick("Filter Focus by (Escape when done)", rows)
    if not f then return end
    if f.key == "" then
      tl.resetFocusFilter(root)
    else
      local s = root.querySelector('.tl-filter[data-key="' .. f.key .. '"]')
      local opts = {}
      for i = 0, s.options.length - 1 do
        local o = s.options.item(i)
        local group = o.parentElement and o.parentElement.tagName == "OPTGROUP" and o.parentElement.getAttribute("label") or nil
        table.insert(opts, {
          name = o.textContent,
          description = (i == s.selectedIndex) and "current" or group,
          value = o.value,
        })
      end
      local v = pick(f.name, opts)
      if v then
        s.value = v.value
        tl.applyFocusFilter(root, true)
      end
    end
  end
end

command.define { name = "Throughline: Filter Focus", run = function() throughline.filterFocus() end }

-- One filter dropdown. `options` holds { value, label } entries or
-- { group, options } groups; `value` is the current choice.
local function filterSelect(key, allLabel, options, value)
  local opts = { dom.option { value = "", allLabel } }
  for _, o in ipairs(options) do
    if o.group then
      local inner = {}
      for _, g in ipairs(o.options) do
        local x = { value = g.value, g.label }
        if g.value == value then x.selected = "selected" end
        table.insert(inner, dom.option(x))
      end
      table.insert(opts, dom.optgroup { label = o.group, table.unpack(inner) })
    else
      local x = { value = o.value, o.label }
      if o.value == value then x.selected = "selected" end
      table.insert(opts, dom.option(x))
    end
  end
  return dom.select {
    class = value and value ~= "" and "tl-filter tl-filter-on" or "tl-filter",
    ["data-key"] = key,
    onchange = function(e) tl.applyFocusFilter(e.target.closest(".tl-focus"), true) end,
    table.unpack(opts),
  }
end

-- The project a Focus row belongs to: the first project the task links to,
-- else the project page it sits on, else (for a subtask on a task page) the
-- project its task page's task links to. `projects` is a set of page names.
local function focusProjectOf(t, projects, sourceOf)
  for _, l in ipairs(t.links or {}) do
    if projects[l] then return l end
  end
  if projects[t.page] then return t.page end
  local src = sourceOf[t.page]
  if src and src ~= t then
    for _, l in ipairs(src.links or {}) do
      if projects[l] then return l end
    end
  end
end

-- One Focus row. The data- attributes carry everything the filter bar
-- matches on, so filtering never needs the index again.
local function focusRow(t, now, ends, folder, sourceOf)
  local isSource = sourceOf[t.page] == t or (sourceOf[t.page] and sourceOf[t.page].ref == t.ref)
  local title = t._title
  local meta = {}
  if t._project then
    table.insert(meta, dom.span { class = "tl-chip tl-pchip", title = t._project, dom.span { class = "tl-pdot" }, basename(t._project) })
  end
  -- a task page's own task needs no "where"; any other task names its page
  if not isSource then
    table.insert(meta, dom.span { class = "tl-chip tl-src", title = "on " .. t.page, t.page })
  end
  for _, c in ipairs(dateChips(t, now)) do table.insert(meta, c) end
  local blocked = blockedChip(t.blockedBy)
  if blocked then table.insert(meta, blocked) end
  local page, pos, ref = t.page, t.pos, t.ref
  return dom.div {
    class = "tl-row",
    ["data-page"] = page,
    ["data-pos"] = tostring(pos),
    ["data-title"] = title,
    ["data-source"] = isSource and "1" or "0",
    ["data-taskpage"] = startsWith(page, folder) and "1" or "0",
    ["data-project"] = t._project or "",
    ["data-cat"] = tl.categoryOf(t.state),
    ["data-state"] = t.state,
    ["data-when"] = whenTokens(t, now, ends),
    ["data-tags"] = table.concat(t.tags or {}, " "),
    ["data-folder"] = folderOf(page),
    dom.span {
      class = "tl-icon",
      ["data-tl-state"] = shownState(t.state),
      title = tl.labelOf(t.state) .. ". Click to change",
      onclick = function(e) e.stopPropagation(); tl.pickRowState(e.target) end,
    },
    dom.span {
      class = "tl-row-title",
      -- a task page opens at the top; any other task at its line
      onclick = function()
        if isSource then editor.navigate(page) else editor.navigate(ref) end
      end,
      title,
    },
    dom.span { class = "tl-row-meta", table.unpack(meta) },
  }
end

-- A Focus section: a <details>, open unless the section is folded by default.
-- Empty sections are rendered but hidden, so a filter change can show them.
local function focusSectionNode(s, rows)
  local head = dom.div {
    class = "tl-fsection-head",
    dom.span { class = "tl-fchev", "▸" },
    dom.span { class = "tl-fsection-title", s.label },
    dom.span { class = "tl-count", tostring(#rows) },
  }
  local cls = "tl-fsection"
  if #rows == 0 then cls = cls .. " tl-hide" end
  local attrs = { class = cls, ["data-section"] = s.key }
  if not s.folded then attrs.open = "open" end
  table.insert(attrs, dom.summary { class = "tl-fsummary", head })
  table.insert(attrs, dom.div { class = "tl-rows", table.unpack(rows) })
  return dom.details(attrs)
end

local function sortedKeys(set)
  local out = {}
  for k in pairs(set) do table.insert(out, k) end
  table.sort(out)
  return out
end

-- The filter bar. Its choices are built from what the list actually contains
-- (projects, tags and folders in use), plus the configured open states.
-- `used` holds sets of projects, tags and folders; `current` the filter.
local function focusFilterBar(used, defaults, current)
  local projectOpts = {}
  local pnames = sortedKeys(used.projects)
  -- a default project with no open tasks still needs to be selectable
  if defaults.project and not used.projects[defaults.project] and defaults.project ~= "none" then
    table.insert(pnames, defaults.project)
    table.sort(pnames)
  end
  for _, name in ipairs(pnames) do table.insert(projectOpts, { value = name, label = basename(name) }) end
  table.insert(projectOpts, { value = "none", label = "No project" })

  -- states and categories share one dropdown: values are "s:DOING" or "c:held"
  local stateOpts, catOpts, seenCat = {}, {}, {}
  for _, st in ipairs(tl.states()) do
    if not tl.isClosedState(st.state) then
      table.insert(stateOpts, { value = "s:" .. st.state, label = st.label })
      local c = tl.categoryOf(st.state)
      if not seenCat[c] then seenCat[c] = true; table.insert(catOpts, { value = "c:" .. c, label = categoryLabels[c] or c }) end
    end
  end

  local whenOpts = {
    { value = "overdue", label = "Overdue" },
    { value = "today", label = "Today" },
    { value = "week", label = "Next 7 days" },
    { value = "month", label = "Next 30 days" },
    { value = "undated", label = "No date" },
  }

  local tagOpts = {}
  for _, tag in ipairs(sortedKeys(used.tags)) do table.insert(tagOpts, { value = tag, label = "#" .. tag }) end

  -- where a task lives: task pages or not, or a top-level folder ("/" is the
  -- top level itself)
  local folderOpts = {}
  for _, f in ipairs(sortedKeys(used.folders)) do
    table.insert(folderOpts, { value = f == "" and "/" or f, label = f == "" and "Top level" or (f .. "/") })
  end
  local sourceGroups = {
    { group = "Kind", options = {
      { value = "task-pages", label = "Task pages" },
      { value = "other-pages", label = "Other pages" },
    } },
    { group = "Folder", options = folderOpts },
  }

  return dom.div {
    class = "tl-filterbar",
    filterSelect("project", "All projects", projectOpts, current.project),
    filterSelect("state", "All states", { { group = "State", options = stateOpts }, { group = "Category", options = catOpts } }, current.state),
    filterSelect("when", "Any time", whenOpts, current.when),
    filterSelect("tag", "All tags", tagOpts, current.tag),
    filterSelect("source", "All pages", sourceGroups, current.source),
    dom.button { class = "tl-button tl-ghost tl-reset", onclick = function(e) tl.resetFocusFilter(e.target) end, "Reset" },
  }
end

-- ${throughline.focus()}, or with a starting filter for this placement:
-- ${throughline.focus { project = "Projects/Website", when = "week" }}
-- Keys: project (a page, "this" for the page it is on, or "none"), state (a
-- state like "DOING"), category (e.g. "held"), when (overdue, today, week,
-- month, undated), tag, source (a top-level folder, "/", "task-pages" or
-- "other-pages"), and id, to tell apart two lists on one page. The filter
-- bar starts from these, or from what it was last set to in this browser.
function tl.focus(opts)
  opts = opts or {}
  local now = today()
  local horizon = addDays(now, tl.upcomingDays())
  local host = editor.getCurrentPage()
  local folder = tl.taskFolder()
  local tasks, sourceOf = focusTasks()
  local projects = {}
  for _, p in ipairs(tl.projectList()) do projects[p.name] = true end

  -- the starting filter, in the filter bar's own encoding
  local defaults = {}
  if opts.project then defaults.project = opts.project == "this" and host or opts.project end
  if opts.state then defaults.state = "s:" .. opts.state end
  if opts.category then defaults.state = "c:" .. opts.category end
  if opts.when then defaults.when = opts.when end
  if opts.tag then defaults.tag = opts.tag end
  if opts.source then defaults.source = opts.source end
  local key = host .. "#" .. (opts.id or "")
  local remembered = storeGet("throughline.focus:" .. key)
  local current = remembered and decodeFilter(remembered) or defaults

  -- sort every task into its section, and note what the filter bar can offer
  local bySection = {}
  for _, s in ipairs(focusSections) do bySection[s.key] = {} end
  local used = { projects = {}, tags = {}, folders = {} }
  for _, t in ipairs(tasks) do
    t._project = focusProjectOf(t, projects, sourceOf)
    t._date = earliest(t.due and tostring(t.due) or nil, t.scheduled and tostring(t.scheduled) or nil)
    -- sort keys, worked out once rather than in every comparison
    t._title = tl.plainText(t.name)
    t._rank = tl.categoryOf(t.state) == "active" and 0 or 1
    table.insert(bySection[focusSection(t, now, horizon)], t)
    if t._project then used.projects[t._project] = true end
    for _, tag in ipairs(t.tags or {}) do used.tags[tag] = true end
    used.folders[folderOf(t.page)] = true
  end

  -- within a section: started work first, then by date, then by name
  local ends = { week = addDays(now, 7), month = addDays(now, 30) }
  local nodes, total = {}, 0
  for _, s in ipairs(focusSections) do
    local list = bySection[s.key]
    table.sort(list, function(a, b)
      if a._rank ~= b._rank then return a._rank < b._rank end
      local da, db = a._date or "9999", b._date or "9999"
      if da ~= db then return da < db end
      return a._title < b._title
    end)
    local rows = {}
    for _, t in ipairs(list) do table.insert(rows, focusRow(t, now, ends, folder, sourceOf)) end
    total = total + #rows
    table.insert(nodes, focusSectionNode(s, rows))
  end

  return widget.html(dom.div {
    class = "tl-focus",
    ["data-key"] = key,
    ["data-defaults"] = encodeFilter(defaults),
    dom.div {
      class = "tl-ftoolbar",
      dom.span { class = "tl-ptoolbar-title", "Focus" },
      dom.span { class = "tl-ptoolbar-count", tostring(total) },
    },
    focusFilterBar(used, defaults, current),
    dom.div { class = "tl-focus-empty tl-hide", "Nothing matches. Clear a filter, or enjoy the quiet." },
    table.unpack(nodes),
  })
end

-- Widgets are built before they are attached, so the starting filter is
-- applied once the list is on the page: by the editor watcher as soon as it
-- appears (see Background tick), else by the next tick.
function tl.applyPendingFilters()
  local roots = js.window.document.querySelectorAll(".tl-focus:not([data-filtered])")
  for i = 0, roots.length - 1 do
    local r = roots.item(i)
    r.setAttribute("data-filtered", "1")
    tl.applyFocusFilter(r, false)
  end
end

---------------------------------------------------------------------------
-- Projections
--
-- A projection is an ordinary link to a task page, `- [[Tasks/x|alias]]`.
-- SilverBullet draws it as a link; Throughline adds data-tl-state and
-- data-tl-due attributes to every such link in the editor, and the
-- stylesheet draws the state's icon in front of it and the due date after
-- it. Pressing the icon or the date opens a panel for editing the task.
---------------------------------------------------------------------------

-- The state of task page `page`, or nil if it is not one. Cached in
-- tl.stateMap, which the background tick clears every few seconds (the
-- page:index event does not reach client-side Space Lua) and every write
-- clears at once.
function tl.stateOf(page)
  if not tl.stateMap then
    local m, due, title = {}, {}, {}
    for _, t in ipairs(tl.sources(nil)) do
      m[t.page] = t.state
      due[t.page] = t.due and tostring(t.due) or false
      title[t.page] = tl.plainText(t.name)
    end
    -- task pages written moments ago, which the index does not know yet
    for p, w in pairs(tl.pending) do
      if m[p] == nil and clock() - w.at <= 20 then m[p] = w.state end
    end
    -- due dates set moments ago, likewise
    for p, w in pairs(tl.pendingDue) do
      if clock() - w.at > 20 or due[p] == w.due then tl.pendingDue[p] = nil else due[p] = w.due end
    end
    tl.stateMap, tl.dueMap, tl.titleMap = m, due, title
  end
  return tl.stateMap[page]
end

-- The task text of task page `page`, from the same cache; the page name
-- when it is not known (yet).
function tl.titleOf(page)
  if not tl.stateMap then tl.stateOf(page) end
  return (tl.titleMap and tl.titleMap[page]) or basename(page)
end

-- The due date of task page `page`, or false; from the same cache.
function tl.dueOf(page)
  if not tl.stateMap then tl.stateOf(page) end
  return tl.dueMap and tl.dueMap[page]
end

-- Record that Throughline just gave task page `page` the state `state`.
function tl.noteState(page, state)
  tl.pending[page] = state and { state = state, at = clock() } or nil
  if tl.stateMap then tl.stateMap[page] = state end
end

-- Mark every link to a task page in the editor with its state.
function tl.markLinks()
  local links = js.window.document.querySelectorAll("#sb-main a.sb-wiki-link")
  local now = today()
  for i = 0, links.length - 1 do
    local a = links.item(i)
    local page = a.getAttribute("href") or ""
    local st = tl.stateOf(page)
    if st then
      local shown = shownState(st)
      if a.getAttribute("data-tl-state") ~= shown then a.setAttribute("data-tl-state", shown) end
      -- the due date, drawn after the link by the stylesheet; red once past
      local due = tl.dueOf(page)
      local label = due and shortDate(due) or nil
      if a.getAttribute("data-tl-due") ~= label then
        if label then a.setAttribute("data-tl-due", label) else a.removeAttribute("data-tl-due") end
      end
      local late = (due and not tl.isClosedState(st) and due < now) and "1" or nil
      if a.getAttribute("data-tl-late") ~= late then
        if late then a.setAttribute("data-tl-late", late) else a.removeAttribute("data-tl-late") end
      end
    end
  end
end

-- Bring board cards and Focus rows on screen in line with the current task
-- states, for changes made outside them: a projection's picker, a Focus row,
-- editing the task page, or another device.
function tl.syncWidgets()
  local doc = js.window.document
  local cards = doc.querySelectorAll(".tl-card[data-state]")
  for i = 0, cards.length - 1 do
    local c = cards.item(i)
    local st = tl.stateOf(c.getAttribute("data-page"))
    if st and st ~= c.getAttribute("data-state") then placeCard(c, st) end
  end
  local rows = doc.querySelectorAll('.tl-row[data-source="1"]')
  for i = 0, rows.length - 1 do
    local r = rows.item(i)
    local st = tl.stateOf(r.getAttribute("data-page"))
    if st and st ~= r.getAttribute("data-state") then markRow(r, st) end
  end
end

-- Redraw everything that shows task states, after Throughline changed one.
function tl.refreshStates()
  pcall(tl.markLinks)
  pcall(tl.syncWidgets)
end

-- The popover a projection's icon opens: the task's state as a row of icons,
-- its dates and progress (attrForm), and Delete. It is plain DOM appended to
-- <body>, outside the editor, placed under the link. Every change writes at
-- once; Escape, Done, scrolling or a click outside closes it.
function tl.closePopover()
  if tl.popover then
    tl.popover.remove()
    tl.popover = nil
  end
end

function tl.openTaskPopover(page, anchor)
  tl.closePopover()
  local current = tl.stateOf(page)
  local buttons = {}
  local function mark(state)
    for _, b in ipairs(buttons) do
      if b.getAttribute("data-state") == state then b.classList.add("tl-on") else b.classList.remove("tl-on") end
    end
  end
  for _, st in ipairs(tl.states()) do
    local state = st.state
    table.insert(buttons, dom.button {
      class = state == current and "tl-pop-state tl-on" or "tl-pop-state",
      title = st.label,
      ["data-state"] = state,
      onclick = function()
        tl.setTaskPageState(page, state)
        mark(state)
        tl.refreshStates()
      end,
      dom.span { class = "tl-icon", ["data-tl-state"] = shownState(state) },
      st.label,
    })
  end
  local subs = subtasksByPage()[page]
  local pop = dom.div {
    class = "tl-pop",
    dom.div {
      class = "tl-pop-head",
      dom.a {
        class = "tl-pop-title",
        href = "/" .. page,
        onclick = function(e) e.preventDefault(); tl.closePopover(); editor.navigate(page) end,
        tl.titleOf(page),
      },
    },
    dom.div { class = "tl-pop-states", table.unpack(buttons) },
    attrForm(page, tl.taskAttrs(page), subs, function()
      tl.refreshCard(page)
      tl.refreshStates()
    end),
    dom.div {
      class = "tl-pop-foot",
      dom.button {
        class = "tl-button tl-ghost tl-delete",
        onclick = function() tl.closePopover(); tl.deleteTaskPage(page) end,
        "Delete task page",
      },
      dom.span { class = "tl-spacer" },
      dom.button { class = "tl-button", onclick = function() tl.closePopover() end, "Done" },
    },
  }
  -- under the link, kept inside the window
  local w = js.window
  local r = anchor.getBoundingClientRect()
  local left = math.max(8, math.min(r.left, w.innerWidth - 348))
  local top = r.bottom + 6
  if top + 330 > w.innerHeight then top = math.max(8, r.top - 336) end
  pop.style.left = left .. "px"
  pop.style.top = top .. "px"
  w.document.body.appendChild(pop)
  tl.popover = pop
end

-- The projection whose icon (the first ~1em of the link) or due date (drawn
-- after it) is under the pointer of event `e`, or nil. A long link wraps, as
-- on a task page's first line, so the icon is measured on the link's first
-- line box and the date on its last.
local function projectionHit(e)
  local a = e.target.closest and e.target.closest("a.sb-wiki-link")
  if not a or not a.getAttribute("data-tl-state") then return nil end
  local rs = a.getClientRects()
  if rs.length == 0 then return nil end
  local first, last = rs.item(0), rs.item(rs.length - 1)
  local onIcon = e.clientY >= first.top and e.clientY <= first.bottom
    and e.clientX - first.left <= first.height * 1.1
  local onDue = a.getAttribute("data-tl-due") and e.clientY >= last.top and e.clientY <= last.bottom
    and e.clientX > last.right - 6 * last.height
  if onIcon or onDue then return a end
end

-- Pressing the mouse on a projection's icon or date opens the popover. It
-- acts on mousedown, before the editor does: once the editor has focus, a
-- press on a line moves the cursor there and SilverBullet swaps the link for
-- its raw markdown, so a click handler would never see the link. The click
-- that follows is swallowed, so the link does not navigate. A press outside
-- an open popover closes it.
function tl.onLinkPress(e)
  if tl.popover and not tl.picking and not (e.target.closest and e.target.closest(".tl-pop")) then tl.closePopover() end
  local a = projectionHit(e)
  if not a then return end
  e.preventDefault()
  e.stopPropagation()
  tl.swallowClick = true
  tl.openTaskPopover(a.getAttribute("href"), a)
end

function tl.onLinkClick(e)
  if tl.swallowClick then
    tl.swallowClick = false
    e.preventDefault()
    e.stopPropagation()
    return
  end
  -- a click on a task state in the editor text (not in a widget) only places
  -- the cursor (that happened on mousedown): SilverBullet would cycle the
  -- state, which gets in the way of editing it as text
  local st = e.target.closest and e.target.closest("#sb-main .cm-line [data-task-state]")
  if st and not st.closest('[contenteditable="false"]') then
    e.stopPropagation()
    return
  end
  -- a click without a press first, e.g. from the keyboard
  local a = projectionHit(e)
  if not a then return end
  e.preventDefault()
  e.stopPropagation()
  tl.openTaskPopover(a.getAttribute("href"), a)
end

-- One set of document listeners, registered once: Space Lua re-runs this
-- file on every config reload, so a marker on <html> guards it. Clicks are
-- caught in the capture phase, before SilverBullet follows the link.
local root = js.window.document.documentElement
if root.getAttribute("data-tl-click") ~= "3" then
  root.setAttribute("data-tl-click", "3")
  local doc = js.window.document
  doc.addEventListener("mousedown", function(e) throughline.onLinkPress(e) end, true)
  doc.addEventListener("click", function(e) throughline.onLinkClick(e) end, true)
  doc.addEventListener("keydown", function(e)
    if e.key == "Escape" and throughline.popover and not throughline.picking then throughline.closePopover() end
  end, true)
  doc.addEventListener("scroll", function(e)
    if throughline.popover and not throughline.picking and not (e.target.closest and e.target.closest(".tl-pop")) then throughline.closePopover() end
  end, true)
end

-- The editor watcher: whenever the editor adds or replaces elements (a page
-- opens, lines scroll into view, a widget draws), mark the new projection
-- links and filter new Focus lists in the next frame, instead of waiting for
-- the tick. Our own attribute changes add no elements, so they do not loop.
function tl.onEditorChange()
  if tl.markQueued then return end
  tl.markQueued = true
  js.window.requestAnimationFrame(function()
    tl.markQueued = false
    pcall(tl.markLinks)
    pcall(tl.applyPendingFilters)
  end)
end
local main = js.window.document.querySelector("#sb-main")
if main and root.getAttribute("data-tl-watch") ~= "1" then
  root.setAttribute("data-tl-watch", "1")
  local observer = js.new(js.window.MutationObserver, function() throughline.onEditorChange() end)
  observer.observe(main, js.tojs({ childList = true, subtree = true }))
end

-- The bar at the top of a task page: an Edit task button that opens the same
-- panel as a projection's icon. The task line itself stays plain text.
event.listen {
  name = "hooks:renderTopWidgets",
  run = function()
    local page = editor.getCurrentPage()
    if not startsWith(page, tl.taskFolder()) or not tl.stateOf(page) then return nil end
    return widget.html(dom.div {
      class = "tl-taskbar",
      dom.button {
        class = "tl-button",
        title = "Edit this task's state, dates, blocker and progress",
        onclick = function(e) tl.openTaskPopover(page, e.target) end,
        "Edit task",
      },
    })
  end,
}

-- On project pages the board replaces SilverBullet's Linked Tasks and Linked
-- Mentions panels: the stylesheet hides them under body.tl-project.
function tl.markProjectPage()
  local meta = editor.getCurrentPageMeta() or {}
  local body = js.window.document.body
  local isProject = contains(meta.tags, "project")
  if isProject ~= body.classList.contains("tl-project") then
    if isProject then body.classList.add("tl-project") else body.classList.remove("tl-project") end
  end
end

event.listen {
  name = "editor:pageLoaded",
  run = function()
    pcall(tl.markProjectPage)
    pcall(tl.markLinks)
  end,
}

-- The stylesheet keys every theme off one attribute on <html>.
function tl.applyTheme()
  local root = js.window.document.documentElement
  local theme = tl.theme()
  if root.getAttribute("data-tl-theme") ~= theme then root.setAttribute("data-tl-theme", theme) end
end
pcall(tl.applyTheme)

---------------------------------------------------------------------------
-- Background tick
--
-- Once a second: mark projection links (new ones appear as the user scrolls
-- and types), move board cards and Focus rows whose state changed elsewhere
-- (the state cache is rebuilt from the index every third tick), mark project
-- pages (on a fresh client a page's tags may not be
-- indexed yet when it loads), apply Focus filters to lists that just
-- rendered, and pick up a changed theme. Each step is cheap when nothing
-- changed, and a failure in one does not stop the others.
---------------------------------------------------------------------------

event.listen {
  name = "cron:secondPassed",
  run = function()
    tl.tick = (tl.tick or 0) + 1
    tl.stateCache = nil
    if tl.tick % 3 == 0 then tl.stateMap = nil end
    pcall(tl.markLinks)
    pcall(tl.syncWidgets)
    pcall(tl.markProjectPage)
    pcall(tl.applyPendingFilters)
    pcall(tl.applyTheme)
  end,
}

---------------------------------------------------------------------------
-- Task commands
--
-- Make task page (and Promote subtask, the same command) moves a task into a
-- page of its own and leaves a projection where it was. Delete task page
-- removes the page and every projection of it.
---------------------------------------------------------------------------

-- a free page name in the task folder for a task's text: "rerun-load-test",
-- "rerun-load-test-2", ...
function tl.slugFor(text)
  local s = string.lower(tl.plainText(text))
  s = string.gsub(s, "[^%w]+", "-")
  s = string.gsub(string.gsub(s, "^%-+", ""), "%-+$", "")
  if #s > 40 then s = string.gsub(string.sub(s, 1, 40), "%-[^%-]*$", "") end
  if s == "" then s = "task" end
  local candidate, n = s, 2
  while pageExists(tl.taskFolder() .. candidate) do
    candidate = s .. "-" .. n
    n = n + 1
  end
  return candidate
end

local function indentOf(line)
  return #(string.match(line, "^(%s*)") or "")
end

-- The task under the cursor and everything nested below it.
local function blockAt(text, cursor)
  local ls, pos = {}, 0
  for line in string.gmatch(text .. "\n", "([^\n]*)\n") do
    table.insert(ls, { text = line, from = pos, to = pos + #line })
    pos = pos + #line + 1
  end
  local at
  for i, l in ipairs(ls) do
    if cursor >= l.from and cursor <= l.to then at = i; break end
  end
  if not at or not string.match(ls[at].text, "^%s*[-*] %[[^%]]*%] ") then return nil end
  local indent = indentOf(ls[at].text)
  local last = at
  for i = at + 1, #ls do
    local l = ls[i].text
    if string.match(l, "^%s*$") or indentOf(l) <= indent then break end
    last = i
  end
  local block = {}
  for i = at, last do table.insert(block, string.sub(ls[i].text, indent + 1)) end
  -- the nearest project link above, for a task that inherits its project
  local inherited
  local need = indent
  local projectLink = projectLinkPattern()
  for i = at - 1, 1, -1 do
    local l = ls[i].text
    if not string.match(l, "^%s*$") and indentOf(l) < need then
      inherited = inherited or string.match(l, projectLink)
      need = indentOf(l)
      if need == 0 then break end
    end
  end
  return {
    from = ls[at].from,
    to = ls[last].to,
    indent = string.rep(" ", indent),
    lines = block,
    nested = indent > 0,
    inheritedProject = inherited,
  }
end

-- Move the task under the cursor, with its subtasks, to a new task page and
-- leave a projection in its place. On a nested task of a task page this is
-- promotion: the new page records `partOf` its parent.
function tl.makeTaskPage()
  local page = editor.getCurrentPage()
  local b = blockAt(editor.getText(), editor.getCursor())
  if not b then
    editor.flashNotification("Put the cursor on a task first", "error")
    return
  end
  local folder = tl.taskFolder()
  local first = b.lines[1]
  local alias = tl.plainText(string.gsub(first, "^[-*] %[[^%]]*%] ", ""))
  if trim(alias) == "" then
    editor.flashNotification("Give the task some text first", "error")
    return
  end
  -- the field starts empty: Enter takes the suggestion, typing replaces it
  local suggested = tl.slugFor(alias)
  local slug = editor.prompt("Task page name (Enter for " .. folder .. suggested .. ")", "")
  if slug == nil then return end
  slug = trim(slug)
  if slug == "" then slug = suggested end
  local target = folder .. slug
  if pageExists(target) then
    editor.flashNotification(target .. " already exists", "error")
    return
  end
  -- the source names its project explicitly: its own link, else the project
  -- page it came from, else the nearest project link above it, else the
  -- project of the task page it came from
  local projectLink = projectLinkPattern()
  local project = string.match(first, projectLink)
  if not project then
    if startsWith(page, tl.projectFolder()) then project = page
    else project = b.inheritedProject end
    if not project and startsWith(page, folder) then
      project = string.match(tl.read(page), projectLink)
    end
    if project then b.lines[1] = first .. " [[" .. project .. "]]" end
  end
  local body = TASK_PAGE_FRONTMATTER .. table.concat(b.lines, "\n") .. "\n"
  local promoted = b.nested and startsWith(page, folder)
  if promoted then body = body .. "\n[partOf: [[" .. page .. "]]]\n" end
  space.writePage(target, body)
  local projection = "- [[" .. target .. "|" .. alias .. "]]"
  editor.replaceRange(b.from, b.to, b.indent .. projection)
  if project and project ~= page and pageExists(project) then
    local ls = splitLines(tl.read(project))
    appendToList(ls, projection)
    tl.write(project, table.concat(ls, "\n") .. "\n")
  end
  tl.noteState(target, string.match(b.lines[1], "^[-*] %[([^%]]*)%]"))
  editor.flashNotification((promoted and "Promoted to " or "Created ") .. target)
end

-- the first link into the task folder on line `text`, or nil
local function taskLinkOnLine(text)
  return string.match(text or "", "%[%[(" .. escapePattern(tl.taskFolder()) .. "[^%]|]+)")
end

-- the task page a delete acts on: the open page if it is one, otherwise the
-- task page linked from the line under the cursor
local function taskPageAtCursor()
  local page = editor.getCurrentPage()
  if startsWith(page, tl.taskFolder()) then return page end
  local line = editor.getCurrentLine()
  return taskLinkOnLine(line and line.text)
end

-- Throughline: Open task. Open the task linked from the cursor line (a
-- projection, a blockedBy, ...) with the cursor inside its state brackets,
-- so the keyboard edits the task as text. Alt+Left comes back.
function tl.openTaskAtCursor()
  local line = editor.getCurrentLine()
  local target = taskLinkOnLine(line and line.text)
  if not target then
    editor.flashNotification("No task link on this line", "error")
    return
  end
  if not pageExists(target) then
    editor.flashNotification("No task page " .. target, "error")
    return
  end
  local s = taskLineIn(tl.read(target) or "")
  -- s is the "-" of "- [": two characters on is just inside the bracket
  editor.navigate(s and (target .. "@" .. (s + 2)) or target)
end

-- The subtasks of the task on task page text `text`: each task line nested
-- directly under it, with everything nested below that line, unindented.
local function subtaskBlocks(text)
  local ls = splitLines(text)
  local s
  for i, l in ipairs(ls) do
    if string.match(l, "^[-*] %[") then s = i; break end
  end
  if not s then return {} end
  local blocks, cur, childIndent = {}, nil, nil
  for i = s + 1, #ls do
    local l = ls[i]
    local ind = indentOf(l)
    if string.match(l, "^%s*$") or ind == 0 then break end
    childIndent = childIndent or ind
    if ind <= childIndent then
      childIndent = ind
      cur = nil
      if string.match(l, "^%s*[-*] %[[^%]]*%] ") then
        cur = { lines = {} }
        table.insert(blocks, cur)
      end
    end
    if cur then table.insert(cur.lines, string.sub(l, childIndent + 1)) end
  end
  for _, b in ipairs(blocks) do
    b.title = tl.plainText(string.gsub(b.lines[1], "^[-*] %[[^%]]*%] ", ""))
  end
  return blocks
end

-- Make each subtask block a task page of its own, linked to `project` and
-- listed on the project page, as Make task page would.
local function promoteSubtasks(blocks, project)
  local folder = tl.taskFolder()
  local projections = {}
  for _, b in ipairs(blocks) do
    local lines = { table.unpack(b.lines) }
    if project and not string.find(lines[1], "[[" .. project .. "]]", 1, true) then
      lines[1] = lines[1] .. " [[" .. project .. "]]"
    end
    local target = folder .. tl.slugFor(b.title)
    space.writePage(target, TASK_PAGE_FRONTMATTER .. table.concat(lines, "\n") .. "\n")
    tl.noteState(target, string.match(lines[1], "^[-*] %[([^%]]*)%]"))
    table.insert(projections, "- [[" .. target .. "|" .. b.title .. "]]")
  end
  if project and #projections > 0 and pageExists(project) then
    local ls = splitLines(tl.read(project))
    for _, pr in ipairs(projections) do appendToList(ls, pr) end
    tl.write(project, table.concat(ls, "\n") .. "\n")
  end
end

-- What to do with a task page's subtasks when it is deleted, asked in one
-- picker that also says which projections go: "keep" makes them task pages
-- of their own, "delete" deletes them too, nil cancels. The choice is then
-- confirmed once more, with the subtasks listed.
local function askAboutSubtasks(target, blocks, project, projections)
  local n = #blocks
  local name = tl.titleOf(target)
  local title = "Delete \"" .. name .. "\"? It has " .. n .. " subtask(s)"
  local choice = pick(title, {
    { name = "Delete it, and make its " .. n .. " subtask(s) tasks of their own", value = "keep" },
    { name = "Delete it and its " .. n .. " subtask(s)", value = "delete" },
  })
  if not choice then return nil end
  local list = {}
  for _, b in ipairs(blocks) do table.insert(list, "• " .. b.title) end
  local msg
  if choice.value == "keep" then
    msg = "Delete \"" .. name .. "\" and make these " .. n .. " subtask(s) tasks of their own" ..
      (project and (", in " .. basename(project)) or "") .. "?\n\n" .. table.concat(list, "\n")
  else
    msg = "Delete \"" .. name .. "\" and these " .. n .. " subtask(s) for good?\n\n" .. table.concat(list, "\n")
  end
  if projections ~= "" then msg = msg .. "\n\nThis also removes " .. projections end
  if not editor.confirm(msg, { destructive = true }) then return nil end
  return choice.value
end

-- Delete a task page and every projection of it, after confirmation. A
-- projection here is a list item that starts with a link to the page; other
-- links to it stay, as links to a missing page. When the task has subtasks,
-- the user chooses whether they become tasks of their own or go too.
function tl.deleteTaskPage(target)
  target = target or taskPageAtCursor()
  if not target or not pageExists(target) then
    editor.flashNotification("No task page to delete here", "error")
    return
  end
  local pattern = "\n%s*[-*] %[%[" .. escapePattern(target) .. "[|%]][^\n]*"
  local pages, count, seen = {}, 0, {}
  for _, l in ipairs(query[[from index.links()]]) do
    if l.toPage == target and not seen[l.page] then
      seen[l.page] = true
      local n = 0
      for _ in string.gmatch("\n" .. tl.read(l.page), pattern) do n = n + 1 end
      if n > 0 then
        table.insert(pages, { page = l.page, n = n })
        count = count + n
      end
    end
  end
  local where = {}
  for _, p in ipairs(pages) do table.insert(where, p.page .. " (" .. p.n .. ")") end
  local projections = count > 0 and (count .. " projection(s) on: " .. table.concat(where, ", ")) or ""
  -- with subtasks: one picker for what happens to them, then a confirmation;
  -- without: a single confirmation
  local pageText = tl.read(target) or ""
  local blocks = subtaskBlocks(pageText)
  local keep = false
  local project
  if #blocks > 0 then
    local s, e = taskLineIn(pageText)
    project = s and string.match(string.sub(pageText, s, e), projectLinkPattern()) or nil
    local what = askAboutSubtasks(target, blocks, project, projections)
    if not what then return end
    keep = what == "keep"
  else
    local msg = "Delete \"" .. tl.titleOf(target) .. "\"?"
    if projections ~= "" then msg = msg .. "\n\nThis also removes " .. projections end
    if not editor.confirm(msg, { destructive = true }) then return end
  end
  for _, p in ipairs(pages) do
    local text = string.gsub("\n" .. tl.read(p.page), pattern, "")
    tl.write(p.page, string.sub(text, 2))
  end
  if editor.getCurrentPage() == target then editor.navigate("index") end
  -- the deletion reaches the server with the next sync, not instantly
  local ok, err = pcall(space.deletePage, target)
  if not ok then
    editor.flashNotification("Could not delete " .. target .. ": " .. tostring(err), "error")
    return
  end
  tl.noteState(target, nil)
  if keep then promoteSubtasks(blocks, project) end
  editor.flashNotification("Deleted " .. target .. (keep and (", kept " .. #blocks .. " subtask(s) as tasks") or ""))
end

command.define { name = "Throughline: Make task page", run = function() throughline.makeTaskPage() end }
command.define { name = "Throughline: Promote subtask", run = function() throughline.makeTaskPage() end }
command.define { name = "Throughline: Delete task page", run = function() throughline.deleteTaskPage() end }

command.define { name = "Throughline: Open task", key = "Mod-. o", run = function() throughline.openTaskAtCursor() end }

-- /task, on any line: an empty line, "- ", "- [ ] text", "- [DOING] text" or
-- plain text. The line becomes a task (asking for its text when it has none)
-- and then gets its task page.
slashCommand.define {
  name = "task",
  description = "Make a task page from this line",
  run = function()
    local line = editor.getCurrentLine()
    local text = line and line.text or ""
    if taskLinkOnLine(text) and string.match(text, "^%s*[-*] %[%[") then
      editor.flashNotification("Already a task page", "error")
      return
    end
    local indent, rest = string.match(text, "^(%s*)(.-)%s*$")
    local state, body = string.match(rest, "^[-*] %[([^%]%[]*)%]%s*(.*)$")
    if not state then
      state = " "
      body = string.match(rest, "^[-*]%s+(.*)$") or ((rest == "-" or rest == "*") and "" or rest)
    end
    body = trim(body)
    if body == "" then
      body = editor.prompt("New task", "")
      if not body or trim(body) == "" then return end
      body = trim(body)
    end
    local task = indent .. "- [" .. state .. "] " .. body
    editor.replaceRange(line.from, line.to, task)
    editor.moveCursor(line.from + #task)
    throughline.makeTaskPage()
  end,
}

-- The snippets: /due, /scheduled, /progress and /blocked write the same
-- [key: value] text you could type, for the names and formats that are hard
-- to remember. They act on the task line under the cursor.

-- the cursor line if it is a task line, else nil after saying why
local function taskLineAtCursor()
  local line = editor.getCurrentLine()
  local text = line and line.text or ""
  if string.match(text, "^%s*[-*] %[%[") and taskLinkOnLine(text) then
    editor.flashNotification("This is a link to a task: open it first (Ctrl+. o)", "error")
    return nil
  end
  if not string.match(text, "^%s*[-*] %[[^%]%[]*%]") then
    editor.flashNotification("Put the cursor on a task line", "error")
    return nil
  end
  return line
end

-- Write [key: value] at the end of the task line, or over the one there.
-- With `keep`, a value already there stays, and the value ends up selected
-- so typing replaces it; otherwise the cursor goes after the attribute.
local function attrSnippet(key, value, keep)
  local line = taskLineAtCursor()
  if not line then return end
  local text = line.text
  local s, e = string.find(text, "%[" .. key .. ":%s*%[%[[^%]]*%]%]%]")
  if not s then s, e = string.find(text, "%[" .. key .. ":[^%]]*%]") end
  local from, to, piece
  if s then
    local old = string.match(string.sub(text, s, e), "^%[[^:]+:%s*(.-)%s*%]$")
    if keep and old and old ~= "" then value = old end
    from, to = line.from + s - 1, line.from + e
    piece = "[" .. key .. ": " .. value .. "]"
  else
    from, to = line.from + #(string.gsub(text, "%s+$", "")), line.to
    piece = " [" .. key .. ": " .. value .. "]"
  end
  editor.replaceRange(from, to, piece)
  local v = from + #piece - 1 - #value
  if keep then editor.setSelection(v, v + #value) else editor.moveCursor(from + #piece) end
end

slashCommand.define {
  name = "due",
  description = "Due date on this task: [due: today]",
  run = function() attrSnippet("due", today(), true) end,
}
slashCommand.define {
  name = "scheduled",
  description = "Scheduled date on this task: [scheduled: today]",
  run = function() attrSnippet("scheduled", today(), true) end,
}
slashCommand.define {
  name = "progress",
  description = "Progress on this task, 0 to 100: [progress: ]",
  run = function() attrSnippet("progress", "", true) end,
}
slashCommand.define {
  name = "blocked",
  description = "Blocked by another task, chosen by its title",
  run = function()
    if not taskLineAtCursor() then return end
    local page = editor.getCurrentPage()
    local choice = pick("Blocked by which task?", openTaskRows(page))
    if not choice then return end
    attrSnippet("blockedBy", "[[" .. choice.page .. "]]", false)
  end,
}
```

```space-style
/* priority: 10 */

/* How this stylesheet is laid out

   Tokens            colours and font as --tl-* variables, light and dark
   State icons       the task state icons, drawn in three places: the editor,
                     the widgets and projection links
   Project icons     Linear's project status shapes
   Widget chrome     chips, buttons, toolbars shared by all widgets
   Board, Projects overview, Focus list
   Task popover      the editing panel and its form
   Overflow          how long text is shortened or wrapped, everywhere
   Theme: native     overrides for the default theme

   Everything above "Theme: native" is the lineish theme. native keeps its
   layout and replaces colours, backgrounds and borders; it applies when
   <html> has data-tl-theme="native", which the Lua sets from the theme
   setting. */

/* ---- Tokens ------------------------------------------------------------- */
html {
  --tl-font: "Inter", "Inter Variable", -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  --tl-ink: #1b1c1f;
  --tl-ink-2: #3c3e45;
  --tl-muted: #6b6f78;
  --tl-faint: #a0a3ab;
  --tl-line: #e8e8eb;
  --tl-line-strong: #d7d8dd;
  --tl-surface: #ffffff;
  --tl-surface-2: #f8f8f9;
  --tl-hover: #f2f2f4;
  --tl-accent: #5e6ad2;
  --tl-amber: #e3a008;
  --tl-blue: #4b8de8;
  --tl-green: #46a876;
  --tl-orange: #f08c3c;
  --tl-red: #e5484d;
  --tl-violet: #5e6ad2;
  --tl-grey: #9ca0a8;
  --tl-shadow: 0 1px 1px rgba(16, 17, 20, 0.03), 0 2px 5px rgba(16, 17, 20, 0.05);
  --tl-shadow-lift: 0 2px 4px rgba(16, 17, 20, 0.06), 0 8px 24px rgba(16, 17, 20, 0.10);
  --tl-overdue-bg: rgba(229, 72, 77, 0.10);
  --tl-today-bg: rgba(227, 160, 8, 0.13);
}
html[data-theme="dark"] {
  --tl-ink: #e8e9ec;
  --tl-ink-2: #c8cad0;
  --tl-muted: #8c8f98;
  --tl-faint: #5f626b;
  --tl-line: #2a2b31;
  --tl-line-strong: #383a42;
  --tl-surface: #1d1e23;
  --tl-surface-2: #17181c;
  --tl-hover: #26272d;
  --tl-amber: #f0b429;
  --tl-blue: #6aa1ef;
  --tl-green: #4fbf87;
  --tl-orange: #f59e57;
  --tl-red: #f06a6e;
  --tl-violet: #7c86e6;
  --tl-grey: #6f737c;
  --tl-shadow: 0 1px 2px rgba(0, 0, 0, 0.35);
  --tl-shadow-lift: 0 4px 18px rgba(0, 0, 0, 0.5);
  --tl-overdue-bg: rgba(240, 106, 110, 0.14);
  --tl-today-bg: rgba(240, 180, 41, 0.14);
}

/* ---- State icons ---------------------------------------------------------
   Three places draw a state: SilverBullet's own task (editor and query
   results, [data-task-state]), Throughline's widgets (.tl-icon) and task
   projections (links with data-tl-state). The default custom states get
   icons; any other state keeps SilverBullet's text. */

/* SilverBullet's task: shrink the state word to a 1em box, hide brackets */
:is([data-task-state="DOING"], [data-task-state="WAITING"], [data-task-state="BLOCKED"],
    [data-task-state="CANCELLED"], [data-task-state="BACKLOG"]) {
  display: inline-block;
  position: relative;
  width: 1em;
  height: 1em;
  overflow: hidden;
  text-indent: 0; /* list lines carry a negative hanging indent */
  color: transparent !important;
  vertical-align: -0.12em;
}
:is([data-task-state="DOING"], [data-task-state="WAITING"], [data-task-state="BLOCKED"],
    [data-task-state="CANCELLED"], [data-task-state="BACKLOG"]) * {
  color: transparent !important; /* the editor nests a coloured span */
}
.sb-task-mark:has(+ :is([data-task-state="DOING"], [data-task-state="WAITING"], [data-task-state="BLOCKED"], [data-task-state="CANCELLED"], [data-task-state="BACKLOG"])),
:is([data-task-state="DOING"], [data-task-state="WAITING"], [data-task-state="BLOCKED"], [data-task-state="CANCELLED"], [data-task-state="BACKLOG"]) + .sb-task-mark,
.sb-atom:has(+ :is([data-task-state="DOING"], [data-task-state="WAITING"], [data-task-state="BLOCKED"], [data-task-state="CANCELLED"], [data-task-state="BACKLOG"])),
:is([data-task-state="DOING"], [data-task-state="WAITING"], [data-task-state="BLOCKED"], [data-task-state="CANCELLED"], [data-task-state="BACKLOG"]) + .sb-atom {
  display: none;
}

/* the icon box, in all three places */
:is([data-task-state="DOING"], [data-task-state="WAITING"], [data-task-state="BLOCKED"],
    [data-task-state="CANCELLED"], [data-task-state="BACKLOG"])::before,
.tl-icon,
#sb-main a.sb-wiki-link[data-tl-state]::before {
  content: "";
  box-sizing: border-box;
  border-radius: 50%;
}
:is([data-task-state="DOING"], [data-task-state="WAITING"], [data-task-state="BLOCKED"],
    [data-task-state="CANCELLED"], [data-task-state="BACKLOG"])::before {
  position: absolute;
  inset: 0.06em;
}
.tl-icon {
  display: inline-block;
  flex: none;
  position: relative;
  width: 1.05em;
  height: 1.05em;
}
#sb-main a.sb-wiki-link[data-tl-state]::before {
  display: inline-block;
  width: 0.95em;
  height: 0.95em;
  margin-right: 0.35em;
  vertical-align: -0.13em;
  cursor: pointer;
}

/* planned and done: only widgets and projections need these; SilverBullet
   draws its own checkbox */
.tl-icon[data-tl-state="todo"],
#sb-main a.sb-wiki-link[data-tl-state="todo"]::before {
  border: 0.12em solid var(--tl-grey);
  border-radius: 0.24em;
}
.tl-icon[data-tl-state="done"],
#sb-main a.sb-wiki-link[data-tl-state="done"]::before {
  border-radius: 0;
  background: var(--tl-accent); /* a filled square with the tick cut out */
  -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Cmask id='m'%3E%3Crect width='16' height='16' rx='3.5' fill='white'/%3E%3Cpath d='M4 8.3l2.6 2.6L12 5.5' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/mask%3E%3Crect width='16' height='16' rx='3.5' mask='url(%23m)'/%3E%3C/svg%3E") center / contain no-repeat;
          mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Cmask id='m'%3E%3Crect width='16' height='16' rx='3.5' fill='white'/%3E%3Cpath d='M4 8.3l2.6 2.6L12 5.5' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/mask%3E%3Crect width='16' height='16' rx='3.5' mask='url(%23m)'/%3E%3C/svg%3E") center / contain no-repeat;
}

/* BACKLOG: a dashed circle */
[data-task-state="BACKLOG"]::before,
.tl-icon[data-tl-state="BACKLOG"],
#sb-main a.sb-wiki-link[data-tl-state="BACKLOG"]::before {
  border: 0.12em dashed var(--tl-grey);
}

/* DOING: a ring with a wedge filling clockwise from 12 o'clock */
[data-task-state="DOING"]::before,
.tl-icon[data-tl-state="DOING"],
#sb-main a.sb-wiki-link[data-tl-state="DOING"]::before {
  border: 0.11em solid var(--tl-amber);
  padding: 0.09em;
  background: conic-gradient(from 0deg, var(--tl-amber) 0 37.5%, transparent 37.5% 100%) content-box;
}

/* WAITING: a clock */
[data-task-state="WAITING"]::before,
.tl-icon[data-tl-state="WAITING"],
#sb-main a.sb-wiki-link[data-tl-state="WAITING"]::before {
  border-radius: 0;
  background: var(--tl-blue);
  -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Ccircle cx='8' cy='8' r='6.4' fill='none' stroke='black' stroke-width='1.7'/%3E%3Cpath d='M8 4.2V8l2.7 1.7' fill='none' stroke='black' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") center / contain no-repeat;
          mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Ccircle cx='8' cy='8' r='6.4' fill='none' stroke='black' stroke-width='1.7'/%3E%3Cpath d='M8 4.2V8l2.7 1.7' fill='none' stroke='black' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") center / contain no-repeat;
}
[data-task-state="WAITING"]::before { inset: 0; }

/* BLOCKED: a traffic cone */
[data-task-state="BLOCKED"]::before,
.tl-icon[data-tl-state="BLOCKED"],
#sb-main a.sb-wiki-link[data-tl-state="BLOCKED"]::before {
  border-radius: 0;
  background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Cpath d='M6.6 1.4h2.8l3.1 11.6h-9z' fill='%23f76707'/%3E%3Cpath d='M5.59 5h4.82l.52 2H5.07zM4.54 9h6.92l.52 2H4.02z' fill='%23fff'/%3E%3Crect x='1.6' y='12.9' width='12.8' height='2.1' rx='.7' fill='%23d9480f'/%3E%3C/svg%3E") center / contain no-repeat;
}
[data-task-state="BLOCKED"]::before { inset: 0; }

/* CANCELLED: a no-parking sign, thick ring with a 40 degree slash */
[data-task-state="CANCELLED"]::before,
.tl-icon[data-tl-state="CANCELLED"],
#sb-main a.sb-wiki-link[data-tl-state="CANCELLED"]::before {
  border-radius: 0;
  background: var(--tl-muted);
  -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Ccircle cx='8' cy='8' r='6.2' fill='none' stroke='black' stroke-width='2.4'/%3E%3Cline x1='3.25' y1='4.01' x2='12.75' y2='11.99' stroke='black' stroke-width='2.4'/%3E%3C/svg%3E") center / contain no-repeat;
          mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Ccircle cx='8' cy='8' r='6.2' fill='none' stroke='black' stroke-width='2.4'/%3E%3Cline x1='3.25' y1='4.01' x2='12.75' y2='11.99' stroke='black' stroke-width='2.4'/%3E%3C/svg%3E") center / contain no-repeat;
}
[data-task-state="CANCELLED"]::before { inset: 0; }

/* A state without an icon of its own: a projection shows its name as a small
   label; a widget shows a plain ring, since its row or card names it. */
#sb-main a.sb-wiki-link[data-tl-state]:not([data-tl-state="todo"], [data-tl-state="done"],
    [data-tl-state="DOING"], [data-tl-state="WAITING"], [data-tl-state="BLOCKED"],
    [data-tl-state="CANCELLED"], [data-tl-state="BACKLOG"])::before {
  content: attr(data-tl-state);
  width: auto;
  height: auto;
  text-indent: 0; /* list lines carry a negative hanging indent */
  white-space: nowrap;
  border-radius: 0.6em;
  padding: 0 0.4em;
  font-size: 0.62em;
  font-weight: 650;
  line-height: 1.55;
  vertical-align: 0.15em;
  color: #fff;
  background: var(--tl-muted);
}
.tl-icon:not([data-tl-state="todo"], [data-tl-state="done"], [data-tl-state="DOING"],
    [data-tl-state="WAITING"], [data-tl-state="BLOCKED"], [data-tl-state="CANCELLED"],
    [data-tl-state="BACKLOG"]) {
  border: 0.12em solid var(--tl-muted);
}

/* closed tasks: grey text (SilverBullet already strikes it) */
.cm-line:has([data-task-state="CANCELLED"]) .cm-task-checked { color: #8a8f98; }
#sb-main a.sb-wiki-link:is([data-tl-state="CANCELLED"], [data-tl-state="done"]) {
  text-decoration: line-through;
  opacity: 0.75;
}

/* Everything is plain text. On the line that holds the cursor (SilverBullet
   marks it with .sb-li-cursor), the state shows as its text again, brackets
   and all, so it can be edited like any other word. */
.cm-line:has(.sb-li-cursor) :is([data-task-state="DOING"], [data-task-state="WAITING"], [data-task-state="BLOCKED"],
    [data-task-state="CANCELLED"], [data-task-state="BACKLOG"]) {
  display: inline;
  width: auto;
  height: auto;
  overflow: visible;
  color: inherit !important;
}
.cm-line:has(.sb-li-cursor) :is([data-task-state="DOING"], [data-task-state="WAITING"], [data-task-state="BLOCKED"],
    [data-task-state="CANCELLED"], [data-task-state="BACKLOG"]) * {
  color: inherit !important;
}
.cm-line:has(.sb-li-cursor) :is([data-task-state="DOING"], [data-task-state="WAITING"], [data-task-state="BLOCKED"],
    [data-task-state="CANCELLED"], [data-task-state="BACKLOG"])::before {
  content: none;
}
.cm-line:has(.sb-li-cursor) .sb-atom { display: inline !important; }

/* SilverBullet's own state menu (the ▾ after a state) is not used, and a
   click on a state places the cursor instead of cycling it (tl.onLinkClick):
   type the state, or use the task page's Edit task button or the panel. */
.sb-task-dropdown { display: none !important; }
#sb-main .cm-line [data-task-state] { cursor: text; }

/* ---- Project status icons (Linear's shapes) ----------------------------- */
.tl-picon {
  display: inline-block;
  flex: none;
  box-sizing: border-box;
  width: 1em;
  height: 1em;
  border-radius: 50%;
  position: relative;
}
.tl-picon[data-cat="backlog"]   { border: 0.12em dashed var(--tl-grey); }
.tl-picon[data-cat="planned"]   { border: 0.12em solid var(--tl-grey); }
.tl-picon[data-cat="started"]   {
  border: 0.12em solid var(--tl-amber);
  padding: 0.1em;
  background: conic-gradient(var(--tl-amber) 0 50%, transparent 50% 100%) content-box;
}
.tl-picon[data-cat="paused"]    {
  border: 0.12em solid var(--tl-grey);
  background: linear-gradient(90deg, transparent 30%, var(--tl-grey) 30% 43%, transparent 43% 57%, var(--tl-grey) 57% 70%, transparent 70%) center / 100% 46% no-repeat;
}
.tl-picon[data-cat="completed"] {
  background: var(--tl-accent);
  -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Cmask id='m'%3E%3Ccircle cx='8' cy='8' r='8' fill='white'/%3E%3Cpath d='M4.6 8.2l2.3 2.3L11.4 6' fill='none' stroke='black' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/mask%3E%3Ccircle cx='8' cy='8' r='8' mask='url(%23m)'/%3E%3C/svg%3E") center / contain no-repeat;
          mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Cmask id='m'%3E%3Ccircle cx='8' cy='8' r='8' fill='white'/%3E%3Cpath d='M4.6 8.2l2.3 2.3L11.4 6' fill='none' stroke='black' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/mask%3E%3Ccircle cx='8' cy='8' r='8' mask='url(%23m)'/%3E%3C/svg%3E") center / contain no-repeat;
}
.tl-picon[data-cat="canceled"]  {
  background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Ccircle cx='8' cy='8' r='8' fill='%239ca0a8'/%3E%3Cpath d='M5.5 5.5l5 5M10.5 5.5l-5 5' stroke='white' stroke-width='1.8' stroke-linecap='round'/%3E%3C/svg%3E") center / contain no-repeat;
}

/* ---- Shared widget chrome ----------------------------------------------- */
:is(.tl-board, .tl-projects, .tl-focus) {
  font-family: var(--tl-font);
  font-size: 13px;
  line-height: 1.4;
  color: var(--tl-ink);
  -webkit-font-smoothing: antialiased;
}
:is(.tl-board, .tl-projects, .tl-focus) p { margin: 0; display: inline; }
:is(.tl-board, .tl-projects, .tl-focus) :is(button, select, option) { font-family: var(--tl-font) !important; }
.tl-count {
  color: var(--tl-muted);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}
.tl-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.3em;
  font-size: 12px;
  line-height: 18px;
  color: var(--tl-muted);
  border: 1px solid var(--tl-line);
  background: var(--tl-surface);
  border-radius: 999px;
  padding: 0 7px;
  white-space: nowrap;
}
.tl-overdue { color: var(--tl-red); border-color: transparent; background: var(--tl-overdue-bg); font-weight: 550; }
.tl-today { color: #a36c00; border-color: transparent; background: var(--tl-today-bg); font-weight: 550; }
html[data-theme="dark"] .tl-today { color: var(--tl-amber); }
.tl-button {
  font: inherit;
  font-size: 12px;
  font-weight: 500;
  color: var(--tl-ink-2);
  border: 1px solid var(--tl-line-strong);
  background: var(--tl-surface);
  border-radius: 6px;
  padding: 3px 10px;
  cursor: pointer;
  box-shadow: 0 1px 1px rgba(0, 0, 0, 0.03);
}
.tl-button:hover { background: var(--tl-hover); }
.tl-ghost { border-color: transparent; background: transparent; box-shadow: none; color: var(--tl-muted); }
.tl-ghost:hover { color: var(--tl-ink); }
.tl-delete { color: var(--tl-red); }
.tl-hide { display: none !important; }
.tl-spacer { flex: 1; }
.tl-actions { display: flex; gap: 6px; margin-top: 10px; }

/* toolbars above the overview and the Focus list */
:is(.tl-ptoolbar, .tl-ftoolbar) {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 2px 2px 10px;
}
.tl-ptoolbar-title { font-size: 14px; font-weight: 600; letter-spacing: -0.01em; }
.tl-ptoolbar-count {
  font-size: 12px;
  color: var(--tl-muted);
  background: var(--tl-hover);
  border-radius: 999px;
  padding: 0 7px;
  font-variant-numeric: tabular-nums;
}

/* ---- Board -------------------------------------------------------------- */
.tl-board {
  /* break out of the text column: the board wants width, prose does not */
  width: min(96vw, 1200px);
  position: relative;
  left: 50%;
  transform: translateX(-50%);
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(13em, 1fr);
  gap: 10px;
  overflow-x: auto;
  padding: 2px 0 10px;
}
.tl-col {
  background: var(--tl-surface-2);
  border: 1px solid var(--tl-line);
  border-radius: 10px;
  padding: 8px;
  min-height: 6em;
}
.tl-col-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 550;
  color: var(--tl-ink-2);
  padding: 2px 4px 10px;
}
.tl-col-head .tl-icon { font-size: 13px; }
.tl-fold-head {
  list-style: none;
  cursor: pointer;
  color: var(--tl-muted);
  font-size: 12px;
  padding: 5px 8px;
  border: 1px dashed var(--tl-line-strong);
  border-radius: 6px;
  text-align: center;
  margin-bottom: 8px;
}
.tl-fold-head::-webkit-details-marker { display: none; }
.tl-cards { display: flex; flex-direction: column; gap: 6px; min-height: 2em; }
.tl-card {
  background: var(--tl-surface);
  border: 1px solid var(--tl-line);
  border-radius: 8px;
  box-shadow: var(--tl-shadow);
  cursor: grab;
  transition: border-color 0.12s, box-shadow 0.12s;
}
.tl-card:hover { border-color: var(--tl-line-strong); }
.tl-card[open] { box-shadow: var(--tl-shadow-lift); }
.tl-dragging { opacity: 0.35; }
.tl-drop-marker {
  height: 2px;
  margin: -1px 2px;
  border-radius: 2px;
  background: var(--tl-accent);
  box-shadow: 0 0 0 3px rgba(94, 106, 210, 0.18);
}
.tl-card-head {
  list-style: none;
  display: grid;
  grid-template-columns: 1.05em 1fr;
  column-gap: 8px;
  row-gap: 6px;
  padding: 10px 10px 9px;
  cursor: pointer;
}
.tl-card-head::-webkit-details-marker { display: none; }
.tl-card-head .tl-icon { margin-top: 0.12em; }
.tl-title { font-weight: 500; color: var(--tl-ink); }
.tl-col-closed .tl-title { text-decoration: line-through; color: var(--tl-muted); }
.tl-chips { grid-column: 2; display: flex; flex-wrap: wrap; gap: 4px; }
.tl-card-body {
  border-top: 1px solid var(--tl-line);
  padding: 8px 12px 10px;
}

/* Hide backlog, in the To do column's header on every board. While backlog
   cards are hidden it reads "Show backlog (n)". */
.tl-bl-toggle {
  margin-left: auto;
  font: inherit;
  font-size: 11px;
  color: var(--tl-muted);
  background: transparent;
  border: none;
  padding: 0 2px;
  cursor: pointer;
}
.tl-bl-toggle:hover { color: var(--tl-ink); }
.tl-bl-toggle .tl-bl-show { display: none; }
.tl-hide-backlog .tl-bl-toggle .tl-bl-hide { display: none; }
.tl-hide-backlog .tl-bl-toggle .tl-bl-show { display: inline; }
.tl-hide-backlog .tl-bl-toggle::after { content: " (" attr(data-n) ")"; }
.tl-hide-backlog .tl-card[data-cat="backlog"] { display: none; }

/* New task, at the end of the To do column */
.tl-newtask {
  display: block;
  width: 100%;
  margin-top: 6px;
  padding: 6px 10px;
  font: inherit;
  font-size: 12px;
  text-align: left;
  color: var(--tl-muted);
  background: transparent;
  border: 1px dashed var(--tl-line-strong);
  border-radius: 8px;
  cursor: pointer;
}
.tl-newtask:hover { color: var(--tl-ink); border-color: var(--tl-muted); }

/* SilverBullet draws a border round the element holding a widget. The board
   and the overview are wider than the text column, so only slivers of that
   border showed above and below them; hide it for Throughline's widgets. The
   selector matches SilverBullet's own, to win over it. */
#sb-main .cm-editor :is(.sb-lua-directive-inline, .sb-lua-directive-block):has(> .tl-board, > .tl-projects, > .tl-focus) {
  border-color: transparent;
}

/* ---- Projects overview -------------------------------------------------- */
.tl-projects {
  width: min(96vw, 1200px);
  position: relative;
  left: 50%;
  transform: translateX(-50%);
  padding: 2px 0 8px;
}
.tl-toggle-closed {
  font: inherit;
  font-size: 12px;
  color: var(--tl-muted);
  background: transparent;
  border: 1px solid var(--tl-line);
  border-radius: 6px;
  padding: 3px 9px;
  cursor: pointer;
}
.tl-toggle-closed:hover { background: var(--tl-hover); color: var(--tl-ink); }
.tl-toggle-closed::after { content: " (" attr(data-n) ")"; }
.tl-toggle-closed[data-n="0"] { display: none; }
.tl-when-shown { display: none; }
.tl-show-closed .tl-when-shown { display: inline; }
.tl-show-closed .tl-when-hidden { display: none; }
.tl-psection { margin-bottom: 16px; }
.tl-psection.tl-empty { display: none; }
.tl-psection-closed { display: none; }
.tl-show-closed .tl-psection-closed:not(.tl-empty) { display: block; }
.tl-psection-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 550;
  color: var(--tl-ink-2);
  padding: 6px 4px;
  margin-bottom: 6px;
  border-bottom: 1px solid var(--tl-line);
}
.tl-pgrid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 10px;
  align-items: start;
}
.tl-pcard {
  background: var(--tl-surface);
  border: 1px solid var(--tl-line);
  border-radius: 10px;
  box-shadow: var(--tl-shadow);
  transition: border-color 0.12s, box-shadow 0.12s;
}
.tl-pcard:hover { border-color: var(--tl-line-strong); }
.tl-pcard[open] { box-shadow: var(--tl-shadow-lift); grid-column: span 2; }
@media (max-width: 640px) { .tl-pcard[open] { grid-column: auto; } }
.tl-pcard-head {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px 14px;
  cursor: pointer;
}
.tl-pcard-head::-webkit-details-marker { display: none; }
.tl-pcard-top { display: flex; align-items: center; gap: 9px; }
.tl-pname {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: var(--tl-ink) !important;
  text-decoration: none !important;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tl-pname:hover { text-decoration: underline !important; text-underline-offset: 2px; }
.tl-chev {
  margin-left: auto;
  color: var(--tl-faint);
  font-size: 11px;
  transition: transform 0.15s;
  padding: 2px 4px;
  border-radius: 4px;
}
.tl-pcard-head:hover .tl-chev { color: var(--tl-muted); background: var(--tl-hover); }
.tl-pcard[open] .tl-chev { transform: rotate(180deg); }
.tl-pcard-line { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.tl-pcard-counts { display: flex; gap: 12px; flex-wrap: wrap; }
.tl-ccount {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--tl-ink-2);
  font-variant-numeric: tabular-nums;
}
.tl-ccount .tl-icon { font-size: 12px; }
.tl-ccount.tl-zero { color: var(--tl-faint); }
.tl-ccount.tl-zero .tl-icon { opacity: 0.45; }

/* health: Linear's on track / at risk / off track */
.tl-health {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 500;
  line-height: 20px;
  padding: 0 8px 0 6px;
  border-radius: 999px;
  border: 1px solid var(--tl-line);
  color: var(--tl-ink-2);
  white-space: nowrap;
}
.tl-health-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--tl-grey);
  box-sizing: border-box;
}
.tl-health[data-health="on-track"] .tl-health-dot { background: var(--tl-green); }
.tl-health[data-health="at-risk"] .tl-health-dot { background: var(--tl-orange); }
.tl-health[data-health="off-track"] .tl-health-dot { background: var(--tl-red); }
.tl-health[data-health="on-track"] { color: var(--tl-green); }
.tl-health[data-health="at-risk"] { color: var(--tl-orange); }
.tl-health[data-health="off-track"] { color: var(--tl-red); }
.tl-health[data-health="none"], .tl-health[data-health="missing"] { color: var(--tl-muted); }
.tl-health[data-health="missing"] .tl-health-dot { background: transparent; border: 1.5px dashed var(--tl-grey); }
.tl-health.tl-stale { border-style: dashed; }
.tl-health.tl-stale .tl-health-dot { background: transparent; border: 1.5px solid currentColor; }

/* progress ring */
.tl-progress {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--tl-muted);
  font-variant-numeric: tabular-nums;
}
.tl-ring {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: conic-gradient(var(--tl-violet) calc(var(--tl-pct) * 1%), var(--tl-line-strong) 0);
  /* the hole is cut out, so the ring sits on any background */
  -webkit-mask: radial-gradient(closest-side, transparent 60%, #000 64%);
          mask: radial-gradient(closest-side, transparent 60%, #000 64%);
}
.tl-progress-none { color: var(--tl-faint); }

/* the expanded card: a stats sheet */
.tl-pcard-body {
  border-top: 1px solid var(--tl-line);
  padding: 12px 14px 14px;
  cursor: default;
}
.tl-update {
  background: var(--tl-surface-2);
  border: 1px solid var(--tl-line);
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 12px;
}
.tl-update-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 6px; }
.tl-update-date { font-size: 12px; color: var(--tl-muted); }
.tl-update-text { color: var(--tl-ink-2); }
.tl-update-text p { display: block; margin: 0.2em 0; }
.tl-update-empty { color: var(--tl-muted); font-size: 12px; }
.tl-stats {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  border: 1px solid var(--tl-line);
  border-radius: 8px;
  overflow: hidden;
}
/* hairlines between cells; the outer border hides the ones on the edge */
.tl-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 10px;
  min-width: 0;
  box-shadow: 1px 0 0 var(--tl-line), 0 1px 0 var(--tl-line);
}
.tl-stat-label { font-size: 11px; color: var(--tl-muted); text-transform: none; }
.tl-stat-value {
  font-size: 13px;
  font-weight: 550;
  color: var(--tl-ink);
  font-variant-numeric: tabular-nums;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tl-stat.tl-bad .tl-stat-value { color: var(--tl-red); }
.tl-pstatus {
  font: inherit;
  font-size: 13px;
  font-weight: 550;
  color: var(--tl-ink);
  background: transparent;
  border: 1px solid var(--tl-line);
  border-radius: 6px;
  padding: 1px 4px;
  margin-left: -5px;
  cursor: pointer;
}

/* ---- Focus list --------------------------------------------------------- */
.tl-focus { margin: 4px 0 12px; }
.tl-filterbar {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  margin-bottom: 10px;
}
.tl-filter {
  font: inherit;
  font-size: 12px;
  color: var(--tl-ink-2);
  background: var(--tl-surface);
  border: 1px solid var(--tl-line-strong);
  border-radius: 6px;
  padding: 3px 6px;
  cursor: pointer;
  max-width: 12em;
}
.tl-filter:hover { background: var(--tl-hover); }
.tl-filter-on {
  border-color: var(--tl-accent);
  color: var(--tl-accent);
  background: rgba(94, 106, 210, 0.08);
}
.tl-focus-empty {
  color: var(--tl-muted);
  font-size: 13px;
  padding: 18px;
  text-align: center;
  border: 1px dashed var(--tl-line-strong);
  border-radius: 8px;
}
.tl-fsection {
  border: 1px solid var(--tl-line);
  border-radius: 8px;
  margin-bottom: 8px;
  overflow: hidden;
  background: var(--tl-surface);
}
.tl-fsummary { list-style: none; cursor: pointer; }
.tl-fsummary::-webkit-details-marker { display: none; }
.tl-fsection-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 12px;
  background: var(--tl-surface-2);
  font-size: 13px;
  font-weight: 550;
  color: var(--tl-ink-2);
}
.tl-fsection[open] .tl-fsection-head { border-bottom: 1px solid var(--tl-line); }
.tl-fchev { color: var(--tl-faint); font-size: 10px; transition: transform 0.15s; }
.tl-fsection[open] .tl-fchev { transform: rotate(90deg); }
.tl-fsection[data-section="overdue"] .tl-fsection-title { color: var(--tl-red); }
.tl-row {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 36px;
  padding: 0 12px;
  border-bottom: 1px solid var(--tl-line);
}
.tl-row:last-child { border-bottom: none; }
.tl-row:hover { background: var(--tl-hover); }
.tl-row .tl-icon { cursor: pointer; font-size: 13px; }
.tl-row-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
  color: var(--tl-ink);
}
.tl-row-meta { display: flex; gap: 6px; flex: none; align-items: center; }
.tl-pchip { color: var(--tl-ink-2); }
.tl-pdot {
  width: 7px;
  height: 7px;
  border-radius: 2px;
  background: var(--tl-violet);
  opacity: 0.8;
}
.tl-src { border-style: dashed; }
.tl-row-closed .tl-row-title { text-decoration: line-through; color: var(--tl-muted); }
@media (max-width: 640px) {
  .tl-row { flex-wrap: wrap; padding: 6px 12px; gap: 6px 10px; }
  .tl-row-title { flex-basis: calc(100% - 2em); white-space: normal; }
  .tl-row-meta { padding-left: 1.7em; flex-wrap: wrap; }
}

/* ---- Task popover and attribute form ------------------------------------
   The popover opens from a projection's icon; the same form sits in an
   expanded board card. The popover lives outside the widgets, so it takes
   SilverBullet's modal colours. */

/* a projection's due date, after the link; red once past */
#sb-main a.sb-wiki-link[data-tl-due]::after {
  content: "⚑ " attr(data-tl-due);
  margin-left: 0.5em;
  font-size: 0.8em;
  color: var(--tl-muted);
  cursor: pointer;
}
#sb-main a.sb-wiki-link[data-tl-late]::after { color: var(--tl-red); font-weight: 600; }

.tl-pop {
  position: fixed;
  z-index: 1000;
  width: 340px;
  box-sizing: border-box;
  padding: 10px 12px;
  font-family: var(--tl-font);
  font-size: 13px;
  color: var(--modal-color, var(--tl-ink));
  background: var(--modal-background-color, var(--root-background-color, #fff));
  border: 1px solid var(--modal-border-color, var(--tl-line));
  border-radius: 8px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.18);
}
.tl-pop :is(button, input) { font-family: var(--tl-font) !important; }
.tl-pop-head { margin-bottom: 8px; }
.tl-pop-title { font-weight: 600; color: var(--tl-ink); text-decoration: none; }
.tl-pop-title:hover { text-decoration: underline; }
.tl-pop-states { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 10px; }
.tl-pop-state {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font: inherit;
  font-size: 12px;
  color: var(--tl-ink-2);
  background: transparent;
  border: 1px solid var(--tl-line);
  border-radius: 6px;
  padding: 2px 7px;
  cursor: pointer;
}
.tl-pop-state:hover { background: var(--tl-hover); }
.tl-pop-state.tl-on { border-color: var(--tl-accent); color: var(--tl-accent); }
.tl-pop-state .tl-icon { font-size: 12px; }
.tl-pop-foot { display: flex; align-items: center; gap: 6px; margin-top: 10px; }

.tl-attrs { display: flex; flex-direction: column; gap: 6px; margin-bottom: 8px; }
.tl-attr { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 8px; font-size: 12px; }
.tl-attr-label { width: 6.5em; flex: none; color: var(--tl-muted); white-space: nowrap; }
.tl-date {
  font: inherit;
  color: var(--tl-ink);
  background: transparent;
  border: 1px solid var(--tl-line);
  border-radius: 6px;
  padding: 2px 6px;
  color-scheme: light dark;
}
.tl-range { flex: 1; min-width: 6em; accent-color: var(--tl-accent); }
.tl-attr-value { color: var(--tl-muted); white-space: nowrap; font-variant-numeric: tabular-nums; }
.tl-attr-clear {
  font: inherit;
  color: var(--tl-faint);
  background: transparent;
  border: none;
  padding: 0 4px;
  cursor: pointer;
}
.tl-attr-clear:hover { color: var(--tl-red); }
.tl-card-notes .tl-attrs { padding-bottom: 8px; border-bottom: 1px solid var(--tl-line); }
.tl-blocker { color: var(--tl-accent); cursor: pointer; text-decoration: underline; text-underline-offset: 2px; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
.tl-blocker.tl-blocker-none { color: var(--tl-muted); cursor: default; text-decoration: none; }
.tl-attr-pick {
  font: inherit;
  font-size: 12px;
  color: var(--tl-accent);
  background: transparent;
  border: none;
  padding: 0 2px;
  cursor: pointer;
}
.tl-blocked { color: var(--tl-orange); }
.tl-unblocked { color: var(--tl-faint); text-decoration: line-through; }
.tl-tprog { gap: 4px; }

/* the Edit task bar at the top of a task page */
.tl-taskbar { display: flex; gap: 6px; padding: 2px 0 6px; font-family: var(--tl-font); }
.tl-taskbar .tl-button { font-family: var(--tl-font) !important; }

/* on project pages the board replaces SilverBullet's own task panels */
body.tl-project .sb-page-widget[data-view="std.linkedTasks"],
body.tl-project .sb-page-widget[data-view="std.linkedMentions"] { display: none; }

/* ---- Overflow -------------------------------------------------------------
   Nothing may push out of its box. Two rules:
   - In collapsed views (a card's front, a Focus row, chips, column and section
     heads) one-line text ends in "…"; its title attribute holds the full text.
   - In expanded views (an open card, an open project card, the task panel)
     text wraps, so everything is visible. Long words break anywhere. */
:is(.tl-board, .tl-projects, .tl-focus, .tl-pop) { overflow-wrap: anywhere; text-indent: 0; }
/* buttons under a card or a panel wrap onto a second line when narrow */
:is(.tl-actions, .tl-pop-foot, .tl-ptoolbar, .tl-ftoolbar) { flex-wrap: wrap; }
:is(.tl-board, .tl-projects, .tl-focus, .tl-pop) :is(img, video, table, pre) { max-width: 100%; }

/* chips: one line, shortened to fit */
.tl-chip { max-width: 100%; min-width: 0; overflow: hidden; }
.tl-chip > :not(.tl-pdot, .tl-ring, .tl-health-dot) { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tl-chips, .tl-pcard-line, .tl-pcard-counts { min-width: 0; max-width: 100%; }

/* card fronts: titles wrap, the grid never grows past the card */
.tl-card-head { grid-template-columns: 1.05em minmax(0, 1fr); }
.tl-card, .tl-col, .tl-cards, .tl-pcard, .tl-pcard-head, .tl-pcard-top { min-width: 0; }
.tl-col-head, .tl-psection-head, .tl-fsection-head { min-width: 0; }
:is(.tl-col-title, .tl-psection-title, .tl-fsection-title) {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tl-bl-toggle, .tl-count { flex: none; white-space: nowrap; }

/* Focus rows: the title gives way first, then the chips */
.tl-row { min-width: 0; }
.tl-row-meta { flex: 0 1 auto; min-width: 0; max-width: 55%; overflow: hidden; }
.tl-row-meta .tl-chip { flex: 0 1 auto; }
/* dates are short and matter most: they keep their size; project, page and
   blocked-by chips give way */
.tl-row-meta .tl-chip:not(.tl-pchip, .tl-src, .tl-blocked) { flex: none; }

/* task titles: at most two lines on a closed card (the title attribute holds
   the rest); in full, wrapping, once the card is open and in the task panel */
.tl-title {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  overflow: hidden;
}
.tl-card[open] .tl-title {
  display: inline;
  -webkit-line-clamp: unset;
  line-clamp: none;
  overflow: visible;
}

/* the blocking task in an open card or the task panel: at most three lines,
   the rest hidden; the link's title holds the full name */
:is(.tl-card-body, .tl-pop) .tl-blocker {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  overflow: hidden;
  white-space: normal;
}

/* expanded views show everything else: no shortening inside them */
:is(.tl-card-body, .tl-pcard-body, .tl-pop) :is(.tl-stat-value, .tl-update-text, .tl-attr-value:not(.tl-blocker)) {
  white-space: normal;
  overflow: visible;
  text-overflow: clip;
}
.tl-stats { grid-template-columns: repeat(auto-fill, minmax(min(150px, 100%), 1fr)); }
.tl-attr > * { min-width: 0; }
.tl-date { max-width: 100%; }
.tl-pop { max-width: calc(100vw - 16px); max-height: calc(100vh - 16px); overflow: auto; }
.tl-pop-states { min-width: 0; }

/* ---- Theme: native -------------------------------------------------------
   Everything above is the lineish theme. native keeps the same layout but
   takes SilverBullet's own font and colours, drops the panel backgrounds and
   shadows, and draws its rules as dotted lines. Selected by
   throughline.theme, which sets html[data-tl-theme]. */
html[data-tl-theme="native"] {
  --tl-font: var(--editor-font);
  --tl-ink: var(--root-color);
  --tl-ink-2: var(--root-color);
  --tl-muted: var(--subtle-color);
  --tl-faint: var(--meta-subtle-color);
  --tl-line: var(--ui-surface-border-color);
  --tl-line-strong: color-mix(in srgb, var(--subtle-color) 45%, transparent);
  --tl-dots: color-mix(in srgb, var(--subtle-color) 55%, transparent);
  --tl-surface: transparent;
  --tl-surface-2: transparent;
  --tl-hover: var(--subtle-background-color);
  --tl-accent: var(--ui-accent-color);
  --tl-violet: var(--ui-accent-color);
  --tl-shadow: none;
  --tl-shadow-lift: none;
  --tl-overdue-bg: transparent;
  --tl-today-bg: transparent;
}
html[data-tl-theme="native"] :is(.tl-board, .tl-projects, .tl-focus) {
  font-size: 0.95em;
  line-height: 1.5;
  -webkit-font-smoothing: auto;
}
html[data-tl-theme="native"] :is(.tl-board, .tl-projects, .tl-focus) :is(button, select, option) {
  font-family: var(--ui-font, var(--tl-font)) !important;
}

/* small print in em, so it follows the editor's size */
html[data-tl-theme="native"] :is(.tl-chip, .tl-ccount, .tl-health, .tl-progress, .tl-update-date,
    .tl-stat-label, .tl-filter, .tl-button, .tl-toggle-closed, .tl-ptoolbar-count) {
  font-size: 0.85em;
}
html[data-tl-theme="native"] :is(.tl-col-head, .tl-psection-head, .tl-fsection-head, .tl-ptoolbar-title,
    .tl-stat-value, .tl-pstatus, .tl-pname, .tl-focus-empty) {
  font-size: 1em;
}

/* chips are plain words, coloured only when they mean something */
html[data-tl-theme="native"] .tl-chip { border: none; background: none; padding: 0; border-radius: 0; }
html[data-tl-theme="native"] .tl-row-meta { gap: 0.9em; }
html[data-tl-theme="native"] .tl-chips { gap: 0.9em; }
html[data-tl-theme="native"] .tl-today { color: #9a6700; }
html[data-theme="dark"][data-tl-theme="native"] .tl-today { color: var(--tl-amber); }
html[data-tl-theme="native"] .tl-src { font-style: italic; }
html[data-tl-theme="native"] .tl-pdot { border-radius: 50%; opacity: 1; }
html[data-tl-theme="native"] .tl-ptoolbar-count { background: none; padding: 0; }

/* buttons and pickers: SilverBullet's own buttons; selects read as text */
html[data-tl-theme="native"] .tl-button {
  color: var(--button-color);
  background: var(--button-background-color);
  border: 1px solid var(--button-border-color);
  border-radius: 5px;
  box-shadow: none;
}
html[data-tl-theme="native"] .tl-button:hover { background: var(--button-hover-background-color); }
html[data-tl-theme="native"] .tl-ghost { background: transparent; border-color: transparent; color: var(--tl-muted); }
html[data-tl-theme="native"] :is(.tl-pstatus, .tl-toggle-closed, .tl-filter) {
  color: var(--tl-ink);
  background: transparent;
  border: 1px dotted var(--tl-dots);
  border-radius: 4px;
}
html[data-tl-theme="native"] .tl-pstatus { border-width: 0 0 1px; border-radius: 0; padding: 0 2px; margin-left: 0; }
html[data-tl-theme="native"] :is(.tl-toggle-closed, .tl-filter):hover { background: transparent; border-style: solid; }
html[data-tl-theme="native"] .tl-filter-on { color: var(--tl-accent); border: 1px solid var(--tl-accent); background: transparent; }

/* dotted outlines instead of panels */
html[data-tl-theme="native"] :is(.tl-col, .tl-card, .tl-pcard, .tl-focus-empty, .tl-fold-head) {
  background: transparent;
  border: 1px dotted var(--tl-dots);
  border-radius: 4px;
  box-shadow: none;
}
html[data-tl-theme="native"] :is(.tl-card, .tl-pcard):hover,
html[data-tl-theme="native"] :is(.tl-card, .tl-pcard)[open] { border-color: var(--subtle-color); }
/* board columns are open: a heading over a dotted rule, cards below */
html[data-tl-theme="native"] .tl-col { border: none; padding: 0 2px; }
html[data-tl-theme="native"] .tl-col-head {
  font-weight: 600;
  color: var(--tl-ink);
  padding: 2px 2px;
  margin-bottom: 8px;
  border-bottom: 1px dotted var(--tl-dots);
}
html[data-tl-theme="native"] .tl-board { gap: 14px; }
/* the overview stays in the text column, like the rest of the page */
html[data-tl-theme="native"] .tl-projects { width: auto; left: auto; transform: none; }
html[data-tl-theme="native"] :is(.tl-card-body, .tl-pcard-body) { border-top: 1px dotted var(--tl-dots); }
html[data-tl-theme="native"] .tl-drop-marker { box-shadow: none; }
html[data-tl-theme="native"] .tl-newtask { border: 1px dotted var(--tl-dots); border-radius: 4px; font-size: 0.85em; }
html[data-tl-theme="native"] .tl-pop { font-family: var(--editor-font); border-radius: 5px; box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2); }
html[data-tl-theme="native"] :is(.tl-pop-state, .tl-date) { border: 1px dotted var(--tl-dots); border-radius: 4px; }
html[data-tl-theme="native"] .tl-card-notes .tl-attrs { border-bottom: 1px dotted var(--tl-dots); }
html[data-tl-theme="native"] .tl-bl-toggle { font-size: 0.8em; font-weight: normal; }
html[data-tl-theme="native"] .tl-chev { color: var(--tl-muted); }
html[data-tl-theme="native"] .tl-pcard-head:hover .tl-chev { background: none; color: var(--tl-ink); }
html[data-tl-theme="native"] .tl-pname {
  color: var(--editor-wiki-link-page-color, var(--link-color)) !important;
  font-weight: 600;
  letter-spacing: 0;
}

/* section heads: bold text over a dotted rule */
html[data-tl-theme="native"] .tl-psection-head,
html[data-tl-theme="native"] .tl-fsection-head {
  background: none;
  padding: 2px 0;
  font-weight: 600;
  color: var(--tl-ink);
  border-bottom: 1px dotted var(--tl-dots);
}
html[data-tl-theme="native"] .tl-fsection {
  border: none;
  border-radius: 0;
  background: none;
  overflow: visible;
  margin-bottom: 14px;
}
/* room for the section arrow, which would otherwise poke out on the left */
html[data-tl-theme="native"] .tl-fsection-head { padding-left: 6px; }
html[data-tl-theme="native"] .tl-fsection[open] .tl-fsection-head { border-bottom: 1px dotted var(--tl-dots); }
html[data-tl-theme="native"] .tl-row {
  padding: 0 4px;
  min-height: 2.2em;
  border-bottom: 1px dotted var(--tl-dots);
}
html[data-tl-theme="native"] .tl-row:last-child { border-bottom: none; }

/* health: a dot and a word, no pill */
html[data-tl-theme="native"] .tl-health { border: none; padding: 0; border-radius: 0; }

/* the stats sheet: a dotted ledger */
html[data-tl-theme="native"] .tl-update {
  background: none;
  border: none;
  border-left: 2px solid var(--tl-dots);
  border-radius: 0;
  padding: 2px 0 2px 10px;
}
html[data-tl-theme="native"] .tl-stats { border: none; border-radius: 0; column-gap: 18px; }
html[data-tl-theme="native"] .tl-stat {
  box-shadow: none;
  padding: 5px 0;
  border-bottom: 1px dotted var(--tl-dots);
}
html[data-tl-theme="native"] .tl-stat-value { font-weight: 500; }
```
