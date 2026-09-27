# Validation record

Checked on 27 September 2026.

## Automated numerical and API checks

**26 tests passed** under Python 3.12 on Linux. The dependency versions are pinned in `requirements.txt` and `requirements-dev.txt`.

Coverage includes:

- E = 200 GPa, UTS = 450 MPa and ν = 0.30 for the synthetic reference.
- Resilience = 0.15625 MJ/m³ from the specified 250 MPa elastic limit.
- Numerical toughness compared with an independently integrated closed-form expression.
- The offset intersection satisfying the offset-line equation.
- Equivalent N/kN, mm/m and ratio/percent inputs.
- Brittle fracture without a fabricated proof stress; interrupted tests without fabricated full toughness.
- Missing optional lateral/time data, missing primary measurements, invalid geometry, loading reversals and smoothing limits.
- Width-based Poisson calculation and separately supplied ductility dimensions.
- Replicate grouping and explicitly selected upper/lower yield rows.
- CSV, decimal-comma CSV, XLSX sheet selection and analysis snapshot reopening.
- Original input precision preserved through JSON export, restore and re-analysis.
- HTML, PDF, PNG, SVG, CSV and JSON outputs, including three-language report paths.
- Translation-key parity, explicit interface keys and local-origin request restriction.

## Browser checks

Passed with Chromium 133 controlled by Playwright in the development environment. No JavaScript page errors were recorded.

- All six combinations of three languages and two themes, with numerical-result equality before and after changes.
- Mouse selection of the elastic interval followed by recalculation.
- Overview, elastic, advanced, comparison and export views.
- Two-repeat comparison and grouped statistics.
- JSON download, restore and a fresh analysis.
- Incomplete-test behaviour and XLSX upload.
- A 390 px layout with no document-level horizontal overflow.

The files in `docs/screenshots/` are actual browser captures. They are not generated interface mockups.

For optional browser checks on another machine, Node.js is only a development dependency:

```bash
npm install
npx playwright install chromium
npm run test:browser
```

The browser test uses `.venv/bin/python`; set `TENSILE_PYTHON` if your environment is elsewhere. It temporarily starts the local server and rewrites the example screenshots.

## Document check

Generated PDF output was rendered and visually reviewed for character support, the complete property table, translated settings and page numbers.

## Limits of this record

This is synthetic-data and software validation. No independently reviewed laboratory dataset has been used. The environment was Linux; a separate macOS test run is not recorded. The MATLAB script was prepared and reviewed but not run, because MATLAB is unavailable here. No completed MATLAB validation, macOS validation or hosted GitHub Actions result is claimed.
