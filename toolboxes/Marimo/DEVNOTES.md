# gprMax Marimo Dashboard — Developer Notes

Running log of architecture decisions, framework gotchas, and things
to surface in the official docs. Updated as each component is built.

---

## Environment

### Apple Silicon build (macOS 15, M1/M2)
`setup.py` hardcodes `/opt/homebrew/bin/gcc-15` in the darwin block,
ignoring `CC` overrides. On macOS 15 this triggers a fatal SDK header
conflict (`_bounds.h` not found).

**Fix:** patch darwin block to use Apple Clang + LLVM libomp.

```python
os.environ["CC"] = "clang"
compile_args = ["-O3", "-w", "-Xpreprocessor", "-fopenmp", "-march=native", ...]
libraries = ["omp"]   # LLVM omp, not GNU gomp
```

Build command:
```bash
CFLAGS="-I/opt/homebrew/opt/libomp/include" \
LDFLAGS="-L/opt/homebrew/opt/libomp/lib" \
pip install -e . --no-build-isolation
```

**Status:** applied locally, not yet submitted upstream as its own PR.
**Doc flag:** needs a macOS install note in the official setup guide.

---

## marimo 0.23.x Behaviours

### Orphan cell problem
Cells that return a display element (e.g. `mo.vstack`, `mo.md`) but no
named variables are not executed by the reactive DAG. They have no
downstream dependents so marimo skips them silently.

**Fix:** use `mo.output.replace()` inside the cell that owns the data.
This is a side-effect call — sets display output independently of
what the cell returns.

```python
@app.cell
def _(mo):
    slider = mo.ui.slider(...)
    mo.output.replace(mo.vstack([mo.md("### Header"), slider]))
    return slider   # export for downstream cells
```

**Doc flag:** document this pattern in the contributor guide as the
standard way to display + export from the same cell.

### mo.stop() does not propagate through empty guard cells
`mo.stop(condition, output)` halts the current cell and is intended
to stop all downstream cells. However, if the guard cell returns
nothing (`return`), downstream cells have no named variable dependency
on it. marimo's DAG does not consider them downstream and they execute
anyway, causing crashes.

```python
# Broken — guard cell returns nothing, downstream cell runs regardless
@app.cell
def _(file_picker, mo):
    if not file_picker.value:
        mo.stop(True, mo.md("Select a file."))
    return  # no named return = no downstream dependency

@app.cell
def _(file_picker, h5py):
    # This cell runs even when file_picker is empty — IndexError
    with h5py.File(file_picker.value[0].path, "r") as hf:
        ...
```

**Fix:** merge the guard check into the same cell as the operation
it is protecting. The stop then halts the cell before the crash.

```python
@app.cell
def _(file_picker, h5py, mo):
    if not file_picker.value:
        mo.stop(True, mo.md("Select a file."))
    # Only reaches here if a file is selected
    with h5py.File(file_picker.value[0].path, "r") as hf:
        ...
```

### UI element embedding in mo.md f-strings
Embedding slider objects via f-string interpolation in `mo.md()` does
not render the widget in 0.23.x. Use `mo.vstack()` with the element
as a direct child instead.

```python
# Broken in 0.23.x
mo.md(f"### Header\n{slider}")

# Works
mo.vstack([mo.md("### Header"), slider])
```

### Reading a widget's `.value` in the cell that creates it — not allowed
Discovered while building `bscan_dashboard.py`. If a cell does
`widget = mo.ui.dropdown(...)` and then reads `widget.value` later in
that **same** cell, marimo raises `RuntimeError: Accessing the value
of a UIElement in the cell that created it is not allowed` — but only
at actual execution time. `marimo check` (the static linter) does not
catch this; it passed clean on the exact code that then failed when
run. The only way to catch it is to actually run the notebook.

```python
# Broken — raises RuntimeError at runtime, invisible to marimo check
@app.cell
def _(mo):
    directory_input = mo.ui.text(...)
    bases = scan_bases(directory_input.value)   # same cell — fails
    ...
```

**Fix:** split widget creation and the cell that reads its `.value`
into two separate cells, same pattern as the orphan-cell fix above
(`file_browser` → data-loading cell in `ascan_dashboard.py` already
does this correctly; it was `bscan_dashboard.py`'s directory-input
cell that got this wrong initially).

### Circular reactivity: a cell that writes state and depends on a
### widget built from that same state loops forever
Also found while building `bscan_dashboard.py`. If cell A calls
`set_state(...)` and cell B reads `get_state()` to build a widget
(e.g. populate a dropdown's options), and cell A also takes that
widget as one of its own inputs — every `set_state()` call in A
triggers B to rerun, which produces a **new** widget object even if
its visible value is unchanged, which is a changed input to A, which
reruns and calls `set_state()` again. Forever. This does not raise an
error — the notebook just never finishes rendering. `marimo check`
does not catch this either; only actually running the notebook
(`marimo export`, `marimo run`) surfaces it, and even then it looks
like a hang, not a crash.

```python
# Broken — infinite loop, no error, notebook just never settles
@app.cell
def _(get_state, mo):
    known = get_state()["known_components"]
    component_selector = mo.ui.dropdown(options=known, ...)
    return (component_selector,)

@app.cell
def _(component_selector, set_state, mo):
    # depends on component_selector AND writes state that the cell
    # above reads — this is the cycle
    set_state({...})
    return
```

**Fix:** don't let a widget's construction depend on state that the
widget's own consumer writes to. In `bscan_dashboard.py` this meant
the component/receiver picker cells peek directly at the first
matching file on disk (independent of the shared accumulator state)
instead of reading `known_components` out of state — so they only
rerun when the directory/file selection actually changes, not every
time the poll cell writes new data.

### `mo.download`'s `data` accepts a zero-argument callable — use it
`mo.download(data=..., ...)` accepts either literal bytes or a
callable that returns bytes. The callable form is lazy: it only runs
when the button is actually clicked. Passing eager bytes means the
expensive computation (e.g. `plotly.io.to_image()`, which spins up
headless Chrome via kaleido) reruns on **every** cell re-execution,
not just on click. This was the actual cause of a "dashboard reloads
every couple of seconds" complaint when live polling was on: every
poll tick re-ran the renderer cell, which re-ran two kaleido exports
synchronously before anything could update.

```python
# Broken — recomputes on every render, not just on click
svg_btn = mo.download(data=pio.to_image(fig, format="svg"), ...)

# Fixed — only runs when clicked
def _make_svg():
    return pio.to_image(fig, format="svg", width=1200, height=600, scale=2)
svg_btn = mo.download(data=_make_svg, ...)
```

The same applies to `fig.to_html(include_plotlyjs=True)` — not slow
like kaleido (no external process), but it embeds the entire Plotly.js
library (several MB) into the button's payload on every render
regardless of trace-data size, which is enough on its own to trip
marimo's static-export output-size cap (see below) even with a tiny
dataset. Make it lazy too.

**Trade-off:** going lazy means failure (e.g. Chrome not installed)
only surfaces when the button is clicked, not ahead of time. Keep a
static note near the buttons pointing at `plotly_get_chrome` and the
Plotly toolbar's camera icon (works without kaleido at all) as a
fallback, since you can no longer show a conditional error message
before the click happens.

**Doc flag:** this belongs in the contributor guide next to the
`mo.output.replace()` pattern — any `mo.download` wrapping an
expensive computation should default to the callable form.

### `mo.ui.slider` / `mo.ui.range_slider` default to `debounce=False`
Without `debounce=True`, dragging fires a reactive update on every
pixel of movement, not just on release. Combined with an expensive
downstream cell (see above), this means dragging a slider doesn't
trigger the expensive work once — it triggers it dozens of times
mid-drag, before the mouse is even released.

```python
# fires continuously while dragging
font_size = mo.ui.slider(start=10, stop=22, value=13, label="Font size")

# fires once, on release
font_size = mo.ui.slider(start=10, stop=22, value=13, label="Font size", debounce=True)
```

Set `debounce=True` on any slider whose downstream cell does real
work (rebuilding a figure, exporting, recomputing a CSV) — there is
essentially never a reason to want live feedback on every pixel of a
cosmetic control like font size or line width.

### `mo.hstack` defaults to `justify="space-between"`, not `"start"`
With two widgets in an `mo.hstack([a, b], gap="2rem")`, the default
justify pushes them to opposite edges of the container rather than
clustering them together with the given gap — looks broken/unpolished
especially with only 2–3 items (more items partially masks it since
there's more content to distribute the spacing across). Set
`justify="start"` explicitly on every hstack unless the spread-out
look is actually wanted.

### Static export caps total cell output at 10MB by default
`marimo export html` enforces `output_max_bytes` (default ~10MB) per
cell. An interactive `mo.ui.plotly(fig)` widget plus a redundant eager
`to_html(include_plotlyjs=True)` download in the *same* cell can trip
this even with a trivially small dataset, since Plotly.js itself is
multi-MB and was being embedded twice. When a cell's output is
silently replaced with `"Your output is too large"`, check for
duplicate embeds of the Plotly.js bundle before assuming a real
rendering bug — this can also be raised via `[tool.marimo.runtime]
output_max_bytes = ...` in `pyproject.toml` if a genuinely large
output is unavoidable, but the better fix is usually removing the
duplicate embed (see the `mo.download` lazy-callable note above).

### Confirmed working
- `mo.ui.plotly(fig)` returned from a cell renders correctly
- `mo.vstack([...])` called via `mo.output.replace()` renders correctly
- `mo.ui.slider` — confirmed working (Component 1)
- `mo.ui.range_slider` — confirmed working (Component 3); state resets
  correctly when a new file is selected via `mo.ui.file_browser`
- `mo.ui.file_browser` — confirmed working; `.value` is a tuple of
  file objects, each with a `.path` attribute; empty tuple when nothing
  selected; also accepts a `value=` constructor argument to pre-select
  files programmatically (used for headless testing — see below)
- `mo.ui.refresh(options=[...], default_interval=...)` — confirmed
  working as a polling timer for `bscan_dashboard.py`'s live directory
  watch; referencing `refresh.value` in a cell's signature establishes
  the reactive dependency on the timer tick
- `mo.ui.run_button` — confirmed working; **no `value=` constructor
  override exists**, so a "click" cannot be simulated for headless
  testing the way `file_browser`'s selection can

---

## Plotly

### scaleanchor and axis padding
Applying `scaleanchor="y"` on the x-axis causes Plotly to pad the
x-range symmetrically to match the y scale, pushing the domain off
to the right (x goes negative).

**Fix:** apply `scaleanchor="x"` on the y-axis only, and add
`constrain="domain"` to both axes.

```python
xaxis=dict(range=[-0.01, domain_x + 0.01], constrain="domain", ...),
yaxis=dict(range=[-0.01, domain_y + 0.01], scaleanchor="x",
           constrain="domain", ...),
```

### kaleido needs Chrome — `pip install kaleido` alone is not enough
`kaleido` v1+ requires Google Chrome's headless engine to rasterize
figures for `plotly.io.to_image()` (SVG/PDF export). Installing the
Python package is not sufficient on its own.

**One-time setup:**
```bash
plotly_get_chrome
```
This downloads a dedicated "Chrome for Testing" binary to kaleido's
own cache directory — does not touch or require the user's regular
browser. Diagnostic to confirm it worked:
```bash
python -c "import plotly.io as pio, plotly.graph_objects as go; \
fig = go.Figure(data=go.Scatter(x=[1,2,3], y=[1,2,3])); \
print('OK', len(pio.to_image(fig, format='svg')))"
```
Without this step, every `pio.to_image()` call raises
`ChromeNotFoundError`. See the `mo.download` lazy-callable note above
for the separate performance issue this interacts with — even with
Chrome correctly installed, calling `to_image()` eagerly on every
render is slow enough (headless Chrome invocation per call) to make
a dashboard feel broken if it's not made lazy.

**Two independent SVG export paths exist, both worth keeping:**
- The Plotly toolbar's camera icon: browser-side rendering via
  JavaScript, does **not** need kaleido/Chrome at all, always works,
  exports the current viewport including any zoom.
- The dashboard's own "Download SVG" button: Python-side via
  `pio.to_image()`, needs kaleido + Chrome, exports the figure as
  currently configured (not viewport-dependent).

---

## Testing infrastructure

### Pure-logic modules, tested independently of marimo
Same principle as `h5_reader.py`'s original design (Decision 2.1):
any logic that doesn't strictly need marimo — file discovery, data
validation, array stacking — goes in its own module with zero marimo
imports, so it's testable with plain `pytest` against synthetic HDF5
fixtures, no running notebook required.

`trace_matrix.py` follows this pattern for the B-scan work:
`process_trace()` (validate + extract one column from a loaded
single-trace file, with a `preferred_receiver` override) and
`stack_traces()` (assemble an ordered list of loaded files into a
matrix, in whatever order the caller decides — trace number for a
live sequential run, physical position for a hand-picked file set).
15 tests in `tests/test_trace_matrix.py`, covering component/receiver
fallback, mismatched-length rejection, missing-source-position
handling, and the specific case of a *shuffled* input list correctly
sorting to physical position rather than trusting selection order.

### Headless validation for marimo notebooks, without a browser
Two tools catch different classes of bug:

- **`marimo check --strict <file>.py`** — static graph validation.
  Catches syntax errors, undefined references, and cell-dependency
  issues. Does **not** catch the same-cell `.value` access bug or the
  circular-reactivity bug above — both passed `marimo check` clean
  and only failed when actually run.
- **`marimo export html <file>.py -o out.html`** — actually executes
  the full reactive graph once, headlessly, with each widget's
  default/constructor value. This is what caught both of the above.
  Requires the notebook's imports (e.g. `toolboxes.Marimo.h5_reader`)
  to be resolvable, so run it with `PYTHONPATH` set to the repo root
  and a real `toolboxes/Marimo/__init__.py` present (namespace
  packages didn't reliably resolve for this).

**Simulating user input for a headless test:** most `mo.ui.*` widgets
accept a `value=` constructor argument that pre-fills their starting
state — `mo.ui.text(value=...)`, `mo.ui.file_browser(value=[...])`,
`mo.ui.range_slider(value=[...])` all confirmed working this way.
`mo.ui.run_button` does not (see "Confirmed working" above), so a
button click cannot be simulated headlessly — the workaround used for
`ascan_dashboard.py` was to seed the isolated `mo.state([])` trace
list directly with a literal trace dict, as if "Add trace" had
already been clicked, to exercise the renderer cell in an export test.

**Regex sort traps:** when discovering `gprMax`'s per-trace B-scan
files (`<base><N>.h5`), a naive `sorted()` on filenames sorts
lexicographically, not numerically — `1, 10, 11, 12, 2, 3, ...`
instead of `1, 2, 3, ..., 12`. Tested explicitly against a 1–12
fixture set before trusting the sort in production code.

---

## Component 1 — Parameter Controls 

### Architecture decisions
- 4 cells: imports / sliders + display / in_text + preview / geometry
- Receiver position hardcoded as `src_x + 0.040 m` (40 mm offset).
  Will need a slider in a later iteration.
- `surface_y = 0.170` hardcoded. Acceptable for 2D TMz scope.
  Should become a slider when domain controls are added.
- Geometry parser is fault-tolerant by design — `try/except
  (IndexError, ValueError): pass` on every line. Parser reads the
  same `in_text` string shown in the preview, so geometry is always
  in sync.

### Parser coverage
| Primitive   | Plotly shape | Notes                        |
|-------------|--------------|------------------------------|
| `#box`      | rect         | Uses y-coords from .in file  |
| `#cylinder` | circle       | Axis-along-z assumed (2D)    |
| `#sphere`   | circle       | Projected to x-y plane       |

### Known gaps (for later)
- No `#rx_array` support
- No multi-material colour mapping
- No `#fractal_box` or `#add_surface_roughness`
- Cylinder rendered as ellipse if `constrain="domain"` is missing

### Status
PR open on upstream `devel` (`gsoc/component-1-parameter-controls`),
unreviewed as of the last check.

---

## Component 2 — Simulation Progress Tracker ✅

Built and verified end-to-end against a real 3117-iteration run
(`antenna_like_GSSI_1500_fs.in`). File:
`toolboxes/Marimo/progress_tracker.py`. Branch:
`gsoc/component-2-progress-tracker` — pushed, PR not yet opened.

### What it does
Launches gprMax via `subprocess` with `--show-progress-bars`, reads
live output on a background thread, mirrors progress into the UI via
`mo.ui.refresh` + `mo.state`, renders a plain HTML/CSS bar. Stop
button confirmed to terminate the process cleanly (`ps aux` showed
nothing lingering afterward).

### Corrections to this doc's earlier "planned architecture"
The original plan below (kept for the record) said tqdm output was
on stderr and that `mo.ui.progress_bar()` would render it. **Both
were wrong, confirmed by actually running it:**

- **tqdm output is on stdout, not stderr.** Confirmed by redirecting
  stdout/stderr separately on a real run — stderr came back 0 bytes.
  Implementation redirects `stderr=subprocess.STDOUT` and reads from
  `proc.stdout`.
- **`mo.ui.progress_bar` does not exist** in the installed marimo
  version. `AttributeError` on first real run. Replaced with a plain
  inline HTML/CSS bar via `mo.Html` — no dependency on a named widget
  that may not exist across marimo versions.
- **The naive regex `(\d+)/(\d+)` false-matches gprMax's own status
  lines** — e.g. "Model 1/1, input file: ..." and "Writing geometry
  view file 1/1," both matched before tqdm's real progress line did.
  Tightened to `(\d+)/(\d+)\s*\[` — requires tqdm's trailing bracket,
  which gprMax's own log lines don't have.
- **Open question resolved:** does gprMax expose a Python API
  hook/callback for progress, as an alternative to parsing stdout?
  Checked directly (`grep -rn "callback|hook" gprMax/ --include="*.py"`)
  — no such API exists. Output parsing is the only option currently,
  not a workaround pending something better.

### Still open
- `DEVNOTES.md`'s Component 2 section (this one) needed the stderr
  correction above — done as of this update.
- PR not yet opened on GitHub (branch pushed, description drafted).

---

## Component 3 — Post-Processing Visualization ✅

Covers both the A-scan viewer and the B-scan dashboard — grouped here
per the original proposal's Component 3 deliverable list, which
included both "A-scan viewer" and "B-scan radargram with live
trace-by-trace updates" under one component, even though they ended
up as two separate files.

### A-Scan Viewer (`ascan_dashboard.py`)

#### HDF5 schema (confirmed from `cylinder_Ascan_2D.h5`)

```
/rxs/rx1/Ez      — Ez electric field time series at receiver (always present)
/rxs/rx1/Ex      — Ex field (present if requested in .in file)
/rxs/rx1/Ey      — Ey field (present if requested in .in file)
/rxs/rx1/Hx      — Hx magnetic field (present if requested)
/rxs/rx1/Hy      — Hy magnetic field (present if requested)
/rxs/rx1/Hz      — Hz magnetic field (present if requested)
```

Field component availability varies by model configuration. `Ez` is
present for all 2D TMz models and used as the default in the dashboard.
The root-level `dt` attribute holds the time step in seconds and is
used to build the real-time axis.

#### Architecture — grown considerably past the original 3-cell design
Antonis's July 2 architecture redirect (see below) turned this from a
single-file viewer into a workspace-style multi-file dashboard:
load all files up front, pick traces interactively, build overlay
plots. `h5_reader.py` was added as the foundation layer underneath —
zero marimo dependency, pure `h5py` + `numpy`, independently testable.

Current cell structure: imports / file loading / metadata banner /
isolated trace-list state / trace picker / button handler / appearance
controls / time-zoom slider / figure renderer + export.

- Guard check (`if not file_picker.value: mo.stop(...)`) merged into
  the HDF5 read cell — see the `mo.stop()` marimo gotcha above.
- Time axis: `np.arange(n_steps) * dt * 1e9` gives nanoseconds when
  `dt` is present in HDF5 root attrs.
- `mo.output.replace()` used throughout to display + export from the
  same cell — see the orphan-cell gotcha above.
- Dual y-axis (V/m left, A/m right, dashed lines) when the active
  trace list mixes E-field and H-field components.
- Metadata banner via `h5_reader.format_metadata_text()` — shows dt,
  dx/dy/dz, grid size, receiver positions for each loaded file.
- Multi-file loading, dynamic component/receiver selection, colour
  picker with auto-advancing palette (Matplotlib tab10), time-zoom
  slider (`mo.ui.range_slider`, always exports full unzoomed data on
  download regardless of zoom state), CSV/SVG/PDF/HTML export.

#### Confirmed output on `cylinder_Ascan_2D.h5`
- dt = 4.71731e-12 s → 637 steps → 3.0 ns total window
- Direct wave arrival visible at ~1.2 ns
- Reflected signal from buried PEC cylinder visible at ~2.2 ns
- Range slider zooms correctly; chart updates on every tick
- Time axis label: `Time (ns)` (confirmed correct unit)

#### Known gaps — closed since last update
- ~~Only reads `rx1`~~ — **fixed.** Receiver selector added, reads
  from `list_receivers()` dynamically, never hardcoded.
- ~~Only reads `Ez`~~ — **fixed.** Component selector was already
  dynamic; still true that it defaults to `Ez` when present.
- ~~No time-gating~~ — **already present** via the time-zoom slider;
  this line in the original notes was stale by the time it was written.

#### Still deferred, explicitly, per Antonis's own stated priority
- Background subtraction (target trace minus free-space trace)
- FFT frequency spectrum toggle (reuse `gprMax.utilities.utilities.fft_power`,
  do not reimplement)

Both were named directly in Antonis's review of this dashboard and
explicitly deferred by him until the foundation was confirmed solid —
next up, not skipped.

#### Performance bug found and fixed this session
The SVG/PDF/HTML export buttons were computed eagerly on every cell
re-execution — see the `mo.download` lazy-callable gotcha above for
the mechanism. Also missing `debounce=True` on all three sliders
(line width, font size, time zoom) and `justify="start"` on four
`mo.hstack` calls. All fixed; see the marimo-behaviours section above
for the general pattern, since the same bugs were independently
introduced in `bscan_dashboard.py` by copying this code.

#### Status
PR #696 open on upstream `devel`, unreviewed as of the last check
(alongside PR #686 for Component 1). Branch:
`gsoc/component-3-ascan-dashboard`.

---

### B-Scan Dashboard (`bscan_dashboard.py`) — new this session

Directly answers two things from Antonis's review notes on the A-scan
dashboard: "multiple files - bscan" (assemble many A-scan files into
a radargram) and "3d" (a 3D surface view of the same data). Built as
a second file rather than folded into `ascan_dashboard.py`, since the
two dashboards serve genuinely different visualization paradigms
(line-overlay comparison vs. spatial heatmap/surface) and Antonis's
own wording ("bscan") pointed at a distinct tool.

#### Two independent modes in one file
- **Part 1 — Live monitoring.** Watches an output directory while
  gprMax is actively writing a sequential B-scan (`-n N` run,
  producing one closed `.h5` file per trace). Polls on a selectable
  interval, only reads unseen files each tick, never rebuilds the
  accumulated matrix from scratch — this was flagged in the original
  proposal as the hardest part of the whole project, and the
  append-only-new-files behaviour was explicitly tested (two ticks
  with the same files present load zero new traces; a third tick with
  new files present loads only those).
- **Part 2 — Load files.** One-shot assembly from any set of
  already-existing single-trace `.h5` files, not necessarily from a
  live-running or even the same B-scan — ordered by physical source
  x-position when available (read from each file's own `srcs/src1`
  metadata), falling back to selection order otherwise.

Both modes share one tested core (`trace_matrix.py`, see Testing
infrastructure above) for the "validate and stack a trace" logic, but
deliberately do **not** share reactive state — Part 1's incremental
accumulator and Part 2's one-shot assembly are different enough
strategies that keeping them structurally independent was safer than
a unified toggle, especially after already tripping the circular-
reactivity bug once in Part 1 alone (see above).

#### File naming convention
`gprMax`'s per-trace B-scan output: `<basename><N>.h5`, e.g.
`cylinder_Bscan_2D1.h5` … `cylinder_Bscan_2D60.h5` for a `-n 60` run.
Regex: `^(.*?)(\d+)\.h5$` — the digit group is greedy even though the
base-name group is lazy, so multi-digit trace numbers parse correctly
(`cylinder_Bscan_2D10.h5` → base `cylinder_Bscan_2D`, num `10`, not a
stray `1` left in the base). See the regex-sort-trap note above.

#### View modes
Heatmap (default, `zmid=0` diverging colourscale, appropriate for a
signed field like Ez) and 3D Surface (`go.Surface`), both built from
the identical assembled matrix — trivial to add once the data is
shaped as `(n_time, n_positions)` either way.

#### Additional features added on top of the original scope, matching
#### Antonis's ascan-review requests
- Metadata banner (reuses `h5_reader.format_metadata_text()`)
- SVG/PDF export (kaleido, same lazy pattern as ascan)
- Receiver selector (both parts)
- Component selector (Part 2 — was previously always auto-picking,
  now user-selectable like Part 1)
- Time-window zoom slider (both parts, same "zoom is view-only, CSV
  always exports full data" convention as ascan's own zoom slider)
- Per-trace normalize toggle (view-only, CSV stays raw) — addresses
  Antonis's vaguely-scoped "manipulate" comment and standard GPR
  practice: deep reflections are much weaker than the direct wave,
  and without some gain control a real (non-synthetic) dataset can
  wash out entirely on a fixed colour scale.

#### Verified against real gprMax output, not just synthetic fixtures
Ran an actual `-n 20` B-scan (`cylinder_Bscan_2D.in`, gprMax
`4.0.0b0`) through both dashboard parts. Confirmed:
- 637 iterations, dt = 4.7173 ps — matches the `.h5` schema exactly.
- **Direct wave: peak time exactly 1.113 ns across all 30 selected
  traces, zero spread.** Correct — source and receiver step together
  with a fixed 0.04 m separation (both step 0.002 m per run per the
  `.in` file), so the direct coupling has nothing to shift it.
- **Reflection arrival time decreases monotonically, 2.486 ns → 2.227
  ns, as source x-position goes 0.04 → 0.098 m.** Also correct: the
  buried PEC cylinder sits at x=0.12 m; with a fixed 0.04 m offset,
  the antenna midpoint reaches the cylinder's x-position (closest
  approach, minimum travel time) when the source is at x = 0.12 −
  0.02 = 0.10 m — one step past the 30-trace selection used, and the
  data shows arrival time still decreasing right up to the last trace
  with no sign of turning around yet, exactly as predicted.
- Load-files mode: fed a deliberately *shuffled* file selection
  (clicked out of numeric order) and confirmed the radargram is
  identical regardless of click order — position-based sort, not
  selection-order, is what actually determines column placement.

#### Known gaps — deliberate, documented in the dashboard's own UI, not oversights
- No fallback yet to a merged output file (`outputfiles_merge.py`
  format) if gprMax stops writing fully-closed per-trace files before
  starting the next one. Deferred: the proposal's original assumption
  (one closed file per trace) has now been confirmed against a real
  run, so this defends against a scenario with no indication it's
  coming, at the cost of supporting a different HDF5 schema
  `h5_reader.py` doesn't currently parse.
- No invert-polarity or time-shift controls. Antonis's "manipulate"
  scope was never fully pinned down in the July 2 call notes — zoom
  and normalize are built; the rest is worth clarifying with him
  rather than guessing further.
- Background subtraction / FFT not built here either, same deferral
  as ascan_dashboard.py, staying consistent with that call.
- Uses the first receiver found per file unless overridden via the
  receiver selector — not tested end-to-end against a real
  multi-receiver `.h5` file (only against a synthetic one), since no
  real multi-receiver gprMax output was available during development.

#### Performance bugs found and fixed this session
Same three bugs as `ascan_dashboard.py` (eager kaleido/`to_html`,
missing slider `debounce`, missing `hstack` `justify`) — inherited
because this file's export code was originally copied from
`ascan_dashboard.py`'s working pattern before the performance issue
in that pattern was known. Fixed in both files; see the marimo-
behaviours section above.

#### Status
Branch `gsoc/component-3-bscan-dashboard`, forked from
`gsoc/component-3-ascan-dashboard`. Not yet committed/pushed as of
this note.

---

## Component 4 — Reactive Recipes (not started)

Per the original proposal: Recipe 1 (A-scan end-to-end workflow
combining parameter controls, simulation launch, progress tracking,
and waveform inspection) and Recipe 2 (Velocity and Permittivity
Calculator). Stretch: PML Tuning visualization, S11 antenna parameter
recipe.

Sequencing note: better to build this *after* background subtraction
and FFT land in `ascan_dashboard.py`, since Recipe 1 is more useful
once it can show frequency-domain and background-subtracted views,
not just raw traces.