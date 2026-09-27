# Feature map

The planned scope is implemented in one application; optional results depend on available measurements. “Unavailable” is an intentional result when the required information is absent.

| # | Capability | Where to use it |
| ---: | --- | --- |
| 1 | CSV and XLSX import | Data source |
| 2 | Column mapping | Columns & units |
| 3 | Direct stress–strain input | Input type |
| 4 | Area / rectangular / circular geometry | Specimen & measurement |
| 5 | Force, extension, stress and strain conversions | Columns & units |
| 6 | Specimen, material, temperature and source metadata | Sample fields and preserved upload source |
| 7 | Missing values, duplicates and invalid geometry checks | Analysis checks and review notes |
| 8 | Row selection, zero correction and smoothing | Preprocessing |
| 9 | Engineering stress–strain curve | Overview |
| 10 | Suggested and graphical elastic interval | Elastic region |
| 11 | E, intercept, R², standard error and residuals | Elastic region; full fit statistics in JSON |
| 12 | 0.2% proof stress and offset line | Elastic region |
| 13 | Upper/lower yield candidates and explicit row confirmation | Elastic region and preprocessing |
| 14 | UTS, maximum load and strain at maximum load | Overview and property table |
| 15 | Maximum-load necking estimate, with endpoint warning | Overview and review notes |
| 16 | Fracture candidate, completeness confirmation and manual row | Preprocessing and data summary |
| 17 | Fracture strain, post-fracture elongation and area reduction | Property table; separate measurements required |
| 18 | Known-limit or estimated resilience | Elastic shading, property table and notes |
| 19 | Recorded energy and confirmed complete tensile toughness | Overview and property table |
| 20 | Poisson’s ratio from transverse strain or width | Advanced analysis |
| 21 | Pre-necking true quantities | Advanced analysis |
| 22 | Elastic/plastic decomposition | Advanced analysis |
| 23 | Hollomon K and n with adjustable plastic interval | Advanced analysis and analysis ranges |
| 24 | Strain rate from increasing time data | Advanced analysis |
| 25 | Geometry bounds and elastic-interval sensitivity | Advanced analysis and sensitivity settings |
| 26 | Multiple curves and matching-condition replicate statistics | Comparison |
| 27 | Interactive overview, elastic, offset and energy plots | Overview and elastic region |
| 28 | True, hardening, Poisson, strain-rate and decomposition plots | Advanced analysis |
| 29 | CSV, JSON, HTML, PDF, PNG and SVG export | Data & report; per-plot PNG/SVG via chart controls |
| 30 | Settings and original data saved and reopened | Analysis JSON export and restore |
| 31 | Deterministic, noisy, brittle and incomplete training data | Data source; data directory |
| 32 | Tests, method documentation and example outputs | tests/, docs/, data/ |
| + | English, German, Turkish with one calculation engine | Header language selector |
| + | Light and dark themes | Header appearance selector |
| + | Independent MATLAB reference calculation | matlab/ — execution pending in MATLAB |

The app runs locally. The MATLAB companion has not been executed in the development environment; independently reviewed laboratory validation remains future work.
