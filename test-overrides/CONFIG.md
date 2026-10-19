Throughline overrides, to test that every setting is honoured.

```space-lua
config.set("throughline.taskFolder", "Todo/")
config.set("throughline.projectFolder", "Work/")
config.set("throughline.states", {
  { state = " ",         label = "To do" },
  { state = "DOING",     label = "Doing" },
  { state = "REVIEW",    label = "In review" },
  { state = "WAITING",   label = "Waiting",   column = "Parked" },
  { state = "BLOCKED",   label = "Blocked",   column = "Parked" },
  { state = "x",         label = "Done",      closed = true },
  { state = "CANCELLED", label = "Cancelled", closed = true },
})
```
