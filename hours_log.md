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
  * Recorded and published the Loom video walkthrough of Components 1 & 2 for mentor review.
  * Drafted and posted the formal Week 2 progress update to the Zulip channel.