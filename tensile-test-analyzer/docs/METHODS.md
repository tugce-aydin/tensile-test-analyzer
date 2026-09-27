# Methods

## Engineering quantities

Force is normalized to N, dimensions to mm, stress to MPa and strain to a dimensionless ratio. Engineering stress is `F/A0`; strain is `extension/L0`. Imported stress–strain data bypass this conversion. A inferred force–extension display may be reconstructed from the declared geometry for direct input; maximum measured force is not reported for that mode.

Acquisition order is preserved. Rows missing the required primary numeric measurements are removed with a count. Missing optional time or lateral measurements do not delete valid primary data. A significant reversal in strain is rejected: the user must select a monotonic loading segment.

Zero subtraction and smoothing are opt-in. Savitzky–Golay smoothing changes stress only and stops before the post-fracture load drop. The unsmoothed curve remains available. All chosen settings are included in the exported snapshot.

## Elastic fit and proof stress

The model is `σ = E ε + b`, fitted by ordinary least squares. The suggestion examines short, low-strain intervals with at least eight observations. This is a heuristic, not a physical identification of the elastic limit. The final manual interval requires at least five observations with strain variation.

The reported fit includes E, intercept, R², slope standard error and sample count. Residual plots and narrower-interval fits help assess the selection. A fitted intercept remains explicit; the proof line is `E(ε − 0.002) + b`. Its first positive-to-negative intersection with `σ − σ_offset` is interpolated linearly.

Upper/lower yield candidates use prominence-filtered local peaks followed by a local minimum in an early post-elastic interval. Noise or nonstandard material response can create false candidates. Values appear as confirmed upper/lower yield only after row numbers are provided by the user.

## Peak and fracture

UTS is the highest analyzed engineering stress. Maximum load is a necking-onset estimate for an appropriate ductile metal, not a direct spatial measurement of necking. A maximum at the record endpoint is explicitly flagged.

A sudden drop to less than half of the previous stress, from a previous stress above a quarter of the curve maximum, proposes the preceding row as a fracture candidate. This is a heuristic. User confirmation or a manual fracture row is required before reporting fracture properties. An interrupted test is not silently called fractured.

## Energy and ductility

Integration uses trapezoids in acquisition order. With stress in MPa and dimensionless strain, the result is MJ/m³. A confirmed fracture record must also begin near zero strain and near zero stress to receive a full-toughness result. Otherwise the result is recorded-range energy.

Linear-elastic resilience is `σ_el²/(2E)`. A user-specified known elastic limit is used where supplied. Otherwise `Rp0.2²/(2E)` is explicitly labelled an estimate; integrating all the way to the offset intersection would include plastic work and is not used as pure elastic resilience.

Post-fracture elongation is `(Lf/L0 − 1)×100`; area reduction is `(1 − Af/A0)×100`. Both require separate measurements. They are not inferred from the final curve point.

## Transverse strain and advanced models

Poisson’s ratio is the negative slope of transverse versus axial strain over the selected elastic interval. Instantaneous width can be converted with `(width − width0)/width0` when width is in mm. Values outside the stable isotropic interval are flagged rather than interpreted as a validated auxetic/anisotropic response.

Before maximum load, the application calculates `ε_true = ln(1+ε)` and `σ_true ≈ σ(1+ε)`. The stress conversion assumes approximate volume conservation and uniform deformation. It is stopped before localized necking invalidates this global conversion.

True plastic strain is approximated as `ε_true − σ_true/E`. A Hollomon fit uses `ln(σ_true) = ln(K) + n ln(ε_pl)` in a user-selected positive plastic range. It reports K, n and log-space R². This does not establish that the material follows a power law; the example reference is deliberately not generated with a Hollomon law.

The engineering elastic/plastic decomposition shown in the interface is also restricted to the pre-maximum-load range. This is an approximation using `σ/E`.

Strain rate is a numerical time derivative when all selected timestamps are finite and strictly increasing. A finite-difference derivative amplifies measurement noise; it is not a machine-control readout.

## Sensitivity and comparisons

Geometry sensitivity changes the declared initial area and gauge length by the selected percentages. For force–extension input, E scales with `L0/A0` and stress with `1/A0`. These are deterministic bounds, not probabilistic confidence intervals. Imported stress–strain data are unchanged by geometry settings. Narrower elastic-interval fits assess selection sensitivity separately.

Statistics group entries by declared repeat group, material, temperature, gauge length, measurement method and source label. Mean and sample standard deviation are calculated only for available values. A single observation has no reported standard deviation. The grouping relies on accurate user metadata and cannot determine whether laboratory conditions truly match.

## Sources

- [University of Cambridge, DoITPoMS — Mechanical Testing of Metals](https://www.doitpoms.ac.uk/tlplib/mechanical_testing_metals/index.php)
- [Missouri S&T — tensile testing for elastic constants](https://web.mst.edu/jthomas/classes/2211/lessons/flexure/tension/details/index.html)
- [Mississippi State University — strength and stiffness characteristics](https://www.ae.msstate.edu/vlsm/materials/strength_chars/)
- [MathWorks — polyfit](https://www.mathworks.com/help/matlab/ref/polyfit.html)
- [MathWorks — trapz](https://www.mathworks.com/help/matlab/ref/trapz.html)

These references explain the educational methods. This project does not claim ASTM/ISO test-method certification or calibration of the input instrument.
