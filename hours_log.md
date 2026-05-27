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