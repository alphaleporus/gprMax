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

### Confirmed working
- `mo.ui.plotly(fig)` returned from a cell renders correctly
- `mo.vstack([...])` called via `mo.output.replace()` renders correctly
- `mo.ui.slider` — confirmed working (Component 1)
- `mo.ui.range_slider` — confirmed working (Component 3); state resets
  correctly when a new file is selected via `mo.ui.file_browser`
- `mo.ui.file_browser` — confirmed working; `.value` is a tuple of
  file objects, each with a `.path` attribute; empty tuple when nothing
  selected

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

---

## Component 2 — Simulation Progress Tracker (upcoming)

### Planned architecture
- Launch gprMax via `subprocess.Popen` with `stderr=subprocess.PIPE`
- tqdm in gprMax writes progress to stderr, not stdout. Format observed:
  `|--->: 100%|████| 637/637 [00:00<00:00, 1015.34it/s]`
- Parse `current/total` from stderr lines to derive percentage
- Push updates into `mo.state`; UI cell reads state and renders
  `mo.ui.progress_bar()`
- Background thread reads stderr line by line to avoid blocking the
  main thread

### Open questions
- Does gprMax expose any Python API hooks for progress (e.g. a callback
  or event) that are preferable to parsing stderr? Ask Craig before
  implementing.
- What is the correct error surface when gprMax exits non-zero?
  Capture stderr tail and display inline, or raise?

---

## Component 3 — A-Scan Viewer ✅

### HDF5 schema (confirmed from `cylinder_Ascan_2D.h5`)

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

### Architecture decisions
- 3 cells: imports / file picker + HDF5 read + slider / waveform plot
- Guard check (`if not file_picker.value: mo.stop(...)`) merged into
  the HDF5 read cell — see marimo section above for why
- Time axis: `np.arange(n_steps) * dt * 1e9` gives nanoseconds when
  `dt` is present in HDF5 root attrs. Falls back to iteration count
  if `dt` is missing (older output files)
- `mo.output.replace(time_slider)` used to display the slider from
  the same cell that reads the file and builds the slider object

### Confirmed output on `cylinder_Ascan_2D.h5`
- dt = 4.71731e-12 s → 637 steps → 3.0 ns total window
- Direct wave arrival visible at ~1.2 ns
- Reflected signal from buried PEC cylinder visible at ~2.2 ns
- Range slider zooms correctly; chart updates on every tick
- Time axis label: `Time (ns)` (confirmed correct unit)

### Known gaps (for later)
- Only reads `rx1`. Multi-receiver files need a receiver selector
- Only reads `Ez`. Field component selector would improve flexibility
- No time-gating or background subtraction controls