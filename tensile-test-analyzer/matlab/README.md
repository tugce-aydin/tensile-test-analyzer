# Independent MATLAB calculation

`validate_reference.m` reads the same synthetic CSV as the Python application. It independently calculates Young's modulus, 0.2% proof stress, tensile strength, Poisson's ratio, resilience and tensile toughness, then compares them with the Python reference JSON.

Run in MATLAB (R2020a or later):

```matlab
cd('/path/to/tensile-test-analyzer/matlab')
summary = validate_reference;
```

The script uses `readtable`, `polyfit`, `trapz`, `tiledlayout` and `exportgraphics`. It requires base MATLAB; no additional toolbox is intended.

Outputs are written to `matlab/results/`: a numerical comparison CSV and a two-panel figure. The script stops with an assertion if relative differences exceed `1e-6`.

**Execution status:** prepared and reviewed, but not executed in MATLAB in the development environment. The checked-in JSON contains Python results only; it is not evidence of a completed MATLAB run. After running the script, keep its generated outputs if you want to document cross-language validation.
