import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    # UI Control: Soil Relative Permittivity (εr)
    permittivity_slider = mo.ui.slider(start=1.0, stop=81.0, step=0.1, value=7.0, label="Soil Relative Permittivity (εr)")

    # UI Control: Antenna Center Frequency (GHz)
    frequency_slider = mo.ui.slider(start=0.1, stop=5.0, step=0.1, value=1.0, label="Antenna Center Frequency (GHz)")

    # UI Control: Source X-Position (meters)
    source_x_slider = mo.ui.slider(start=0.0, stop=1.0, step=0.01, value=0.13, label="Source X-Position (meters)")

    # Render the controls
    mo.vstack([
        mo.md("### gprMax Parameter Controls"),
        mo.hstack([permittivity_slider, frequency_slider, source_x_slider])
    ])
    return frequency_slider, mo, permittivity_slider, source_x_slider


@app.cell
def _(frequency_slider, mo, permittivity_slider, source_x_slider):
    # Reactive variables pulling from the sliders above
    er = permittivity_slider.value
    freq_hz = frequency_slider.value * 1e9  # Convert GHz to Hz
    src_x = source_x_slider.value

    # Generate the valid .in file syntax
    in_file_content = f"""```text
    #domain: 0.5 0.5 0.002
    #dx_dy_dz: 0.002 0.002 0.002
    #time_window: 4e-9

    #material: {er} 0 1 0 half_space
    #box: 0 0 0 0.5 0.25 0.002 half_space

    #waveform: ricker 1 {freq_hz} my_pulse
    #hertzian_dipole: z {src_x} 0.25 0 my_pulse
    #rx: 0.18 0.25 0
    ```"""

    # Render the preview
    mo.vstack([
        mo.md("### Live `.in` File Preview"),
        mo.md("Notice how the commands update instantly when you move the sliders. This string can be directly written to `model.in`."),
        mo.md(in_file_content)
    ])
    return


if __name__ == "__main__":
    app.run()
