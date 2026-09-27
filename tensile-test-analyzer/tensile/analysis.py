from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd
from scipy.signal import savgol_filter, find_peaks
from scipy.stats import linregress


class AnalysisError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass
class Settings:
    mode: str = "force"
    force_column: str = "force_N"
    extension_column: str = "extension_mm"
    stress_column: str = "stress_MPa"
    strain_column: str = "strain"
    time_column: str = "time_s"
    lateral_column: str = "transverse_strain"
    force_unit: str = "N"
    length_unit: str = "mm"
    stress_unit: str = "MPa"
    strain_unit: str = "ratio"
    lateral_unit: str = "ratio"
    lateral_kind: str = "strain"
    initial_width: float = 10.0
    geometry: str = "area"
    area: float = 10.0
    width: float = 5.0
    thickness: float = 2.0
    diameter: float = 3.568248232
    gauge_length: float = 50.0
    final_length: float | None = None
    final_area: float | None = None
    measurement: str = "extensometer"
    material: str = ""
    temperature: float = 23.0
    source: str = "user"
    sample_name: str = "Sample"
    group: str = ""
    start_row: int = 0
    end_row: int | None = None
    zero: bool = False
    smoothing: int = 0
    elastic_min: float = 0.0001
    elastic_max: float = 0.0009
    auto_elastic: bool = True
    fracture_row: int | None = None
    complete: bool = False
    yield_upper_row: int | None = None
    yield_lower_row: int | None = None
    elastic_limit: float | None = None
    hardening_min: float = 0.002
    hardening_max: float = 0.15
    area_uncertainty: float = 1.0
    length_uncertainty: float = 1.0

    @classmethod
    def from_dict(cls, data):
        keys = cls.__dataclass_fields__
        obj = cls(**{k: v for k, v in data.items() if k in keys})
        for key in [
            "area",
            "width",
            "thickness",
            "diameter",
            "gauge_length",
            "initial_width",
            "elastic_min",
            "elastic_max",
            "hardening_min",
            "hardening_max",
            "area_uncertainty",
            "length_uncertainty",
            "temperature",
        ]:
            try:
                val = float(getattr(obj, key))
                if not np.isfinite(val):
                    raise ValueError
                setattr(obj, key, val)
            except (TypeError, ValueError):
                raise AnalysisError("invalid_settings")
        for key in ["final_length", "final_area", "elastic_limit"]:
            if getattr(obj, key) is not None:
                try:
                    value = float(getattr(obj, key))
                    if not np.isfinite(value):
                        raise ValueError
                    setattr(obj, key, value)
                except (TypeError, ValueError):
                    raise AnalysisError("invalid_settings")
        return obj


def finite(value):
    if isinstance(value, dict):
        return {k: finite(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [finite(v) for v in value]
    if isinstance(value, np.ndarray):
        return finite(value.tolist())
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    return value


def section(c):
    if min(c.gauge_length, c.initial_width) <= 0:
        raise AnalysisError("invalid_geometry")
    if c.geometry == "rectangle":
        a = c.width * c.thickness if min(c.width, c.thickness) > 0 else 0
    elif c.geometry == "circle":
        a = np.pi * c.diameter**2 / 4 if c.diameter > 0 else 0
    elif c.geometry == "area":
        a = c.area
    else:
        raise AnalysisError("invalid_geometry")
    if a <= 0:
        raise AnalysisError("invalid_geometry")
    if c.final_length is not None and c.final_length < c.gauge_length:
        raise AnalysisError("invalid_geometry")
    if c.final_area is not None and not 0 < c.final_area <= a:
        raise AnalysisError("invalid_geometry")
    return a


def column(df, key, required=True):
    if key not in df:
        if required:
            raise AnalysisError("missing_columns")
        return np.full(len(df), np.nan)
    return pd.to_numeric(df[key], errors="coerce").to_numpy(dtype=float)


def fit(x, y):
    if len(x) < 5 or np.ptp(x) <= 0:
        raise AnalysisError("elastic_points")
    r = linregress(x, y)
    return {
        "slope": r.slope,
        "intercept": r.intercept,
        "r2": r.rvalue**2,
        "stderr": r.stderr,
        "n": len(x),
    }


def elastic_proposal(e, s):
    ceiling = min(0.001, np.max(e) * 0.2)
    candidates = []
    for lo, hi in [(0.0001, ceiling), (0.00005, ceiling * 0.8), (0, ceiling * 0.6)]:
        m = (e >= lo) & (e <= hi)
        if m.sum() >= 8:
            f = fit(e[m], s[m])
            if f["slope"] > 0:
                candidates.append((f["r2"], lo, hi))
    if not candidates:
        raise AnalysisError("elastic_points")
    _, lo, hi = max(candidates)
    return lo, hi


def analyze(df, config=None):
    c = Settings.from_dict(config or {})
    a = section(c)
    if not 0 <= c.area_uncertainty < 50 or not 0 <= c.length_uncertainty < 50:
        raise AnalysisError("invalid_settings")
    if c.mode not in ["force", "stress"]:
        raise AnalysisError("invalid_settings")
    if c.lateral_kind not in ["strain", "width"]:
        raise AnalysisError("invalid_settings")
    if c.lateral_kind == "width" and c.lateral_unit != "mm":
        raise AnalysisError("invalid_units")
    if c.lateral_kind == "strain" and c.lateral_unit == "mm":
        raise AnalysisError("invalid_units")
    warnings = []
    start = int(c.start_row or 0)
    stop = len(df) if c.end_row is None else int(c.end_row) + 1
    if start < 0 or stop > len(df) or stop <= start:
        raise AnalysisError("invalid_range")
    part = df.iloc[start:stop]
    rows = np.arange(start, stop)
    try:
        if c.mode == "force":
            f = column(part, c.force_column) * {"N": 1, "kN": 1000}[c.force_unit]
            extension = (
                column(part, c.extension_column)
                * {"mm": 1, "m": 1000, "um": 0.001}[c.length_unit]
            )
            s = f / a
            e = extension / c.gauge_length
        else:
            s = (
                column(part, c.stress_column)
                * {"MPa": 1, "Pa": 1e-6, "GPa": 1000}[c.stress_unit]
            )
            e = (
                column(part, c.strain_column)
                * {"ratio": 1, "percent": 0.01, "microstrain": 1e-6}[c.strain_unit]
            )
            f = s * a
            extension = e * c.gauge_length
        lateral = (
            column(part, c.lateral_column, False)
            * {"ratio": 1, "percent": 0.01, "microstrain": 1e-6, "mm": 1}[
                c.lateral_unit
            ]
        )
    except KeyError:
        raise AnalysisError("invalid_units")
    if c.lateral_kind == "width":
        lateral = (lateral - c.initial_width) / c.initial_width
    time = column(part, c.time_column, False)
    valid = np.isfinite(s) & np.isfinite(e)
    dropped = int((~valid).sum())
    if dropped:
        warnings.append("missing_removed")
    e, s, f, extension, lateral, time, rows = [
        v[valid] for v in [e, s, f, extension, lateral, time, rows]
    ]
    if len(e) < 12:
        raise AnalysisError("too_few_points")
    original_s = s.copy()
    original_e = e.copy()
    if c.zero:
        s = s - s[0]
        e = e - e[0]
        f = s * a
        extension = e * c.gauge_length
        if np.isfinite(lateral[0]):
            lateral = lateral - lateral[0]
        warnings.append("zero_applied")
    if np.min(e) < -1e-8 or np.max(s) <= 0:
        raise AnalysisError("negative_data")
    if np.any(np.diff(e) < -max(1e-6, np.ptp(e) * 0.0001)):
        raise AnalysisError("nonmonotonic")
    if np.any(np.diff(e) < 0):
        warnings.append("strain_noise")
    dup = int(pd.DataFrame({"e": e, "s": s}).duplicated().sum())
    if dup:
        warnings.append("duplicates")
    candidate = None
    drops = np.where((s[:-1] > 0.25 * np.max(s)) & (s[1:] < 0.5 * s[:-1]))[0]
    if len(drops):
        candidate = int(drops[-1])
    if c.fracture_row is not None:
        idx = np.where(rows == int(c.fracture_row))[0]
        if not len(idx):
            raise AnalysisError("invalid_fracture")
        fracture = int(idx[0])
        confirmed = True
    else:
        fracture = candidate if candidate is not None else len(e) - 1
        confirmed = bool(c.complete)
        if not confirmed:
            warnings.append(
                "fracture_candidate"
                if candidate is not None
                else "fracture_unconfirmed"
            )
    if fracture < 10:
        raise AnalysisError("invalid_fracture")
    raw_stress = s.copy()
    win = int(c.smoothing or 0)
    if win:
        if win < 5 or win % 2 == 0 or win >= fracture:
            raise AnalysisError("invalid_smoothing")
        s[: fracture + 1] = savgol_filter(s[: fracture + 1], win, 2)
        warnings.append("smoothed")
    ef = e[: fracture + 1]
    sf = s[: fracture + 1]
    if c.auto_elastic:
        c.elastic_min, c.elastic_max = elastic_proposal(ef, sf)
    if c.elastic_min >= c.elastic_max:
        raise AnalysisError("invalid_range")
    mask = (ef >= c.elastic_min) & (ef <= c.elastic_max)
    elastic = fit(ef[mask], sf[mask])
    E = elastic["slope"]
    b = elastic["intercept"]
    if E <= 0:
        raise AnalysisError("invalid_modulus")
    if elastic["r2"] < 0.995:
        warnings.append("poor_elastic_fit")
    if abs(b) > max(2, np.max(sf) * 0.01):
        warnings.append("offset_intercept")
    if c.measurement == "crosshead":
        warnings.append("warn_crosshead")
    peak = int(np.argmax(sf))
    if peak == len(sf) - 1:
        warnings.append("no_necking_evidence")
    offset = E * (ef - 0.002) + b
    diff = sf - offset
    crossings = np.where((diff[:-1] >= 0) & (diff[1:] < 0) & (ef[1:] >= 0.002))[0]
    proof = None
    if len(crossings):
        k = int(crossings[0])
        t = diff[k] / (diff[k] - diff[k + 1])
        xp = ef[k] + t * (ef[k + 1] - ef[k])
        yp = sf[k] + t * (sf[k + 1] - sf[k])
        proof = {"strain": xp, "stress": yp}
    else:
        warnings.append("no_proof")
    energy = float(np.trapezoid(sf, ef))
    complete = confirmed and ef[0] <= 1e-5 and abs(sf[0]) < max(2, sf.max() * 0.01)
    if not complete:
        warnings.append("partial_energy")
    if c.elastic_limit is not None:
        if not 0 < c.elastic_limit <= np.max(sf):
            raise AnalysisError("invalid_elastic_limit")
        resilience = c.elastic_limit**2 / (2 * E)
        resilience_kind = "specified_limit"
    elif proof:
        resilience = proof["stress"] ** 2 / (2 * E)
        resilience_kind = "proof_estimate"
        warnings.append("resilience_estimate")
    else:
        resilience = None
        resilience_kind = "unavailable"
    lm = mask & np.isfinite(lateral[: fracture + 1])
    poisson = None
    if lm.sum() >= 5:
        pf = fit(ef[lm], lateral[: fracture + 1][lm])
        poisson = {**pf, "value": -pf["slope"]}
        if not -1 < poisson["value"] < 0.5:
            warnings.append("poisson_check")
    else:
        warnings.append("no_lateral")
    # Local area is needed once deformation is no longer uniform.
    true_e = np.log1p(ef[: peak + 1])
    true_s = sf[: peak + 1] * (1 + ef[: peak + 1])
    plastic = true_e - true_s / E
    hm = (plastic >= c.hardening_min) & (plastic <= c.hardening_max) & (true_s > 0)
    hardening = None
    if hm.sum() >= 8 and np.ptp(plastic[hm]) > 0:
        hf = fit(np.log(plastic[hm]), np.log(true_s[hm]))
        hardening = {
            "n": hf["slope"],
            "K_MPa": np.exp(hf["intercept"]),
            "r2": hf["r2"],
            "points": int(hm.sum()),
        }
    else:
        warnings.append("no_hardening")
    rate = np.full(len(ef), np.nan)
    if np.all(np.isfinite(time[: fracture + 1])) and np.all(
        np.diff(time[: fracture + 1]) > 0
    ):
        rate = np.gradient(ef, time[: fracture + 1])
    else:
        warnings.append("no_time")
    yield_candidates = []
    yp, _ = find_peaks(sf, prominence=max(5, 0.015 * np.max(sf)))
    for k in yp:
        if c.elastic_max < ef[k] < min(0.03, ef[peak]):
            end = min(peak, np.searchsorted(ef, ef[k] + 0.01))
            if end > k + 2:
                low = k + 1 + int(np.argmin(sf[k + 1 : end + 1]))
                yield_candidates.append(
                    {
                        "upper_row": int(rows[k]),
                        "upper_MPa": sf[k],
                        "lower_row": int(rows[low]),
                        "lower_MPa": sf[low],
                    }
                )
    confirmed_yield = {}
    for label, row in [
        ("upper_yield_MPa", c.yield_upper_row),
        ("lower_yield_MPa", c.yield_lower_row),
    ]:
        if row is not None:
            pos = np.where(rows[: fracture + 1] == int(row))[0]
            if not len(pos):
                raise AnalysisError("invalid_range")
            confirmed_yield[label] = float(sf[pos[0]])
        else:
            confirmed_yield[label] = None
    ea = ef[mask]
    range_checks = []
    for trim in [0, 0.1, 0.2]:
        lo = np.min(ea) + np.ptp(ea) * trim
        hi = np.max(ea) - np.ptp(ea) * trim
        m = (ef >= lo) & (ef <= hi)
        if m.sum() >= 5:
            range_checks.append(
                {"trim_percent": trim * 100, "E_GPa": fit(ef[m], sf[m])["slope"] / 1000}
            )
    metrics = {
        "E_GPa": E / 1000,
        "proof_MPa": proof["stress"] if proof else None,
        "UTS_MPa": sf[peak],
        "max_force_N": sf[peak] * a if c.mode == "force" else None,
        "uniform_strain_percent": ef[peak] * 100,
        "fracture_stress_MPa": sf[-1] if confirmed else None,
        "fracture_strain_percent": ef[-1] * 100 if confirmed else None,
        "elongation_percent": (c.final_length / c.gauge_length - 1) * 100
        if c.final_length is not None
        else None,
        "reduction_percent": (1 - c.final_area / a) * 100
        if c.final_area is not None
        else None,
        "resilience_MJ_m3": resilience,
        "toughness_MJ_m3": energy if complete else None,
        "recorded_energy_MJ_m3": energy,
        "poisson": poisson["value"] if poisson else None,
        "hardening_n": hardening["n"] if hardening else None,
        "hardening_K_MPa": hardening["K_MPa"] if hardening else None,
        "mean_rate_s": np.mean(rate) if np.isfinite(rate).all() else None,
    }
    metrics.update(confirmed_yield)
    ua = c.area_uncertainty / 100
    ul = c.length_uncertainty / 100
    sensitivity = {
        "E_GPa_low": E / 1000 * ((1 - ul) / (1 + ua) if c.mode == "force" else 1),
        "E_GPa_high": E / 1000 * ((1 + ul) / (1 - ua) if c.mode == "force" else 1),
        "UTS_MPa_low": sf[peak] / (1 + ua) if c.mode == "force" else sf[peak],
        "UTS_MPa_high": sf[peak] / (1 - ua) if c.mode == "force" else sf[peak],
        "elastic_ranges": range_checks,
    }
    return finite(
        {
            "input_data": df.astype(object)
            .where(pd.notna(df), None)
            .to_dict(orient="split", index=False),
            "settings": asdict(c),
            "metrics": metrics,
            "warnings": list(dict.fromkeys(warnings)),
            "elastic": elastic,
            "proof": proof,
            "poisson_fit": poisson,
            "hardening": hardening,
            "yield_candidates": yield_candidates,
            "resilience_kind": resilience_kind,
            "sensitivity": sensitivity,
            "quality": {
                "input_rows": len(df),
                "used_rows": len(ef),
                "dropped_rows": dropped,
                "duplicates": dup,
                "area_mm2": a,
                "fracture_row": int(rows[fracture]),
                "fracture_confirmed": confirmed,
                "complete_energy": complete,
                "peak_row": int(rows[peak]),
            },
            "series": {
                "row": rows[: fracture + 1],
                "strain": ef,
                "stress": sf,
                "raw_stress": raw_stress[: fracture + 1],
                "force": f[: fracture + 1],
                "extension": extension[: fracture + 1],
                "time": time[: fracture + 1],
                "lateral": lateral[: fracture + 1],
                "rate": rate,
                "true_strain": true_e,
                "true_stress": true_s,
                "plastic_strain": plastic,
                "elastic_strain": sf / E,
                "permanent_strain": ef - sf / E,
            },
            "original": {"strain": original_e, "stress": original_s},
        }
    )


def compare(results):
    groups = {}
    for r in results:
        s = r["settings"]
        key = (
            s["group"] or s["sample_name"],
            s["material"],
            s["temperature"],
            s["gauge_length"],
            s["measurement"],
            s["source"],
        )
        groups.setdefault(key, []).append(r)
    out = []
    for key, items in groups.items():
        stats = {}
        for metric in items[0]["metrics"]:
            v = [
                r["metrics"][metric] for r in items if r["metrics"][metric] is not None
            ]
            stats[metric] = {
                "n": len(v),
                "mean": float(np.mean(v)) if v else None,
                "std": float(np.std(v, ddof=1)) if len(v) > 1 else None,
            }
        out.append(
            {
                "group": key[0],
                "conditions": key[1:],
                "count": len(items),
                "statistics": stats,
            }
        )
    return finite(out)
