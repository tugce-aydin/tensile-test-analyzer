from pathlib import Path
from io import BytesIO
import base64
import json
import html
import numpy as np
import matplotlib

matplotlib.use("Agg")
from matplotlib.figure import Figure
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parents[1]
UNITS = {
    "E_GPa": "GPa",
    "proof_MPa": "MPa",
    "UTS_MPa": "MPa",
    "max_force_N": "N",
    "uniform_strain_percent": "%",
    "fracture_stress_MPa": "MPa",
    "fracture_strain_percent": "%",
    "elongation_percent": "%",
    "reduction_percent": "%",
    "resilience_MJ_m3": "MJ/m³",
    "toughness_MJ_m3": "MJ/m³",
    "recorded_energy_MJ_m3": "MJ/m³",
    "poisson": "—",
    "hardening_n": "—",
    "hardening_K_MPa": "MPa",
    "mean_rate_s": "s⁻¹",
    "upper_yield_MPa": "MPa",
    "lower_yield_MPa": "MPa",
}
METHODS = [
    "method_intro",
    "method_elastic",
    "method_energy",
    "method_resilience",
    "method_true",
    "method_hardening",
    "method_poisson",
    "method_ductility",
]


def dictionary(lang):
    lang = lang if lang in ["tr", "en", "de"] else "en"
    return json.loads((ROOT / "static" / "locales" / f"{lang}.json").read_text())


def display(value, lang):
    t = dictionary(lang)
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return t[str(value).lower()]
    if isinstance(value, (int, float)):
        text = f"{value:.7g}"
        return text.replace(".", ",") if lang in ["tr", "de"] else text
    return t.get(str(value), str(value))


def setting_rows(result, lang):
    t = dictionary(lang)
    s = result["settings"]
    rows = []
    skip = set()
    if s["mode"] == "force":
        skip.update(["stress_column", "strain_column", "stress_unit", "strain_unit"])
    else:
        skip.update(["force_column", "extension_column", "force_unit", "length_unit"])
    skip.update(
        {
            "area": ["width", "thickness", "diameter"],
            "rectangle": ["area", "diameter"],
            "circle": ["area", "width", "thickness"],
        }[s["geometry"]]
    )
    if s["lateral_kind"] == "strain":
        skip.add("initial_width")
    for key, value in s.items():
        if key in skip:
            continue
        label = t.get("area_label" if key == "area" else key, key)
        if key == "mode":
            value = t[value + "_mode"]
        if key == "lateral_kind":
            value = t["lateral_width" if value == "width" else "lateral_strain"]
        rows.append((label, display(value, lang)))
    return rows


def chart(result, lang="en", format="png"):
    t = dictionary(lang)
    s = result["series"]
    fig = Figure(figsize=(9, 5), dpi=160)
    ax = fig.subplots()
    ax.plot(
        np.array(s["strain"]) * 100,
        s["raw_stress"],
        color="#9ca3af",
        lw=1,
        label=t["raw"],
    )
    ax.plot(
        np.array(s["strain"]) * 100,
        s["stress"],
        color="#077d89",
        lw=2,
        label=t["processed"],
    )
    ax.fill_between(
        np.array(s["strain"]) * 100, s["stress"], alpha=0.1, color="#077d89"
    )
    ax.set(
        xlabel=t["strain_axis"],
        ylabel=t["stress_axis"],
        title=result["settings"]["sample_name"],
    )
    if lang in ["tr", "de"]:
        formatter = FuncFormatter(lambda x, pos: f"{x:g}".replace(".", ","))
        ax.xaxis.set_major_formatter(formatter)
        ax.yaxis.set_major_formatter(formatter)
    ax.grid(alpha=0.2)
    ax.legend()
    fig.tight_layout()
    out = BytesIO()
    fig.savefig(out, format=format)
    return out.getvalue()


def html_report(result, lang="en"):
    lang = lang if lang in ["tr", "en", "de"] else "en"
    t = dictionary(lang)
    esc = html.escape
    rows = "".join(
        f"<tr><td>{esc(t[k])}</td><td>{esc(display(v, lang) if v is not None else t['not_available'])}</td><td>{UNITS[k]}</td></tr>"
        for k, v in result["metrics"].items()
    )
    notes = (
        "".join(f"<li>{esc(t.get(k, k))}</li>" for k in result["warnings"])
        or f"<li>{esc(t['no_notes'])}</li>"
    )
    img = base64.b64encode(chart(result, lang)).decode()
    method = "".join(f"<p>{esc(t[k])}</p>" for k in METHODS)
    settings = "".join(
        f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>"
        for k, v in setting_rows(result, lang)
    )
    return f'<!doctype html><html lang="{lang}"><meta charset="utf-8"><title>{esc(t["report_title"])}</title><style>body{{font:15px system-ui;max-width:950px;margin:40px auto;padding:20px;color:#173038}}h1{{font-size:28px}}table{{width:100%;border-collapse:collapse}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #ddd}}img{{width:100%}}li{{margin:6px 0}}</style><h1>{esc(t["report_title"])}</h1><p>{esc(result["settings"]["sample_name"])} · {esc(t.get(result["settings"]["source"], result["settings"]["source"]))}</p><img src="data:image/png;base64,{img}"><table><tr><th>{t["metric"]}</th><th>{t["value"]}</th><th>{t["unit"]}</th></tr>{rows}</table><h2>{t["review"]}</h2><ul>{notes}</ul><h2>{t["method"]}</h2>{method}<h2>{t["settings"]}</h2><table>{settings}</table></html>'


def pdf_report(result, lang="en"):
    t = dictionary(lang)
    font = "DejaVuSans"
    if font not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(font, font_manager.findfont("DejaVu Sans")))
    styles = getSampleStyleSheet()
    for st in styles.byName.values():
        st.fontName = font
    styles["BodyText"].fontSize = 9
    styles["BodyText"].leading = 12
    small = ParagraphStyle("small", fontName=font, fontSize=8, leading=11)
    out = BytesIO()
    doc = SimpleDocTemplate(
        out, rightMargin=38, leftMargin=38, topMargin=35, bottomMargin=40
    )
    subtitle = (
        result["settings"]["sample_name"]
        + " · "
        + t.get(result["settings"]["source"], result["settings"]["source"])
    )
    body = [
        Paragraph(html.escape(t["report_title"]), styles["Title"]),
        Paragraph(html.escape(subtitle), styles["BodyText"]),
        Spacer(1, 10),
        Image(BytesIO(chart(result, lang)), width=450, height=250),
    ]
    cells = [[t["metric"], t["value"], t["unit"]]]
    for k, v in result["metrics"].items():
        cells.append(
            [
                Paragraph(html.escape(t[k]), styles["BodyText"]),
                display(v, lang) if v is not None else t["not_available"],
                UNITS[k],
            ]
        )
    base = [
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5f1f1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#dddddd")),
    ]
    table = Table(cells, colWidths=[270, 140, 85], repeatRows=1)
    table.setStyle(TableStyle(base))
    body += [table, PageBreak(), Paragraph(t["review"], styles["Heading2"])]
    for k in result["warnings"]:
        body.append(Paragraph(html.escape(t.get(k, k)), styles["BodyText"]))
    if not result["warnings"]:
        body.append(Paragraph(t["no_notes"], styles["BodyText"]))
    body.append(Paragraph(t["method"], styles["Heading2"]))
    for k in METHODS:
        body.append(Paragraph(html.escape(t[k]), styles["BodyText"]))
    body.append(Paragraph(t["settings"], styles["Heading2"]))
    pairs = setting_rows(result, lang)
    cells = []
    for i in range(0, len(pairs), 2):
        parts = list(pairs[i]) + (
            list(pairs[i + 1]) if i + 1 < len(pairs) else ["", ""]
        )
        cells.append([Paragraph(html.escape(x), small) for x in parts])
    settings = Table(cells, colWidths=[160, 88, 160, 87])
    settings.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#e1e7e8")),
            ]
        )
    )
    body.append(settings)

    def footer(canvas, document):
        canvas.setFont(font, 8)
        canvas.setFillColor(colors.HexColor("#687b82"))
        canvas.drawString(38, 21, "Tensile Test Analyzer")
        canvas.drawRightString(557, 21, str(document.page))

    doc.build(body, onFirstPage=footer, onLaterPages=footer)
    return out.getvalue()
