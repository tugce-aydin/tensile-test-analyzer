from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def generate():
    entries = []
    for name, E, y, uts, nu, noise, seed in [
        ("reference", 200000, 250, 450, 0.30, 0, 21),
        ("noisy", 200000, 250, 450, 0.30, 1.3, 22),
        ("replicate", 200000, 250, 450, 0.30, 0.5, 23),
        ("aluminium_model", 70000, 160, 310, 0.33, 0, 24),
    ]:
        ey = y / E
        ep = 0.15
        end = 0.25
        e = np.unique(
            np.r_[
                np.linspace(0, ey, 90),
                np.linspace(ey, ep, 550),
                np.linspace(ep, end, 240),
                0.2505,
                0.251,
            ]
        )
        s = np.empty_like(e)
        elastic = e <= ey
        hard = (e > ey) & (e <= ep)
        neck = (e > ep) & (e <= end)
        s[elastic] = E * e[elastic]
        s[hard] = y + (uts - y) * np.sin(np.pi / 2 * (e[hard] - ey) / (ep - ey))
        s[neck] = uts * (1 - 1 / 3 * ((e[neck] - ep) / (end - ep)) ** 1.5)
        s[e > end] = 0
        if noise:
            s += np.random.default_rng(seed).normal(0, noise, len(e))
            s[0] = 0
            s[e > end] = 0
        axial_elastic = s / E
        lateral = -nu * axial_elastic - 0.5 * np.maximum(0, e - axial_elastic)
        df = pd.DataFrame(
            {
                "time_s": e / 0.001,
                "force_N": s * 10,
                "extension_mm": e * 50,
                "transverse_strain": lateral,
            }
        )
        df.to_csv(ROOT / "data" / f"{name}.csv", index=False, float_format="%.10g")
        entries.append(
            {
                "id": name,
                "file": f"{name}.csv",
                "E_GPa": E / 1000,
                "nominal_yield_MPa": y,
                "UTS_MPa": uts,
                "poisson": nu,
                "noise_MPa": noise,
                "seed": seed,
                "source": "synthetic",
                "area_mm2": 10,
                "gauge_length_mm": 50,
                "fracture_strain": 0.25,
                "elastic_limit_MPa": y,
            }
        )
    e = np.r_[np.linspace(0, 0.004, 250), 0.00402]
    s = np.r_[70000 * e[:-1], 0]
    pd.DataFrame(
        {"time_s": e / 0.0001, "force_N": s * 10, "extension_mm": e * 50}
    ).to_csv(ROOT / "data" / "brittle.csv", index=False)
    entries.append(
        {
            "id": "brittle",
            "file": "brittle.csv",
            "E_GPa": 70,
            "UTS_MPa": 280,
            "source": "synthetic",
            "area_mm2": 10,
            "gauge_length_mm": 50,
            "fracture_strain": 0.004,
            "elastic_limit_MPa": 280,
        }
    )
    reference = pd.read_csv(ROOT / "data" / "reference.csv")
    reference.iloc[:350].to_csv(ROOT / "data" / "incomplete.csv", index=False)
    entries.append(
        {
            "id": "incomplete",
            "file": "incomplete.csv",
            "source": "synthetic",
            "complete": False,
            "area_mm2": 10,
            "gauge_length_mm": 50,
        }
    )
    reference.to_excel(ROOT / "data" / "reference.xlsx", index=False, sheet_name="Test")
    pd.DataFrame(
        {
            "stress_MPa": reference.force_N / 10,
            "strain_percent": reference.extension_mm / 50 * 100,
        }
    ).to_csv(ROOT / "data" / "direct_stress.csv", index=False)
    (ROOT / "data" / "manifest.json").write_text(
        json.dumps(entries, indent=2), encoding="utf8"
    )


if __name__ == "__main__":
    generate()
