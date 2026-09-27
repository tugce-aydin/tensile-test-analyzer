# Training datasets

All files in this directory were generated for this project. **None is a laboratory measurement or a published alloy dataset.** The examples are intended to check computation and teach interpretation; they do not establish experimental accuracy.

Regenerate with `python scripts/generate_examples.py` from the repository root. `manifest.json` records parameters and random seeds.

| File | Purpose |
| --- | --- |
| `reference.csv` | Smooth reference: E = 200 GPa, initial yield = 250 MPa, UTS = 450 MPa, ν = 0.30 |
| `noisy.csv` | Same model with seeded 1.3 MPa standard-deviation stress noise |
| `replicate.csv` | Same model with seeded 0.5 MPa stress noise |
| `aluminium_model.csv` | Illustrative alternative: E = 70 GPa, initial yield = 160 MPa, UTS = 310 MPa, ν = 0.33; not a named aluminium grade |
| `brittle.csv` | Linear elastic model that fractures at ε = 0.004; no 0.2% proof intersection |
| `incomplete.csv` | Truncated reference that must not be reported as complete toughness |
| `reference.xlsx` | Reference CSV represented as the `Test` worksheet |
| `direct_stress.csv` | Reference stress in MPa and strain in percent; choose direct stress–strain mode |

## Columns

- `time_s`: time in seconds; reference strain rate is 0.001 s⁻¹.
- `force_N`: axial force in newtons, generated from stress × 10 mm².
- `extension_mm`: gauge extension, generated from engineering strain × 50 mm.
- `transverse_strain`: dimensionless lateral strain. Elastic data follow −ν ε; later values use an illustrative plastic contraction model. Calculate ν only within the elastic interval.

The final two points of ductile examples represent a load drop. The fracture candidate is the last point before that drop. The generator's post-necking branch is a prescribed engineering curve, not a local constitutive law.

No specimen final length or fracture area is invented. Enter separately measured values to calculate post-fracture ductility metrics.

## Analytical check

With `ey = 250 / 200000`, the reference curve uses a linear elastic branch, a sinusoidal hardening branch up to ε = 0.15 and a declining prescribed engineering branch up to ε = 0.25. Its analytical area is:

`0.5*250*ey + 250*(0.15-ey) + 200*(0.15-ey)*2/pi + 450*0.1 - 150*0.1/2.5`

The trapezoidal implementation is checked against this expression. Data are distributed under the repository's MIT license.
