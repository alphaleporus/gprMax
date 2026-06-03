import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell
def _():
    import h5py
    import marimo as mo
    import numpy as np
    import plotly.graph_objects as go

    return go, h5py, mo, np


@app.cell
def _(mo):
    file_picker = mo.ui.file_browser(
        filetypes=[".h5"],
        label="Select gprMax HDF5 output file",
    )
    mo.output.replace(
        mo.vstack(
            [
                mo.md(
                    "### gprMax A-Scan Viewer\n\n"
                    "Select a gprMax HDF5 output file. The Ez field at the first "
                    "receiver is plotted as an interactive waveform. Use the range "
                    "slider to zoom into any time-step window."
                ),
                file_picker,
            ]
        )
    )
    return (file_picker,)


@app.cell
def _(file_picker, go, h5py, mo, np):
    # Guard: stop all downstream cells if no file is selected yet.
    # Merged into this cell so marimo's DAG correctly propagates the stop.
    if not file_picker.value:
        mo.stop(True, mo.md("_Select an HDF5 file above to continue._"))

    fpath = file_picker.value[0].path

    with h5py.File(fpath, "r") as hf:
        ez = hf["rxs"]["rx1"]["Ez"][:]
        # dt is stored as a root-level attribute in gprMax v4 HDF5 output
        dt = float(hf.attrs.get("dt", 0.0))

    n_steps = len(ez)

    # Build time axis: use real time in nanoseconds if dt is available,
    # otherwise fall back to iteration number
    if dt > 0:
        time_axis = np.arange(n_steps) * dt * 1e9  # seconds → nanoseconds
        x_label = "Time (ns)"
    else:
        time_axis = np.arange(n_steps)
        x_label = "Time Step (iterations)"

    time_slider = mo.ui.range_slider(
        start=0,
        stop=n_steps - 1,
        step=1,
        value=[0, n_steps - 1],
        label="Time Step Window (Zoom)",
        full_width=True,
    )
    mo.output.replace(time_slider)
    return dt, ez, fpath, n_steps, time_axis, time_slider, x_label


@app.cell
def _(ez, go, mo, time_axis, time_slider, x_label):
    start, end = time_slider.value

    fig = go.Figure(
        data=go.Scatter(
            x=time_axis[start : end + 1],
            y=ez[start : end + 1],
            mode="lines",
            line=dict(color="#4FC3F7", width=1.2),
            name="Ez",
        )
    )
    fig.update_layout(
        title="gprMax A-Scan — Ez field at receiver",
        xaxis_title=x_label,
        yaxis_title="Amplitude (V/m)",
        template="plotly_dark",
        height=420,
        margin=dict(l=60, r=20, t=50, b=60),
    )
    mo.ui.plotly(fig)
    return


if __name__ == "__main__":
    app.run()
