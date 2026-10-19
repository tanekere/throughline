---
name: Library/tanekere/Throughline
tags: meta/library
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
* A **project** is a page tagged `#project`. Put `${throughline.board()}` on it
  for a Kanban board of its tasks. The board's card order is the order in which
  the page lists its task projections.

Commands: `Throughline: Make task page` (also `/task`), `Throughline: Promote
subtask`, `Throughline: Delete task page`.

States, out of the box: `[ ]` to do, `[DOING]`, `[WAITING]` and `[BLOCKED]`
(sharing the board column "On hold"), `[x]` done, `[CANCELLED]`. Change them
with the `throughline.states` setting.

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
  ui = { category = "Throughline", label = "Task folder" },
})

config.define("throughline.projectFolder", {
  description = "Folder holding project pages, with a trailing slash.",
  type = "string",
  default = "Projects/",
  ui = { category = "Throughline", label = "Project folder" },
})

config.define("throughline.states", {
  description = "Task states in board order. States with the same `column` share a board column; a card dropped there takes the one marked `drop`. `closed` states share the Done column.",
  type = "array",
  default = {
    { state = " ",         label = "To do" },
    { state = "DOING",     label = "Doing" },
    { state = "WAITING",   label = "Waiting",   column = "On hold" },
    { state = "BLOCKED",   label = "Blocked",   column = "On hold", drop = true },
    { state = "x",         label = "Done",      closed = true },
    { state = "CANCELLED", label = "Cancelled", closed = true },
  },
  ui = { category = "Throughline", label = "States" },
})

function tl.taskFolder() return config.get("throughline.taskFolder", "Tasks/") end
function tl.projectFolder() return config.get("throughline.projectFolder", "Projects/") end
function tl.states() return config.get("throughline.states", {}) end

-- Defining the custom states gives completion and SilverBullet's state picker.
for _, st in ipairs(tl.states()) do
  if st.state ~= " " and st.state ~= "x" then
    taskState.define { name = st.state, done = st.closed or false }
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

-- The index's own `done` flag covers [x] only; taskState.define { done = true }
-- does not set it, so closed states come from the configuration.
function tl.isClosedState(state)
  if state == "x" or state == "X" then return true end
  for _, st in ipairs(tl.states()) do
    if st.state == state then return st.closed or false end
  end
  return false
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
    if not st.closed and (st.column or st.label) == column then
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

local function column(title, columnKey, cards, closed, project)
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
      dom.span { title },
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
    if not st.closed and not seen[key] then
      seen[key] = true
      local cards = {}
      for _, t in ipairs(tasks) do
        if not isClosed(t) and tl.columnOf(t.state) == key then table.insert(cards, card(t, now, subs[t.page])) end
      end
      table.insert(cols, column(key, key, cards, false, project))
    end
  end
  local closed = {}
  for _, t in ipairs(tasks) do
    if isClosed(t) then table.insert(closed, card(t, now, subs[t.page])) end
  end
  table.insert(cols, column("Done", "closed", closed, true, project))
  return widget.html(dom.div { class = "tl-board", table.unpack(cols) })
end

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
  end,
}

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
  --tl-ink: #1f2328;
  --tl-muted: #6b7280;
  --tl-amber: #e8a400;
  --tl-blue: #2f74d0;
  --tl-col-bg: #f3f4f6;
  --tl-card-bg: #ffffff;
  --tl-card-border: #e2e5e9;
  --tl-card-shadow: 0 1px 2px rgba(16, 24, 40, 0.06), 0 1px 3px rgba(16, 24, 40, 0.08);
  --tl-chip-bg: #eef1f5;
  --tl-overdue: #c92a2a;
  --tl-overdue-bg: #fde8e8;
}
html[data-theme="dark"] {
  --tl-ink: #e3e5e8;
  --tl-muted: #9aa1ab;
  --tl-amber: #f2b632;
  --tl-blue: #6ea2ec;
  --tl-col-bg: #23262b;
  --tl-card-bg: #2c3036;
  --tl-card-border: #3a3f46;
  --tl-card-shadow: 0 1px 2px rgba(0, 0, 0, 0.4);
  --tl-chip-bg: #383d45;
  --tl-overdue: #ff8787;
  --tl-overdue-bg: #4a2427;
}

/* ---- State icons ---------------------------------------------------------
   Three places draw a state: SilverBullet's own task (editor and query
   results, [data-task-state]), board cards (.tl-icon) and task projections
   (links with data-tl-state). The default custom states get icons; any other
   state keeps SilverBullet's text. */

/* SilverBullet's task: shrink the state word to a 1em box, hide brackets */
[data-task-state="DOING"], [data-task-state="WAITING"],
[data-task-state="BLOCKED"], [data-task-state="CANCELLED"] {
  display: inline-block;
  position: relative;
  width: 1em;
  height: 1em;
  overflow: hidden;
  text-indent: 0; /* list lines carry a negative hanging indent */
  color: transparent !important;
  vertical-align: -0.12em;
}
:is([data-task-state="DOING"], [data-task-state="WAITING"],
    [data-task-state="BLOCKED"], [data-task-state="CANCELLED"]) * {
  color: transparent !important; /* the editor nests a coloured span */
}
.sb-task-mark:has(+ :is([data-task-state="DOING"], [data-task-state="WAITING"], [data-task-state="BLOCKED"], [data-task-state="CANCELLED"])),
:is([data-task-state="DOING"], [data-task-state="WAITING"], [data-task-state="BLOCKED"], [data-task-state="CANCELLED"]) + .sb-task-mark,
.sb-atom:has(+ :is([data-task-state="DOING"], [data-task-state="WAITING"], [data-task-state="BLOCKED"], [data-task-state="CANCELLED"])),
:is([data-task-state="DOING"], [data-task-state="WAITING"], [data-task-state="BLOCKED"], [data-task-state="CANCELLED"]) + .sb-atom {
  display: none;
}

/* the icon box, in all three places */
:is([data-task-state="DOING"], [data-task-state="WAITING"],
    [data-task-state="BLOCKED"], [data-task-state="CANCELLED"])::before,
.tl-icon,
#sb-main a.sb-wiki-link[data-tl-state]::before {
  content: "";
  box-sizing: border-box;
  border-radius: 50%;
}
:is([data-task-state="DOING"], [data-task-state="WAITING"],
    [data-task-state="BLOCKED"], [data-task-state="CANCELLED"])::before {
  position: absolute;
  inset: 0.06em;
}
.tl-icon {
  display: inline-block;
  position: relative;
  width: 1.05em;
  height: 1.05em;
  margin-top: 0.08em;
}
#sb-main a.sb-wiki-link[data-tl-state]::before {
  display: inline-block;
  width: 0.95em;
  height: 0.95em;
  margin-right: 0.35em;
  vertical-align: -0.13em;
  cursor: pointer;
}

/* to do and done: only cards and projections need these; SilverBullet draws
   its own checkbox */
.tl-icon[data-tl-state="todo"],
#sb-main a.sb-wiki-link[data-tl-state="todo"]::before {
  border: 0.12em solid var(--tl-muted);
  border-radius: 0.22em;
}
.tl-icon[data-tl-state="done"],
#sb-main a.sb-wiki-link[data-tl-state="done"]::before {
  border-radius: 0;
  background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Crect width='16' height='16' rx='3.5' fill='%232f9e44'/%3E%3Cpath d='M4 8.3l2.6 2.6L12 5.5' fill='none' stroke='white' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") center / contain no-repeat;
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
  background: var(--tl-ink);
  -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Ccircle cx='8' cy='8' r='6.2' fill='none' stroke='black' stroke-width='2.4'/%3E%3Cline x1='3.25' y1='4.01' x2='12.75' y2='11.99' stroke='black' stroke-width='2.4'/%3E%3C/svg%3E") center / contain no-repeat;
          mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Ccircle cx='8' cy='8' r='6.2' fill='none' stroke='black' stroke-width='2.4'/%3E%3Cline x1='3.25' y1='4.01' x2='12.75' y2='11.99' stroke='black' stroke-width='2.4'/%3E%3C/svg%3E") center / contain no-repeat;
}
[data-task-state="CANCELLED"]::before { inset: 0; }

/* A state without an icon of its own: a projection shows its name as a small
   label; a card shows a plain ring, since its dropdown already names it. */
#sb-main a.sb-wiki-link[data-tl-state]:not([data-tl-state="todo"], [data-tl-state="done"],
    [data-tl-state="DOING"], [data-tl-state="WAITING"], [data-tl-state="BLOCKED"],
    [data-tl-state="CANCELLED"])::before {
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
    [data-tl-state="WAITING"], [data-tl-state="BLOCKED"], [data-tl-state="CANCELLED"]) {
  border: 0.12em solid var(--tl-muted);
}

/* closed tasks: grey text (SilverBullet already strikes it) */
.cm-line:has([data-task-state="CANCELLED"]) .cm-task-checked { color: #8a8f98; }
#sb-main a.sb-wiki-link:is([data-tl-state="CANCELLED"], [data-tl-state="done"]) {
  text-decoration: line-through;
  opacity: 0.75;
}

/* ---- Board ------------------------------------------------------------- */
.tl-board {
  /* break out of the text column: the board wants width, prose does not */
  width: min(96vw, 1200px);
  position: relative;
  left: 50%;
  transform: translateX(-50%);
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(11em, 1fr);
  gap: 0.6em;
  overflow-x: auto;
  font-family: var(--ui-font, system-ui, sans-serif);
  font-size: 0.86rem;
  padding: 0.2em 0 0.6em;
}
.tl-col {
  background: var(--tl-col-bg);
  border-radius: 10px;
  padding: 0.5em;
  min-height: 6em;
}
.tl-col-closed { opacity: 0.85; }
.tl-col-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 650;
  font-size: 0.8em;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--tl-muted);
  padding: 0.1em 0.3em 0.5em;
}
.tl-count {
  background: var(--tl-chip-bg);
  border-radius: 999px;
  padding: 0 0.55em;
  font-weight: 600;
}
.tl-fold-head {
  list-style: none;
  cursor: pointer;
  color: var(--tl-muted);
  font-size: 0.85em;
  padding: 0.3em 0.4em;
  border: 1px dashed var(--tl-card-border);
  border-radius: 6px;
  text-align: center;
  margin-bottom: 0.45em;
}
.tl-fold-head::-webkit-details-marker { display: none; }
.tl-cards { display: flex; flex-direction: column; gap: 0.45em; min-height: 2em; }
.tl-card {
  background: var(--tl-card-bg);
  border: 1px solid var(--tl-card-border);
  border-radius: 8px;
  box-shadow: var(--tl-card-shadow);
  cursor: grab;
}
.tl-card[open] { box-shadow: 0 4px 12px rgba(16, 24, 40, 0.14); }
.tl-dragging { opacity: 0.35; }
.tl-drop-marker {
  height: 3px;
  margin: -0.12em 0.15em;
  border-radius: 2px;
  background: var(--tl-blue);
  box-shadow: 0 0 0 3px rgba(47, 116, 208, 0.18);
}
.tl-card-head {
  list-style: none;
  display: grid;
  grid-template-columns: 1.1em 1fr;
  column-gap: 0.45em;
  row-gap: 0.35em;
  padding: 0.55em 0.6em;
  cursor: pointer;
  line-height: 1.3;
}
.tl-card-head::-webkit-details-marker { display: none; }
.tl-title { font-weight: 550; }
.tl-col-closed .tl-title { text-decoration: line-through; color: var(--tl-muted); }
.tl-chips { grid-column: 2; display: flex; flex-wrap: wrap; gap: 0.3em; }
.tl-chip {
  font-size: 0.78em;
  background: var(--tl-chip-bg);
  color: var(--tl-muted);
  border-radius: 4px;
  padding: 0.05em 0.4em;
  white-space: nowrap;
}
.tl-chip p, .tl-title p { display: inline; margin: 0; }
.tl-overdue { background: var(--tl-overdue-bg); color: var(--tl-overdue); font-weight: 600; }
.tl-state {
  grid-column: 2;
  justify-self: start;
  font: inherit;
  font-size: 0.78em;
  color: var(--tl-muted);
  background: transparent;
  border: 1px solid var(--tl-card-border);
  border-radius: 4px;
  padding: 0.05em 0.2em;
  cursor: pointer;
}
.tl-card-body {
  border-top: 1px solid var(--tl-card-border);
  padding: 0.4em 0.7em 0.6em;
  font-size: 0.95em;
}
/* projected subtasks carry a link to their source position; noise in a card */
.tl-card-body a.wiki-link[data-ref*="@"] { display: none; }
.tl-card-body h2 { font-size: 1em; margin: 0.5em 0 0.2em; }
.tl-card-body ul { padding-left: 1.2em; margin: 0.2em 0; }
.tl-actions { display: flex; gap: 0.4em; margin-top: 0.4em; }
.tl-button {
  font: inherit;
  font-size: 0.85em;
  border: 1px solid var(--tl-card-border);
  background: var(--tl-col-bg);
  border-radius: 6px;
  padding: 0.2em 0.6em;
  cursor: pointer;
}
.tl-delete { color: var(--tl-overdue); }

/* on project pages the board replaces SilverBullet's own task panels */
body.tl-project .sb-page-widget[data-view="std.linkedTasks"],
body.tl-project .sb-page-widget[data-view="std.linkedMentions"] { display: none; }
```
