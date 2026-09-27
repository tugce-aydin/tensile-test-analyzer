from pathlib import Path
from io import BytesIO
from collections import OrderedDict
import json
import secrets
import zipfile
import webbrowser
from threading import Timer
import argparse
from urllib.parse import urlparse
import pandas as pd
from flask import Flask, request, jsonify, render_template, send_file
from tensile.analysis import analyze, compare, finite, AnalysisError
from tensile.reporting import html_report, pdf_report, chart

ROOT = Path(__file__).resolve().parent
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 80 * 1024 * 1024
DATA = OrderedDict()


def remember(df, name, source="user", sheets=None):
    if len(df) > 100000:
        raise AnalysisError("file_too_large")
    key = secrets.token_urlsafe(18)
    DATA[key] = (df, name, source)
    while len(DATA) > 30:
        DATA.popitem(last=False)
    return {
        "id": key,
        "name": name,
        "source": source,
        "columns": list(map(str, df.columns)),
        "rows": len(df),
        "preview": finite(
            df.head(6).where(pd.notnull(df), None).to_dict(orient="records")
        ),
        "sheets": sheets or [],
    }


@app.before_request
def local_requests():
    origin = request.headers.get("Origin")
    if request.method == "POST" and origin and urlparse(origin).netloc != request.host:
        return jsonify(error="request_error"), 403


@app.errorhandler(AnalysisError)
def bad_analysis(err):
    return jsonify(error=err.code), 400


@app.errorhandler(413)
def large_file(err):
    return jsonify(error="file_too_large"), 413


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/examples")
def examples():
    return jsonify(json.loads((ROOT / "data" / "manifest.json").read_text()))


@app.post("/api/example")
def example():
    name = request.json.get("name", "reference")
    valid = {v["id"] for v in json.loads((ROOT / "data" / "manifest.json").read_text())}
    if name not in valid:
        raise AnalysisError("invalid_file")
    return jsonify(
        remember(pd.read_csv(ROOT / "data" / f"{name}.csv"), name, "synthetic")
    )


@app.post("/api/upload")
def upload():
    f = request.files.get("file")
    if not f:
        raise AnalysisError("invalid_file")
    try:
        raw = f.read()
        suffix = Path(f.filename).suffix.lower()
        sheets = []
        if len(raw) > 10 * 1024 * 1024:
            raise AnalysisError("file_too_large")
        if suffix == ".xlsx":
            with zipfile.ZipFile(BytesIO(raw)) as z:
                if sum(v.file_size for v in z.infolist()) > 100 * 1024 * 1024:
                    raise AnalysisError("file_too_large")
            book = pd.ExcelFile(BytesIO(raw), engine="openpyxl")
            sheets = book.sheet_names
            sheet = request.form.get("sheet") or sheets[0]
            df = pd.read_excel(book, sheet_name=sheet)
        elif suffix == ".csv":
            text = raw.decode("utf-8-sig")
            decimal = request.form.get("decimal", ".")
            df = pd.read_csv(
                BytesIO(text.encode()), sep=None, engine="python", decimal=decimal
            )
        else:
            raise AnalysisError("invalid_file")
        df.columns = df.columns.astype(str)
        if df.columns.duplicated().any():
            raise AnalysisError("invalid_file")
        return jsonify(remember(df, Path(f.filename).stem, sheets=sheets))
    except AnalysisError:
        raise
    except Exception:
        raise AnalysisError("invalid_file")


@app.post("/api/analyze")
def run_analysis():
    data = request.get_json()
    key = data.get("id")
    if key not in DATA:
        raise AnalysisError("session_expired")
    df, name, source = DATA[key]
    config = data.get("settings", {})
    config["source"] = source
    return jsonify(analyze(df, config))


@app.post("/api/restore")
def restore():
    r = request.json
    try:
        df = pd.DataFrame(r["input_data"]["data"], columns=r["input_data"]["columns"])
        return jsonify(
            remember(
                df, r["settings"]["sample_name"], r["settings"].get("source", "user")
            )
        )
    except (KeyError, ValueError, TypeError):
        raise AnalysisError("invalid_file")


@app.post("/api/compare")
def comparisons():
    values = request.json.get("results", [])
    if len(values) > 30:
        raise AnalysisError("invalid_settings")
    return jsonify(compare(values))


@app.post("/api/export/<kind>")
def export(kind):
    payload = request.get_json()
    r = payload["result"]
    lang = payload.get("lang", "en")
    if kind == "json":
        content = json.dumps(r, ensure_ascii=False, indent=2).encode()
        mime = "application/json"
    elif kind == "csv":
        content = (
            pd.DataFrame(
                r["series"]
                | {
                    k: [*v, *([None] * (len(r["series"]["strain"]) - len(v)))]
                    for k, v in r["series"].items()
                }
            )
            .to_csv(index=False)
            .encode("utf-8-sig")
        )
        mime = "text/csv"
    elif kind == "html":
        content = html_report(r, lang).encode()
        mime = "text/html"
    elif kind == "pdf":
        content = pdf_report(r, lang)
        mime = "application/pdf"
    elif kind in ["png", "svg"]:
        content = chart(r, lang, kind)
        mime = "image/png" if kind == "png" else "image/svg+xml"
    else:
        raise AnalysisError("invalid_file")
    return send_file(
        BytesIO(content),
        mimetype=mime,
        as_attachment=True,
        download_name=f"tensile-analysis.{kind}",
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-browser", action="store_true")
    args = p.parse_args()
    if not args.no_browser:
        Timer(1.2, lambda: webbrowser.open(f"http://127.0.0.1:{args.port}")).start()
    app.run(host="127.0.0.1", port=args.port, debug=False)
