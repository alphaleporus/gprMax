import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import h5py
    import plotly.graph_objects as go
    import numpy as np
    return go, h5py, mo, np


@app.cell
def _(mo):
    file_picker = mo.ui.file_browser(filetypes=[".h5"], label="Select gprMax HDF5 output")
    file_picker
    return (file_picker,)


@app.cell
def _(file_picker, mo):
    if not file_picker.value:
        mo.stop(True, mo.md("Select an HDF5 file above to continue."))
    return


@app.cell
def _(file_picker, h5py, mo, np):
    with h5py.File(file_picker.value[0].path, 'r') as f:
        ez_data = f['rxs']['rx1']['Ez'][:]

    n_steps = len(ez_data)
    time_slider = mo.ui.range_slider(
        start=0, stop=n_steps - 1, step=1,
        value=[0, n_steps - 1], label="Time Step Window (Zoom)"
    )
    time_slider
    return ez_data, n_steps, time_slider


@app.cell
def _(ez_data, go, mo, np, time_slider):
    start, end = time_slider.value
    fig = go.Figure(data=go.Scatter(
        x=np.arange(start, end),
        y=ez_data[start:end],
        mode='lines',
        name='Ez'
    ))
    fig.update_layout(
        title="gprMax A-Scan: PEC Cylinder",
        xaxis_title="Time Step (Iterations)",
        yaxis_title="Amplitude (V/m)",
        template="plotly_dark"
    )
    mo.ui.plotly(fig)
    return


if __name__ == "__main__":
    app.run()