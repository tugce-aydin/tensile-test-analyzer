import io
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from tensile.analysis import analyze, AnalysisError, compare
from app import app

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def reference():
    return pd.read_csv(ROOT / "data" / "reference.csv")


def test_reference_closed_form(reference):
    r = analyze(reference, {"complete": True, "elastic_limit": 250})
    m = r["metrics"]
    assert m["E_GPa"] == pytest.approx(200, rel=1e-8)
    assert m["UTS_MPa"] == 450
    assert m["poisson"] == pytest.approx(0.3, rel=1e-8)
    assert m["resilience_MJ_m3"] == pytest.approx(0.15625, rel=1e-8)
    analytic = (
        0.5 * 250 * 0.00125
        + 250 * (0.15 - 0.00125)
        + 200 * (0.15 - 0.00125) * 2 / np.pi
        + 450 * 0.1
        - 150 * 0.1 / 2.5
    )
    assert m["toughness_MJ_m3"] == pytest.approx(analytic, rel=1e-5)
    assert m["fracture_strain_percent"] == 25
    p = r["proof"]
    assert p["stress"] == pytest.approx(
        r["elastic"]["slope"] * (p["strain"] - 0.002) + r["elastic"]["intercept"],
        abs=1e-6,
    )
    assert len(r["series"]["true_strain"]) < len(r["series"]["strain"])
    assert r["series"]["true_strain"][-1] == pytest.approx(np.log1p(0.15))


def test_unit_invariance(reference):
    base = analyze(reference)["metrics"]
    copy = reference.copy()
    copy.force_N /= 1000
    copy.extension_mm /= 1000
    converted = analyze(copy, {"force_unit": "kN", "length_unit": "m"})["metrics"]
    for k in ["E_GPa", "proof_MPa", "UTS_MPa", "recorded_energy_MJ_m3"]:
        assert converted[k] == pytest.approx(base[k])
    direct = pd.DataFrame(
        {"stress": reference.force_N / 10, "percent": reference.extension_mm / 50 * 100}
    )
    r = analyze(
        direct,
        {
            "mode": "stress",
            "stress_column": "stress",
            "strain_column": "percent",
            "strain_unit": "percent",
        },
    )
    assert r["metrics"]["E_GPa"] == pytest.approx(200)
    assert r["metrics"]["max_force_N"] is None


def test_missing_transverse_time(reference):
    r = analyze(reference.drop(columns=["transverse_strain", "time_s"]))
    assert r["metrics"]["poisson"] is None
    assert r["metrics"]["mean_rate_s"] is None


def test_incomplete_is_not_toughness():
    r = analyze(pd.read_csv(ROOT / "data" / "incomplete.csv"))
    assert r["metrics"]["toughness_MJ_m3"] is None
    assert r["metrics"]["fracture_strain_percent"] is None
    assert r["metrics"]["recorded_energy_MJ_m3"] > 0


def test_brittle_has_no_offset():
    r = analyze(
        pd.read_csv(ROOT / "data" / "brittle.csv"),
        {"complete": True, "elastic_limit": 280},
    )
    assert r["metrics"]["proof_MPa"] is None
    assert r["metrics"]["E_GPa"] == pytest.approx(70)
    assert r["metrics"]["toughness_MJ_m3"] == pytest.approx(0.56)
    assert "no_necking_evidence" in r["warnings"]


@pytest.mark.parametrize(
    "settings,code",
    [
        ({"area": 0}, "invalid_geometry"),
        ({"gauge_length": -1}, "invalid_geometry"),
        (
            {"elastic_min": 0.1, "elastic_max": 0.01, "auto_elastic": False},
            "invalid_range",
        ),
        ({"smoothing": 4}, "invalid_smoothing"),
        ({"force_unit": "bad"}, "invalid_units"),
        ({"final_area": 11}, "invalid_geometry"),
    ],
)
def test_invalid_inputs(reference, settings, code):
    with pytest.raises(AnalysisError, match=code):
        analyze(reference, settings)


def test_monotonic_guard(reference):
    d = reference.copy()
    d.loc[200, "extension_mm"] = 0
    with pytest.raises(AnalysisError, match="nonmonotonic"):
        analyze(d)


def test_missing_primary_measurement(reference):
    d = reference.copy()
    d.loc[300, "force_N"] = np.nan
    r = analyze(d)
    assert r["quality"]["dropped_rows"] == 1
    assert r["metrics"]["E_GPa"] == pytest.approx(200)


def test_width_measurements(reference):
    d = reference.copy()
    d["width"] = 10 * (1 + d.transverse_strain)
    r = analyze(
        d, {"lateral_column": "width", "lateral_unit": "mm", "lateral_kind": "width"}
    )
    assert r["metrics"]["poisson"] == pytest.approx(0.3, rel=1e-7)


def test_ductility_and_geometry(reference):
    r = analyze(
        reference,
        {
            "geometry": "rectangle",
            "width": 5,
            "thickness": 2,
            "final_length": 60,
            "final_area": 6,
        },
    )
    assert r["metrics"]["elongation_percent"] == pytest.approx(20)
    assert r["metrics"]["reduction_percent"] == pytest.approx(40)
    assert r["metrics"]["E_GPa"] == pytest.approx(200)


def test_noise_smoothing_and_ranges():
    d = pd.read_csv(ROOT / "data" / "noisy.csv")
    r = analyze(
        d,
        {
            "smoothing": 7,
            "auto_elastic": False,
            "elastic_min": 0.0001,
            "elastic_max": 0.0009,
        },
    )
    assert r["metrics"]["E_GPa"] == pytest.approx(200, rel=0.025)
    assert r["series"]["raw_stress"] != r["series"]["stress"]
    assert len(r["sensitivity"]["elastic_ranges"]) == 3


def test_repeat_statistics(reference):
    a = analyze(reference, {"group": "M1", "material": "M1"})
    b = analyze(reference, {"group": "M1", "material": "M1"})
    c = analyze(reference, {"group": "M1", "material": "M1", "temperature": 100})
    groups = compare([a, b, c])
    assert len(groups) == 2
    assert groups[0]["statistics"]["E_GPa"]["std"] == 0


def test_api_and_reports(reference):
    client = app.test_client()
    up = client.post(
        "/api/upload",
        data={
            "file": (io.BytesIO(reference.to_csv(index=False).encode()), "sample.csv")
        },
        content_type="multipart/form-data",
    )
    assert up.status_code == 200
    response = client.post(
        "/api/analyze",
        json={
            "id": up.json["id"],
            "settings": {"complete": True, "elastic_limit": 250},
        },
    )
    assert response.status_code == 200
    r = response.json
    for lang in ["tr", "en", "de"]:
        for kind in ["csv", "json", "html", "pdf", "png", "svg"]:
            out = client.post("/api/export/" + kind, json={"result": r, "lang": lang})
            assert out.status_code == 200, (lang, kind, out.data[:100])
            assert len(out.data) > 50
            if kind == "pdf":
                assert out.data.startswith(b"%PDF")
    xlsx = client.post(
        "/api/upload",
        data={
            "file": (
                io.BytesIO((ROOT / "data" / "reference.xlsx").read_bytes()),
                "reference.xlsx",
            )
        },
    )
    assert xlsx.status_code == 200 and xlsx.json["sheets"] == ["Test"]


def test_translations_have_parity():
    dictionaries = [
        json.loads((ROOT / "static" / "locales" / f"{l}.json").read_text())
        for l in ["en", "tr", "de"]
    ]
    assert all(set(x) == set(dictionaries[0]) for x in dictionaries)
    assert all(all(isinstance(v, str) and v for v in x.values()) for x in dictionaries)
