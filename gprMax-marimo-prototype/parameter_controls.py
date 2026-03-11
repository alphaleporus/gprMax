import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _(mo):
    permittivity = mo.ui.slider(
        start=1.0, stop=20.0, step=0.5, value=6.0,
        label="Soil Relative Permittivity (εr)"
    )
    frequency = mo.ui.slider(
        start=0.5, stop=3.0, step=0.1, value=1.5,
        label="Antenna Center Frequency (GHz)"
    )
    src_x = mo.ui.slider(
        start=0.05, stop=0.45, step=0.01, value=0.15,
        label="Source X-Position (meters)"
    )
    mo.md(f"### gprMax Parameter Controls\n{permittivity}\n{frequency}\n{src_x}")
    return frequency, permittivity, src_x


@app.cell
def _(frequency, mo, permittivity, src_x):
    mo.md(f"""
### Live `.in` File Preview

Move the sliders above. This output is valid gprMax syntax and can be written directly to `model.in`.

```text
#domain: 0.5 0.5 0.002
#dx_dy_dz: 0.002 0.002 0.002
#time_window: 4e-9

#material: {permittivity.value} 0 1 0 half_space
#box: 0 0 0 0.5 0.25 0.002 half_space

#waveform: ricker 1 {frequency.value}e9 my_pulse
#hertzian_dipole: z {src_x.value:.2f} 0.25 0 my_pulse
#rx: {src_x.value + 0.05:.2f} 0.25 0
```
""")
    return


if __name__ == "__main__":
    app.run()