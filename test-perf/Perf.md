Timings, in milliseconds, of Throughline's main pieces on this space.

${(function()
  local now = js.window.performance
  local function t(f) local a = now.now(); f(); return math.floor(now.now() - a) end
  local rows = {}
  local function add(name, f) table.insert(rows, "| " .. name .. " | " .. t(f) .. " |") end
  add("sources(nil)", function() throughline.sources(nil) end)
  add("stateMap rebuild", function() throughline.stateMap = nil; throughline.stateOf("x") end)
  add("markLinks", function() throughline.markLinks() end)
  add("board(Website)", function() throughline.board("Projects/Website") end)
  add("projects()", function() throughline.projects() end)
  add("focus()", function() throughline.focus() end)
  return "| piece | ms |\n|---|---|\n" .. table.concat(rows, "\n")
end)()}
