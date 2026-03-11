import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import h5py
    import plotly.graph_objects as go
    return go, h5py, mo


@app.cell
def _(mo):
    file_picker = mo.ui.file_browser(filetypes=[".h5"], label="Select merged gprMax B-Scan HDF5")
    file_picker
    return (file_picker,)


@app.cell
def _(file_picker, mo):
    if not file_picker.value:
        mo.stop(True, mo.md("Select a merged HDF5 file above to continue."))
    return


@app.cell
def _(file_picker, go, h5py, mo):
    with h5py.File(file_picker.value[0].path, 'r') as f:
        bscan_data = f['rxs']['rx1']['Ez'][:]

    fig = go.Figure(data=go.Heatmap(
        z=bscan_data.T,
        colorscale='RdBu',
        zmid=0,
        colorbar=dict(title="Amplitude (V/m)")
    ))
    fig.update_layout(
        title="gprMax B-Scan: Buried PEC Cylinder (Hyperbola)",
        xaxis_title="Trace Number (Position along surface)",
        yaxis_title="Time Step (Iterations)",
        yaxis_autorange='reversed',
        template="plotly_dark"
    )
    mo.ui.plotly(fig)
    return


if __name__ == "__main__":
    app.run()