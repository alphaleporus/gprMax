# GSoC 2026 - Daily Hours Log
**Week 1 (May 25 - May 31)**

* **May 25:** 6 hours
  * Patched gprMax setup.py compiler logic to force Apple Clang and fix OpenMP header conflicts.
  * Resolved deep virtual environment dependency chains (mpi4py, terminaltables, jinja2).
  * Built base marimo UI skeleton with reactive parameter sliders and live `.in` string preview.

* **May 26:** 4 hours
  * Debugged marimo 0.23.x orphan cell rendering issue. Root cause: cells returning display elements with no named variables are skipped by the reactive DAG. Fixed using `mo.output.replace()`.
  * Resolved Plotly aspect ratio distortion: Moved `scaleanchor` from xaxis to yaxis.
  * Completed Week 2 target early: Implemented Python geometry parser supporting `#box`, `#cylinder`, and `#sphere`. 
  * Finalised `parameter_controls.py`: 4-cell architecture, all sliders wired, `.in` preview and 2D geometry preview confirmed working.
  * Committed Component 1 to `devel` branch.

* **May 27:** 3 hours
  * Audited and cleaned repo structure removed stray parameter_controls.py from root, moved deliverable to toolboxes/Marimo/ per proposal architecture.
  * Fixed marimo 0.23.x rendering bugs: orphan cell DAG skipping (mo.output.replace pattern), Plotly axis padding (constrain="domain").
  * Posted Week 1 Zulip update. Kanban card moved to In Review.

* **May 28–31:** 0 hours
  * Component 1 committed and stable. No new commits.
  * Used the break to read gprMax FDTD internals (PML formulation, 
    field array layout) to prepare for Component 2 architecture design.

* **June 1:** 0 hours
  * PR prep: reviewed toolboxes/Marimo/ structure, wrote README.md, 
    confirmed requirements.txt.

* **June 2:** 3 hours
  * Audited repository state and resolved a dirty-fork Pull Request issue.
  * Executed a clean upstream branching strategy to isolate Component 1 deliverables from local prototype files.
  * Officially submitted the clean, 5-file Pull Request for the Component 1 Reactive Parameter Dashboard.
  * Planned backend architecture for Component 2 (`h5_reader.py`)

* **June 3:** 5 hours
  * Developed `ascan_dashboard.py`: the A-scan viewer (Component 3).
  * Read `dt` from HDF5 root attributes to build a real-time axis in
    nanoseconds; falls back to iteration count if `dt` is absent.
  * Wired `Ez` array from `rxs/rx1/Ez` to a reactive Plotly Scatter trace.
  * Integrated `mo.ui.range_slider` for zero-latency time-window zooming.
  * Verified against `cylinder_Ascan_2D.h5`: direct wave arrival at ~1.2 ns
    and PEC cylinder reflection at ~2.2 ns both visible and isolatable.
  * Diagnosed and fixed `mo.stop()` DAG propagation failure, merged guard
    check into the HDF5 read cell; documented in DEVNOTES.md.
  * Updated DEVNOTES.md with Component 3 architecture, confirmed HDF5
    schema, and marimo `mo.stop()` gotcha.
  * Ran pre-commit hooks (black formatting applied); committed and pushed
    to fork devel branch.

* **June 4:** 4 hours
  * Reviewed gprMax documentation regarding B-scan trace generation.
  * Researched the mechanics of `outputfiles_merge.py` to plan the architecture for live directory polling versus handling static merged `.h5` files.

* **June 5 - June 6:** 0 hours
  * Scheduled offline days to focus entirely on university exam preparation and academic commitments.

* **June 7:** 2 hours
  * Recorded and published the Loom video walkthrough of Components 1 & 3 for mentor review.
  * Drafted and posted the formal Week 2 progress update to the Zulip channel.

**Weeks 3-4 (June 8 - June 24)**

* **June 8 - June 24:** 0 hours
  * University examinations. No project work this window per the planned
    timeline.

**Week 5 (June 25 - July 1)**

* **June 25 - July 1:** 4 hours
  * Resumed project work post-exams.
  * Began Component 2 research: read through gprMax's simulation loop to
    understand how progress output is generated, drafted an initial
    subprocess/stderr-parsing architecture for the progress tracker.
  * Reviewed open feedback on PR #686 (Component 1) and PR #696 groundwork.

**July 2 - Architecture review with Antonis**

* **July 2:** 2 hours
  * Architecture call with Antonis. Scope for the A-scan dashboard
    redirected from a simple single-file viewer to a multi-file workspace:
    load all files upfront, pick traces interactively, dynamic component
    selection, multi-file overlay.
  * Wrote up the call notes and updated DEVNOTES.md with the new
    direction. Began scoping `h5_reader.py` as a standalone foundation
    layer to support it.

**July 3 - July 13 - ascan_dashboard.py rebuild**

* **July 3 - July 5:** 5 hours
  * Built `h5_reader.py`: standalone HDF5 reader, zero marimo dependency,
    covering `load_file`, `load_files`, `get_trace`, `get_time_axis`,
    `list_components`, `list_receivers`, `format_metadata_text`.
  * Wrote the accompanying unit test suite against synthetic HDF5
    fixtures.

* **July 6 - July 9:** 6 hours
  * Rebuilt `ascan_dashboard.py` around `h5_reader.py`: multi-file
    loading via `mo.ui.file_browser`, dynamic component and receiver
    selection, colour picker with auto-advancing palette, dual y-axis
    for mixed E/H field overlays.
  * Fixed a `mo.state()` isolation bug where the trace list was
    resetting to empty every time a dropdown changed — root cause was
    `mo.state([])` sharing a cell with UI-dependent widgets. Documented
    the fix in DEVNOTES.md as the most important architecture decision
    on this component.
  * Added metadata banner, time-zoom slider, and CSV/SVG/PDF/HTML
    export.

* **July 10 - July 13:** 4 hours
  * Full test pass against `cylinder_Ascan_2D.h5` and multi-file
    scenarios.
  * Cleaned up the branch history following the earlier feature-branch
    lesson from PR #1 — verified the diff contained only the intended
    files.
  * Opened PR #696 (`h5_reader.py` + `ascan_dashboard.py` +
    `test_h5_reader.py` + `requirements.txt`) on upstream `devel`.

**July 14 - July 26**

* **July 14 - July 26:** 3 hours
  * Lighter stretch. Followed up on Payoneer/Aadhaar verification for
    the midterm payment, monitored PR #686 and #696 for review activity,
    minor local testing on the ascan dashboard against additional
    example files.

**July 27 - Component 2**

* **July 27:** 6 hours
  * Built and debugged `progress_tracker.py` against a real gprMax run
    (`antenna_like_GSSI_1500_fs.in`, 3117 iterations).
  * Found `mo.ui.progress_bar` doesn't exist in the installed marimo
    version — replaced with a plain HTML/CSS bar.
  * Confirmed tqdm output is actually on stdout, not stderr as originally
    assumed — corrected the DEVNOTES.md architecture notes and the
    implementation to redirect `stderr=subprocess.STDOUT` and read from
    `proc.stdout`.
  * Fixed a regex false-match bug: `(\d+)/(\d+)` was matching gprMax's
    own "Model 1/1" status lines ahead of tqdm's real progress line;
    tightened to require tqdm's trailing bracket.
  * Confirmed via `grep` that gprMax has no progress callback/hook API —
    closed that open question from the original plan.
  * Verified the Stop button terminates the subprocess cleanly.
  * Pushed branch `gsoc/component-2-progress-tracker`.
  * Checked PR/review status directly against GitHub: #686 and #696
    both still open, zero reviews. Reviewed the Zulip history with
    Antonis directly and confirmed the July 2 scope-change notes were
    accurate.

**July 28 - July 31 - B-scan dashboard**

* **July 28:** 5 hours
  * Reviewed Antonis's feedback on the A-scan dashboard: multi-file
    workspace, dynamic component selection, metadata banner, and export
    all confirmed working; background subtraction and FFT explicitly
    deferred; B-scan assembly from multiple A-scan files and a 3D
    surface view named as the next things to build.
  * Designed and began building `bscan_dashboard.py`: live
    directory-polling mode that watches a running B-scan and appends
    only unseen trace files per tick, matching gprMax's per-trace
    `<basename><N>.h5` output naming.

* **July 29:** 6 hours
  * Added the load-files mode: one-shot assembly from any set of
    already-existing single-trace files, ordered by physical source
    x-position.
  * Extracted the shared "validate and stack a trace" logic into
    `trace_matrix.py`, with a 15-test pytest suite including a fixture
    set built to catch a lexicographic-vs-numeric filename sort bug and
    a shuffled-file-selection test confirming the position-based sort
    is correct regardless of click order.
  * Added the 3D Surface view alongside the Heatmap view.
  * Ran an actual gprMax `-n 20` B-scan through both dashboard modes and
    checked the output numerically: direct-wave arrival time flat to
    the millisecond across every trace, reflection arrival time from
    the buried cylinder decreasing exactly as predicted from its known
    position.

* **July 30:** 5 hours
  * Closed out the remaining items from Antonis's review: receiver
    selector and metadata banner in both dashboard parts, component
    selector added to the load-files mode, time-zoom slider, per-trace
    normalize toggle.
  * Found and fixed two marimo bugs invisible to `marimo check` and
    only caught by actually running the notebook: reading a widget's
    `.value` in the cell that creates it, and a circular-reactivity
    infinite loop between a state-writing cell and a widget built from
    that state.

* **July 31:** 5 hours
  * Diagnosed and fixed a real performance regression: SVG/PDF/HTML
    export were computed eagerly on every render, which combined with
    live polling made the dashboard feel like it reloaded every couple
    of seconds. Fixed via `mo.download`'s lazy-callable support.
  * Found and fixed the same root-cause bugs (missing slider
    `debounce`, missing `hstack` `justify`) independently present in
    `ascan_dashboard.py`, inherited from when bscan's export code was
    copied from ascan's working pattern.
  * Updated DEVNOTES.md and backfilled this hours log.
  * Committed and pushed `bscan_dashboard.py`, `trace_matrix.py`, and
    `test_trace_matrix.py` to `gsoc/component-3-bscan-dashboard`.
  * Pushed the performance fix to `gsoc/component-3-ascan-dashboard`,
    updating PR #696.