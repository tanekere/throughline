---
name: Library/tanekere/Throughline
tags: meta/library
share.uri: "ghr:tanekere/throughline/Throughline.md"
share.mode: pull
---
# Throughline

Project tracking for SilverBullet where tasks, projects and the notes you take
while working live in the same place.

* A **task** is an ordinary markdown task. One that needs room for notes and
  data gets its own **task page** in `Tasks/`; the first task on that page is
  the task's source of truth.
* Anywhere else, a task appears as a **task projection**: a plain link,
  `- [[Tasks/rerun-load-test|rerun the load test]]`, drawn with the task's live
  state. Click the icon to change the state; click the text to open the page.
* A **project** is a page tagged `#project`, with a `status:` in its
  frontmatter. Put `${throughline.board()}` on it for a Kanban board of its
  tasks. The board's card order is the order in which the page lists its task
  projections.
* `${throughline.projects()}` shows every project as a card, grouped by status,
  with its health from the latest dated update under `## Updates`.
* `${throughline.focus()}` is the "what I have to do" list: Overdue, Doing,
  Today, On hold, Upcoming, then Later and Backlog, with a filter bar.

Commands: `Throughline: Make task page` (also `/task`), `Throughline: Promote
subtask`, `Throughline: Delete task page`, `Throughline: New project`,
`Throughline: Post update`, `Throughline: Set project status`.

States, out of the box: `[ ]` planned and `[BACKLOG]` (sharing the board column
"To do"), `[DOING]`, `[WAITING]` and `[BLOCKED]` (sharing "On hold"), `[x]`
done, `[CANCELLED]`. Each has a category, which is what the library acts on.
Change them with the `throughline.states` setting.

```space-lua
-- priority: 10
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
-- State categories
---------------------------------------------------------------------------

local categoryLabels = {
  backlog = "Backlog", planned = "Planned", active = "Active",
  held = "On hold", done = "Done", cancelled = "Cancelled",
}
local categoryOrder = { "backlog", "planned", "active", "held", "done", "cancelled" }

local function stateEntry(state)
  for _, st in ipairs(tl.states()) do
    if st.state == state then return st end
  end
end

-- for states configured without a category (a 0.1 configuration) or not
-- configured at all: the default states keep their usual meaning
local defaultCategories = {
  [" "] = "planned", x = "done", X = "done", BACKLOG = "backlog", DOING = "active",
  WAITING = "held", BLOCKED = "held", CANCELLED = "cancelled",
}

-- The category a state belongs to, as configured. A configuration without
-- categories still works: `closed = true` reads as done, a default state name
-- as its default category, anything else as planned.
function tl.categoryOf(state)
  local st = stateEntry(state)
  if st then
    if st.category then return st.category end
    if st.closed then return defaultCategories[state] == "cancelled" and "cancelled" or "done" end
  end
  return defaultCategories[state] or "planned"
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
  for _, st in ipairs(tl.states()) do
    if st.state == state then return st.column or st.label end
  end
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

local function isClosed(t)
  return t.done or tl.isClosedState(t.state)
end

-- the name CSS knows a state by
local function shownState(state)
  if state == " " then return "todo" end
  if state == "x" or state == "X" then return "done" end
  return state
end

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
  local s = string.gsub(text or "", "%[[%w_]+:%s*%[%[[^%]]*%]%]%]", "")
  s = string.gsub(s, "%[[%w_]+:[^%]]*%]", "")
  s = string.gsub(s, "%[%[[^%]|]*|([^%]]*)%]%]", "%1")
  s = string.gsub(s, "%[%[[^%]]*%]%]", "")
  return trim(string.gsub(s, "%s+", " "))
end

---------------------------------------------------------------------------
-- Sources: the first top-level task on each task page
---------------------------------------------------------------------------

-- Inside query[[...]] a bare name resolves to the object's own field first, so
-- filtering by folder and project happens in Lua, not in the query.
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
    if not project or contains(t.links, project) then table.insert(out, t) end
  end
  return out
end

function tl.setState(page, state)
  local text = tl.read(page)
  local s = string.find(text, "^[-*] %[")
  if not s then
    s = string.find(text, "\n[-*] %[")
    if s then s = s + 1 end
  end
  if not s then
    editor.flashNotification("No task found on " .. page, "error")
    return
  end
  local open = string.find(text, "[", s, true)
  local close = string.find(text, "]", open + 1, true)
  tl.write(page, string.sub(text, 1, open) .. state .. string.sub(text, close))
  tl.stateMap = nil
end

---------------------------------------------------------------------------
-- Board
---------------------------------------------------------------------------

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

-- the task page's prose: everything after its frontmatter and leading task list
local function notes(page)
  local text = space.readPage(page) or ""
  text = string.gsub(text, "^%-%-%-\n.-\n%-%-%-\n", "", 1)
  local out, inList = {}, true
  for line in string.gmatch(text .. "\n", "([^\n]*)\n") do
    if not (inList and (string.match(line, "^%s*[-*] ") or string.match(line, "^%s+%S"))) then
      inList = false
      table.insert(out, line)
    end
  end
  return (string.gsub(table.concat(out, "\n"), "^%s+", ""))
end

local function cardBody(t, subs)
  local parts = {}
  for _, s in ipairs(subs or {}) do table.insert(parts, templates.taskItem(s)) end
  local body = table.concat(parts, "")
  local prose = notes(t.page)
  if prose ~= "" then body = body .. "\n" .. prose end
  if body == "" then return "_No notes yet._" end
  return body
end

-- the card's state dropdown: a native <select>, so touch screens get the OS
-- picker; its click must not toggle the card's <details>
local function stateSelect(t)
  local options = {}
  for _, st in ipairs(tl.states()) do
    local o = { value = st.state, st.label }
    if st.state == t.state then o.selected = "selected" end
    table.insert(options, dom.option(o))
  end
  local page = t.page
  return dom.select {
    class = "tl-state",
    title = "Change state",
    onclick = function(e) e.preventDefault(); e.stopPropagation() end,
    onchange = function(e) tl.moveCard(page, e.target.value) end,
    table.unpack(options),
  }
end

local function card(t, now, subs)
  local chips = {}
  local proj = projectOf(t)
  if proj then
    table.insert(chips, dom.span { class = "tl-chip", basename(proj) })
  end
  if t.due then
    local cls = "tl-chip"
    if not isClosed(t) and t.due < now then cls = cls .. " tl-overdue" end
    table.insert(chips, dom.span { class = cls, title = "due " .. t.due, "⚑ " .. shortDate(t.due) })
  end
  if t.scheduled then
    table.insert(chips, dom.span { class = "tl-chip", title = "scheduled " .. t.scheduled, "▸ " .. shortDate(t.scheduled) })
  end
  local page = t.page
  local title = tl.plainText(t.name)
  return dom.details {
    class = "tl-card",
    draggable = "true",
    ["data-page"] = page,
    ["data-title"] = title,
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
      dom.span { class = "tl-title", title },
      dom.span { class = "tl-chips", table.unpack(chips) },
      stateSelect(t),
    },
    dom.div {
      class = "tl-card-body",
      cardBody(t, subs),
      dom.div {
        class = "tl-actions",
        dom.button { class = "tl-button", onclick = function() editor.navigate(page) end, "Open task page" },
        dom.button { class = "tl-button tl-delete", onclick = function() tl.deleteTaskPage(page) end, "Delete" },
      },
    },
  }
end

function tl.recount(col)
  if not col then return end
  local n = col.querySelectorAll(".tl-card").length
  col.querySelector(".tl-count").textContent = tostring(n)
  local fold = col.querySelector(".tl-fold-head")
  if fold then fold.textContent = tostring(n) .. " closed" end
end

-- Move a card to its state's column at once, then write the source. A drop has
-- already placed the card and passes the column it came from.
function tl.moveCard(page, state, fromCol)
  local doc = js.window.document
  local el = doc.querySelector('.tl-card[data-page="' .. page .. '"]')
  local target = doc.querySelector('.tl-col[data-col="' .. tl.columnOf(state) .. '"] .tl-cards')
  if el and target then
    if not fromCol then
      fromCol = el.closest(".tl-col")
      target.appendChild(el)
    end
    el.querySelector(".tl-icon").setAttribute("data-tl-state", shownState(state))
    local select = el.querySelector(".tl-state")
    if select then select.value = state end
    tl.recount(fromCol)
    tl.recount(target.closest(".tl-col"))
  end
  tl.setState(page, state)
end

-- the order in which the project page lists its task projections
local function listOrder(project)
  local rank, n = {}, 0
  local ok, text = pcall(tl.read, project)
  if not ok or not text then return rank end
  local pattern = "^%s*[-*] %[%[(" .. escapePattern(tl.taskFolder()) .. "[^%]|]+)"
  for line in string.gmatch(text .. "\n", "([^\n]*)\n") do
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

local function splitLines(text)
  local ls = {}
  for line in string.gmatch(text .. "\n", "([^\n]*)\n") do table.insert(ls, line) end
  table.remove(ls) -- the empty string after the final newline
  return ls
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

-- the insertion line shown while dragging
function tl.clearMarker()
  local m = js.window.document.querySelector(".tl-drop-marker")
  if m then m.remove() end
end

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

local function column(title, columnKey, cards, closed, project, iconState)
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
      dom.span { class = "tl-icon", ["data-tl-state"] = shownState(iconState or "x") },
      dom.span { class = "tl-col-title", title },
      dom.span { class = "tl-count", tostring(#cards) },
    },
    list,
  }
end

-- ${throughline.board()} on a project page
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
  -- one column per distinct `column` (or label) of the open states, in order
  local cols, seen = {}, {}
  for _, st in ipairs(tl.states()) do
    local key = st.column or st.label
    if not tl.isClosedState(st.state) and not seen[key] then
      seen[key] = true
      local cards = {}
      for _, t in ipairs(tasks) do
        if not isClosed(t) and tl.columnOf(t.state) == key then table.insert(cards, card(t, now, subs[t.page])) end
      end
      table.insert(cols, column(key, key, cards, false, project, st.state))
    end
  end
  local closed = {}
  for _, t in ipairs(tasks) do
    if isClosed(t) then table.insert(closed, card(t, now, subs[t.page])) end
  end
  table.insert(cols, column("Done", "closed", closed, true, project, "x"))
  return widget.html(dom.div { class = "tl-board", table.unpack(cols) })
end

---------------------------------------------------------------------------
-- Projects: status, updates and health
---------------------------------------------------------------------------

local healthLabels = { ["on-track"] = "On track", ["at-risk"] = "At risk", ["off-track"] = "Off track" }

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
  for line in string.gmatch((text or "") .. "\n", "([^\n]*)\n") do
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

-- Pages linking to a project, in the order a page mentions them; used to
-- order cards by how the page hosting the overview lists its projects.
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

-- everything the overview needs, gathered once per render
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
    local soonEnd = addDays(now, 7)
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

local function healthPill(h)
  local cls = "tl-health"
  if h.stale then cls = cls .. " tl-stale" end
  local title = h.label
  if h.age then title = title .. ", updated " .. ago(addDays(today(), -h.age), today()) end
  return dom.span { class = cls, ["data-health"] = h.key, title = title, dom.span { class = "tl-health-dot" }, h.label }
end

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

local function stat(label, value, cls)
  return dom.div { class = "tl-stat " .. (cls or ""), dom.span { class = "tl-stat-label", label }, dom.span { class = "tl-stat-value", value } }
end

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
        stat("Due in 7 days", tostring(d.soon)),
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

local function storeGet(key)
  local ok, v = pcall(clientStore.get, key)
  if ok then return v end
end

local function storeSet(key, value)
  pcall(clientStore.set, key, value)
end

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

-- Post a project update: pick a health, write a line, and the update goes in
-- under `## Updates`, newest first.
-- the project a command acts on: the one given, else the open page if it is
-- a project, else one the user picks
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
  local choice = view.pick {
    title = question,
    source = function() return rows end,
    presentation = { row = { primary = "name" } },
  }
  return choice and choice.name
end

function tl.postUpdate(project)
  project = chooseProject(project, "Post an update for which project?")
  if not project then return end
  local h = view.pick {
    title = "How is " .. basename(project) .. " going?",
    source = function()
      return {
        { name = "On track", value = "on-track" },
        { name = "At risk", value = "at-risk" },
        { name = "Off track", value = "off-track" },
      }
    end,
    presentation = { row = { primary = "name" } },
  }
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

function tl.pickProjectStatus(project)
  project = chooseProject(project, "Set the status of which project?")
  if not project then return end
  local rows = {}
  for _, s in ipairs(tl.projectStatuses()) do table.insert(rows, { name = s.label, status = s.status }) end
  local choice = view.pick {
    title = "Status of " .. basename(project),
    source = function() return rows end,
    presentation = { row = { primary = "name" } },
  }
  if choice then
    tl.setProjectStatus(project, choice.status)
    editor.flashNotification(basename(project) .. ": " .. choice.name)
  end
end

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

---------------------------------------------------------------------------
-- Focus: the "what I have to do" list
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

-- the section a task belongs to; dates first, so a dated backlog task still
-- shows when it is due
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

local function folderOf(page)
  return string.match(page, "^([^/]+)/") or ""
end

local function whenTokens(t, now)
  local d = earliest(t.due and tostring(t.due) or nil, t.scheduled and tostring(t.scheduled) or nil)
  if not d then return "undated" end
  local tok = {}
  if d < now then table.insert(tok, "overdue") end
  if d == now then table.insert(tok, "today") end
  if d <= addDays(now, 7) then table.insert(tok, "week") end
  if d <= addDays(now, 30) then table.insert(tok, "month") end
  return table.concat(tok, " ")
end

local function dateChip(t, now)
  local due = t.due and tostring(t.due) or nil
  local sch = t.scheduled and tostring(t.scheduled) or nil
  local chips = {}
  if due then
    local cls = "tl-chip"
    if due < now then cls = cls .. " tl-overdue" elseif due == now then cls = cls .. " tl-today" end
    table.insert(chips, dom.span { class = cls, title = "due " .. due, "⚑ " .. (due == now and "Today" or shortDate(due)) })
  end
  if sch then
    local cls = "tl-chip"
    if sch < now then cls = cls .. " tl-overdue" elseif sch == now then cls = cls .. " tl-today" end
    table.insert(chips, dom.span { class = cls, title = "scheduled " .. sch, "▸ " .. (sch == now and "Today" or shortDate(sch)) })
  end
  return chips
end

-- Set the state of the task at `pos` on `page`. The position comes from the
-- index and goes stale once an earlier line on the page changes length, so
-- the line must still hold the task's text; otherwise the task is looked up
-- by its text.
function tl.setStateAt(page, pos, name, state)
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
  tl.stateMap = nil
  return true
end

function tl.pickRowState(el)
  local row = el.closest(".tl-row")
  if not row then return end
  local page = row.getAttribute("data-page")
  local rows = {}
  for _, st in ipairs(tl.states()) do table.insert(rows, { name = st.label, state = st.state }) end
  local choice = view.pick {
    title = "State: " .. row.getAttribute("data-title"),
    source = function() return rows end,
    presentation = { row = { primary = "name" } },
  }
  if not choice then return end
  local ok
  if row.getAttribute("data-source") == "1" then
    tl.setState(page, choice.state)
    ok = true
  else
    ok = tl.setStateAt(page, tonumber(row.getAttribute("data-pos")), row.getAttribute("data-title"), choice.state)
  end
  if ok then
    row.querySelector(".tl-icon").setAttribute("data-tl-state", shownState(choice.state))
    row.setAttribute("data-cat", tl.categoryOf(choice.state))
    row.setAttribute("data-state", choice.state)
    if tl.isClosedState(choice.state) then row.classList.add("tl-row-closed") else row.classList.remove("tl-row-closed") end
  end
end

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
  local empty = root.querySelector(".tl-focus-empty")
  if empty then
    if shown == 0 then empty.classList.remove("tl-hide") else empty.classList.add("tl-hide") end
  end
  if remember then
    storeSet("throughline.focus:" .. root.getAttribute("data-key"), encodeFilter(f))
  end
end

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

-- ${throughline.focus()}, or with defaults for this placement:
-- ${throughline.focus { project = "Projects/Website", when = "week" }}
-- Keys: project (a page, "this" for the page it is on, or "none"), state (a
-- state like "DOING"), category (e.g. "held"), when (overdue, today, week,
-- month, undated), tag, source (a top-level folder, "/", "task-pages" or
-- "other-pages"). The filter bar starts from these, or from what it was last
-- set to in this browser.
function tl.focus(opts)
  opts = opts or {}
  local now = today()
  local horizon = addDays(now, tl.upcomingDays())
  local host = editor.getCurrentPage()
  local folder = tl.taskFolder()
  local tasks, sourceOf = focusTasks()
  local projects = {}
  for _, p in ipairs(tl.projectList()) do projects[p.name] = p end

  local function projectOfTask(t)
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

  local bySection = {}
  for _, s in ipairs(focusSections) do bySection[s.key] = {} end
  local usedProjects, usedTags, usedFolders = {}, {}, {}
  for _, t in ipairs(tasks) do
    local sec = focusSection(t, now, horizon)
    t._section = sec
    t._project = projectOfTask(t)
    t._date = earliest(t.due and tostring(t.due) or nil, t.scheduled and tostring(t.scheduled) or nil)
    table.insert(bySection[sec], t)
    if t._project then usedProjects[t._project] = true end
    for _, tag in ipairs(t.tags or {}) do usedTags[tag] = true end
    usedFolders[folderOf(t.page)] = true
  end

  local function rank(t)
    return tl.categoryOf(t.state) == "active" and 0 or 1
  end

  local nodes = {}
  local total = 0
  for _, s in ipairs(focusSections) do
    local list = bySection[s.key]
    table.sort(list, function(a, b)
      local ra, rb = rank(a), rank(b)
      if ra ~= rb then return ra < rb end
      local da, db = a._date or "9999", b._date or "9999"
      if da ~= db then return da < db end
      return tl.plainText(a.name) < tl.plainText(b.name)
    end)
    local rows = {}
    for _, t in ipairs(list) do
      local isSource = sourceOf[t.page] == t or (sourceOf[t.page] and sourceOf[t.page].ref == t.ref)
      local title = tl.plainText(t.name)
      local meta = {}
      if t._project then
        table.insert(meta, dom.span { class = "tl-chip tl-pchip", dom.span { class = "tl-pdot" }, basename(t._project) })
      end
      if not isSource then
        table.insert(meta, dom.span { class = "tl-chip tl-src", title = "on " .. t.page, t.page })
      end
      for _, c in ipairs(dateChip(t, now)) do table.insert(meta, c) end
      local page, pos, ref = t.page, t.pos, t.ref
      table.insert(rows, dom.div {
        class = "tl-row",
        ["data-page"] = page,
        ["data-pos"] = tostring(pos),
        ["data-title"] = title,
        ["data-source"] = isSource and "1" or "0",
        ["data-taskpage"] = startsWith(page, folder) and "1" or "0",
        ["data-project"] = t._project or "",
        ["data-cat"] = tl.categoryOf(t.state),
        ["data-state"] = t.state,
        ["data-when"] = whenTokens(t, now),
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
          onclick = function()
            if isSource then editor.navigate(page) else editor.navigate(ref) end
          end,
          title,
        },
        dom.span { class = "tl-row-meta", table.unpack(meta) },
      })
    end
    total = total + #rows
    local head = dom.div {
      class = "tl-fsection-head",
      dom.span { class = "tl-fchev", "▸" },
      dom.span { class = "tl-fsection-title", s.label },
      dom.span { class = "tl-count", tostring(#rows) },
    }
    local body = dom.div { class = "tl-rows", table.unpack(rows) }
    local cls = "tl-fsection"
    if #rows == 0 then cls = cls .. " tl-hide" end
    local attrs = { class = cls, ["data-section"] = s.key }
    if not s.folded then attrs.open = "open" end
    table.insert(attrs, dom.summary { class = "tl-fsummary", head })
    table.insert(attrs, body)
    table.insert(nodes, dom.details(attrs))
  end

  -- filter bar options
  local projectOpts = {}
  local pnames = {}
  for name in pairs(usedProjects) do table.insert(pnames, name) end
  if defaults.project and not usedProjects[defaults.project] and defaults.project ~= "none" then table.insert(pnames, defaults.project) end
  table.sort(pnames)
  for _, name in ipairs(pnames) do table.insert(projectOpts, { value = name, label = basename(name) }) end
  table.insert(projectOpts, { value = "none", label = "No project" })
  local stateOpts, catOpts = {}, {}
  local seenCat = {}
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
  local tnames = {}
  for tag in pairs(usedTags) do table.insert(tnames, tag) end
  table.sort(tnames)
  for _, tag in ipairs(tnames) do table.insert(tagOpts, { value = tag, label = "#" .. tag }) end
  local sourceOpts = {
    { value = "task-pages", label = "Task pages" },
    { value = "other-pages", label = "Other pages" },
  }
  local fnames = {}
  for f in pairs(usedFolders) do table.insert(fnames, f) end
  table.sort(fnames)
  local folderOpts = {}
  for _, f in ipairs(fnames) do
    table.insert(folderOpts, { value = f == "" and "/" or f, label = f == "" and "Top level" or (f .. "/") })
  end
  local srcGroups = { { group = "Kind", options = sourceOpts }, { group = "Folder", options = folderOpts } }

  local bar = dom.div {
    class = "tl-filterbar",
    filterSelect("project", "All projects", projectOpts, current.project),
    filterSelect("state", "All states", { { group = "State", options = stateOpts }, { group = "Category", options = catOpts } }, current.state),
    filterSelect("when", "Any time", whenOpts, current.when),
    filterSelect("tag", "All tags", tagOpts, current.tag),
    filterSelect("source", "All pages", srcGroups, current.source),
    dom.button { class = "tl-button tl-ghost tl-reset", onclick = function(e) tl.resetFocusFilter(e.target) end, "Reset" },
  }

  local root = dom.div {
    class = "tl-focus",
    ["data-key"] = key,
    ["data-defaults"] = encodeFilter(defaults),
    dom.div {
      class = "tl-ftoolbar",
      dom.span { class = "tl-ptoolbar-title", "Focus" },
      dom.span { class = "tl-ptoolbar-count", tostring(total) },
    },
    bar,
    dom.div { class = "tl-focus-empty tl-hide", "Nothing matches. Clear a filter, or enjoy the quiet." },
    table.unpack(nodes),
  }
  return widget.html(root)
end

-- Widgets are built before they are attached, so the starting filter is
-- applied on the next tick, to every Focus list that has not had it yet.
function tl.applyPendingFilters()
  local roots = js.window.document.querySelectorAll(".tl-focus:not([data-filtered])")
  for i = 0, roots.length - 1 do
    local r = roots.item(i)
    r.setAttribute("data-filtered", "1")
    tl.applyFocusFilter(r, false)
  end
end

command.define { name = "Throughline: New project", run = function() throughline.newProject() end }
command.define { name = "Throughline: Post update", run = function() throughline.postUpdate() end }
command.define { name = "Throughline: Set project status", run = function() throughline.pickProjectStatus() end }

---------------------------------------------------------------------------
-- Task projections: links to task pages drawn with their live state
---------------------------------------------------------------------------

-- page -> source state, rebuilt every few seconds by the tick below (the
-- page:index event does not reach client-side Space Lua)
function tl.stateOf(page)
  if not tl.stateMap then
    local m = {}
    for _, t in ipairs(tl.sources(nil)) do m[t.page] = t.state end
    tl.stateMap = m
  end
  return tl.stateMap[page]
end

function tl.markLinks()
  local links = js.window.document.querySelectorAll("#sb-main a.sb-wiki-link")
  for i = 0, links.length - 1 do
    local a = links.item(i)
    local st = tl.stateOf(a.getAttribute("href") or "")
    if st then
      local shown = shownState(st)
      if a.getAttribute("data-tl-state") ~= shown then a.setAttribute("data-tl-state", shown) end
    end
  end
end

event.listen {
  name = "cron:secondPassed",
  run = function()
    tl.tick = (tl.tick or 0) + 1
    if tl.tick % 3 == 0 then tl.stateMap = nil end
    pcall(tl.markLinks)
    pcall(tl.markProjectPage)
    pcall(tl.applyPendingFilters)
    pcall(tl.applyTheme)
  end,
}

-- The style keys every theme off one attribute on <html>. Set on load and
-- checked every tick, so a changed config shows without a reload.
function tl.applyTheme()
  local root = js.window.document.documentElement
  local theme = tl.theme()
  if root.getAttribute("data-tl-theme") ~= theme then root.setAttribute("data-tl-theme", theme) end
end
pcall(tl.applyTheme)

-- A click on a projection's icon opens SilverBullet's picker; a click on its
-- text navigates as usual.
function tl.pickState(page)
  local rows = {}
  for _, st in ipairs(tl.states()) do table.insert(rows, { name = st.label, state = st.state }) end
  table.insert(rows, { name = "Delete task page…", delete = true })
  local choice = view.pick {
    title = "State: " .. page,
    source = function() return rows end,
    presentation = { row = { primary = "name" } },
  }
  if choice and choice.delete then
    tl.deleteTaskPage(page)
  elseif choice then
    tl.setState(page, choice.state)
    tl.markLinks()
  end
end

function tl.onLinkClick(e)
  local a = e.target.closest and e.target.closest("a.sb-wiki-link")
  if not a or not a.getAttribute("data-tl-state") then return end
  local r = a.getBoundingClientRect()
  if e.clientX - r.left > r.height * 1.1 then return end
  e.preventDefault()
  e.stopPropagation()
  tl.pickState(a.getAttribute("href"))
end

local root = js.window.document.documentElement
if root.getAttribute("data-tl-click") ~= "1" then
  root.setAttribute("data-tl-click", "1")
  js.window.document.addEventListener("click", function(e) throughline.onLinkClick(e) end, true)
end

-- On project pages the board replaces SilverBullet's Linked Tasks and Linked
-- Mentions panels. Checked on load and on every tick: on a fresh client the
-- page's tags may not be indexed yet when it loads.
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
  run = function() pcall(tl.markProjectPage) end,
}

---------------------------------------------------------------------------
-- Commands: make, promote, delete
---------------------------------------------------------------------------

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
  local projectLink = "%[%[(" .. escapePattern(tl.projectFolder()) .. "[^%]|]+)"
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
  local slug = editor.prompt("Task page name (" .. folder .. "…)", tl.slugFor(alias))
  if not slug or trim(slug) == "" then return end
  local target = folder .. trim(slug)
  if pageExists(target) then
    editor.flashNotification(target .. " already exists", "error")
    return
  end
  -- the source names its project explicitly: its own link, else the project
  -- page it came from, else the nearest project link above it, else the
  -- project of the task page it came from
  local projectLink = "%[%[(" .. escapePattern(tl.projectFolder()) .. "[^%]|]+)"
  local project = string.match(first, projectLink)
  if not project then
    if startsWith(page, tl.projectFolder()) then project = page
    else project = b.inheritedProject end
    if not project and startsWith(page, folder) then
      project = string.match(tl.read(page), projectLink)
    end
    if project then b.lines[1] = first .. " [[" .. project .. "]]" end
  end
  local body = "---\npageDecoration:\n  tree:\n    hide: true\n---\n" .. table.concat(b.lines, "\n") .. "\n"
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
  tl.stateMap = nil
  editor.flashNotification((promoted and "Promoted to " or "Created ") .. target)
end

-- the task page a delete acts on: the open page if it is one, otherwise the
-- task page linked from the line under the cursor
local function taskPageAtCursor()
  local folder = tl.taskFolder()
  local page = editor.getCurrentPage()
  if startsWith(page, folder) then return page end
  local line = editor.getCurrentLine()
  return string.match(line and line.text or "", "%[%[(" .. escapePattern(folder) .. "[^%]|]+)")
end

-- Delete a task page and every projection of it, after confirmation.
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
  local msg = "Delete " .. target .. "?"
  if count > 0 then
    msg = msg .. "\n\nThis also removes " .. count .. " projection(s) on: " .. table.concat(where, ", ")
  end
  if not editor.confirm(msg) then return end
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
  tl.stateMap = nil
  editor.flashNotification("Deleted " .. target)
end

command.define { name = "Throughline: Make task page", run = function() throughline.makeTaskPage() end }
command.define { name = "Throughline: Promote subtask", run = function() throughline.makeTaskPage() end }
command.define { name = "Throughline: Delete task page", run = function() throughline.deleteTaskPage() end }

-- /task: on a task, make its task page; elsewhere, write a new task first
slashCommand.define {
  name = "task",
  description = "Make a task page from this task, or start a new one",
  run = function()
    local line = editor.getCurrentLine()
    if not (line and string.match(line.text or "", "^%s*[-*] %[[^%]]*%] ")) then
      local what = editor.prompt("New task", "")
      if not what or trim(what) == "" then return end
      editor.insertAtCursor("- [ ] " .. trim(what))
    end
    throughline.makeTaskPage()
  end,
}
```

```space-style
/* priority: 10 */
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
.tl-state {
  grid-column: 2;
  justify-self: start;
  font: inherit;
  font-size: 12px;
  color: var(--tl-muted);
  background: transparent;
  border: 1px solid var(--tl-line);
  border-radius: 6px;
  padding: 1px 4px;
  cursor: pointer;
}
.tl-card-body {
  border-top: 1px solid var(--tl-line);
  padding: 8px 12px 10px;
}
/* projected subtasks carry a link to their source position; noise in a card */
.tl-card-body a.wiki-link[data-ref*="@"] { display: none; }
.tl-card-body h2 { font-size: 1em; margin: 0.5em 0 0.2em; }
.tl-card-body ul { padding-left: 1.2em; margin: 0.2em 0; }
.tl-card-body p { display: block; margin: 0.3em 0; }

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

/* on project pages the board replaces SilverBullet's own task panels */
body.tl-project .sb-page-widget[data-view="std.linkedTasks"],
body.tl-project .sb-page-widget[data-view="std.linkedMentions"] { display: none; }

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
    .tl-stat-label, .tl-filter, .tl-button, .tl-toggle-closed, .tl-state, .tl-ptoolbar-count) {
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
html[data-tl-theme="native"] :is(.tl-state, .tl-pstatus, .tl-toggle-closed, .tl-filter) {
  color: var(--tl-ink);
  background: transparent;
  border: 1px dotted var(--tl-dots);
  border-radius: 4px;
}
html[data-tl-theme="native"] :is(.tl-state, .tl-pstatus) { border-width: 0 0 1px; border-radius: 0; padding: 0 2px; margin-left: 0; }
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
