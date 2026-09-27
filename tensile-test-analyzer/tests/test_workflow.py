import io
import json
import re
from pathlib import Path
import pandas as pd
import pytest
from app import app
from tensile.analysis import analyze

ROOT = Path(__file__).resolve().parents[1]


def test_snapshot_reanalyzes_original_data():
    c = app.test_client()
    key = c.post("/api/example", json={"name": "noisy"}).json["id"]
    first = c.post(
        "/api/analyze",
        json={"id": key, "settings": {"complete": True, "smoothing": 7, "zero": True}},
    ).json
    restored = c.post("/api/restore", json=first)
    assert restored.status_code == 200
    again = c.post(
        "/api/analyze", json={"id": restored.json["id"], "settings": first["settings"]}
    ).json
    assert again["metrics"] == first["metrics"]


def test_upper_lower_confirmation():
    d = pd.read_csv(ROOT / "data" / "reference.csv")
    r = analyze(d, {"yield_upper_row": 100, "yield_lower_row": 101})
    assert r["metrics"]["upper_yield_MPa"] == pytest.approx(d.force_N.iloc[100] / 10)
    assert r["metrics"]["lower_yield_MPa"] == pytest.approx(d.force_N.iloc[101] / 10)


def test_upload_decimal_comma_and_sheet_selection():
    c = app.test_client()
    d = pd.read_csv(ROOT / "data" / "reference.csv")
    csv = d.to_csv(index=False, sep=";", decimal=",").encode()
    r = c.post(
        "/api/upload", data={"file": (io.BytesIO(csv), "comma.csv"), "decimal": ","}
    )
    assert r.status_code == 200
    a = c.post("/api/analyze", json={"id": r.json["id"], "settings": {}})
    assert a.json["metrics"]["E_GPa"] == pytest.approx(200)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        d.to_excel(w, index=False, sheet_name="first")
        (d * 2).to_excel(w, index=False, sheet_name="second")
    r = c.post(
        "/api/upload",
        data={"file": (io.BytesIO(buf.getvalue()), "book.xlsx"), "sheet": "second"},
    )
    assert r.status_code == 200 and len(r.json["sheets"]) == 2


def test_late_start_is_partial_even_when_fracture_confirmed():
    d = pd.read_csv(ROOT / "data" / "reference.csv")
    r = analyze(d, {"start_row": 20, "complete": True})
    assert r["metrics"]["toughness_MJ_m3"] is None


def test_limit_estimate_is_labelled():
    d = pd.read_csv(ROOT / "data" / "reference.csv")
    r = analyze(d)
    assert r["resilience_kind"] == "proof_estimate"
    assert "resilience_estimate" in r["warnings"]


def test_local_origin_guard():
    c = app.test_client()
    r = c.post(
        "/api/example",
        json={"name": "reference"},
        headers={"Origin": "https://unrelated.example"},
    )
    assert r.status_code == 403


def test_explicit_markup_keys_exist():
    keys = set(json.loads((ROOT / "static/locales/en.json").read_text()))
    markup = (ROOT / "templates/index.html").read_text()
    assert set(re.findall(r'data-i18n="([^"]+)"', markup)) <= keys
    script = (ROOT / "static/app.js").read_text()
    assert set(re.findall(r"\bt\('([^']+)'\)", script)) <= keys
