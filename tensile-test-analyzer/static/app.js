"use strict";
const $ = (id) => document.getElementById(id);
const state = {
  lang: localStorage.getItem("tensile-language") || "en",
  theme: localStorage.getItem("tensile-theme") || "light",
  locales: {},
  dataset: null,
  result: null,
  comparisons: [],
  tab: "overview",
  file: null,
};
const units = {
  upper_yield_MPa: "MPa",
  lower_yield_MPa: "MPa",
  E_GPa: "GPa",
  proof_MPa: "MPa",
  UTS_MPa: "MPa",
  max_force_N: "N",
  uniform_strain_percent: "%",
  fracture_stress_MPa: "MPa",
  fracture_strain_percent: "%",
  elongation_percent: "%",
  reduction_percent: "%",
  resilience_MJ_m3: "MJ/m³",
  toughness_MJ_m3: "MJ/m³",
  recorded_energy_MJ_m3: "MJ/m³",
  poisson: "",
  hardening_n: "",
  hardening_K_MPa: "MPa",
  mean_rate_s: "s⁻¹",
};
const defaults = {
  mode: "force",
  force_column: "force_N",
  extension_column: "extension_mm",
  stress_column: "stress_MPa",
  strain_column: "strain",
  time_column: "time_s",
  lateral_column: "transverse_strain",
  force_unit: "N",
  length_unit: "mm",
  stress_unit: "MPa",
  strain_unit: "ratio",
  lateral_unit: "ratio",
  lateral_kind: "strain",
  initial_width: 10,
  geometry: "area",
  area: 10,
  width: 5,
  thickness: 2,
  diameter: 3.568248232,
  gauge_length: 50,
  final_length: null,
  final_area: null,
  measurement: "extensometer",
  sample_name: "Reference 01",
  material: "Model M1",
  temperature: 23,
  group: "M1",
  source: "synthetic",
  start_row: 0,
  end_row: null,
  zero: false,
  smoothing: 0,
  elastic_min: 0.0001,
  elastic_max: 0.0009,
  auto_elastic: true,
  fracture_row: null,
  yield_upper_row: null,
  yield_lower_row: null,
  complete: false,
  elastic_limit: null,
  hardening_min: 0.002,
  hardening_max: 0.15,
  area_uncertainty: 1,
  length_uncertainty: 1,
};
const t = (k) => state.locales[state.lang]?.[k] ?? k;
const number = (v, digits = 3) =>
  v === null || v === undefined
    ? "—"
    : new Intl.NumberFormat(
        state.lang === "tr" ? "tr-TR" : state.lang === "de" ? "de-DE" : "en-US",
        { maximumFractionDigits: digits },
      ).format(v);
function el(tag, text, cls) {
  const e = document.createElement(tag);
  if (text !== undefined) e.textContent = text;
  if (cls) e.className = cls;
  return e;
}
function error(key) {
  $("error").textContent = t(key);
  $("error").hidden = false;
  $("status").textContent = "";
}
async function api(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers:
      body instanceof FormData ? {} : { "Content-Type": "application/json" },
    body: body instanceof FormData ? body : JSON.stringify(body),
  });
  if (!res.ok) {
    let e;
    try {
      e = await res.json();
    } catch {
      e = { error: "request_error" };
    }
    throw Error(e.error || "request_error");
  }
  return res;
}
const groups = [
  [
    "sample",
    [
      ["sample_name", "sample", "text"],
      ["material", "material", "text"],
      ["group", "group", "text"],
      ["temperature", "temperature", "number"],
    ],
  ],
  [
    "mapping",
    [
      [
        "mode",
        "mode",
        [
          ["force", "force_mode"],
          ["stress", "stress_mode"],
        ],
      ],
      ["force_column", "force_column", "column"],
      ["extension_column", "extension_column", "column"],
      ["stress_column", "stress_column", "column"],
      ["strain_column", "strain_column", "column"],
      ["time_column", "time_column", "column"],
      ["lateral_column", "lateral_column", "column"],
      ["force_unit", "force_unit", ["N", "kN"]],
      ["length_unit", "length_unit", ["mm", "m", "um"]],
      ["stress_unit", "stress_unit", ["MPa", "GPa", "Pa"]],
      ["strain_unit", "strain_unit", ["ratio", "percent", "microstrain"]],
      [
        "lateral_kind",
        "lateral_kind",
        [
          ["strain", "lateral_strain"],
          ["width", "lateral_width"],
        ],
      ],
      [
        "lateral_unit",
        "lateral_unit",
        ["ratio", "percent", "microstrain", "mm"],
      ],
      ["initial_width", "initial_width", "number"],
    ],
  ],
  [
    "geometry_title",
    [
      ["geometry", "geometry", ["area", "rectangle", "circle"]],
      ["area", "area_label", "number"],
      ["width", "width", "number"],
      ["thickness", "thickness", "number"],
      ["diameter", "diameter", "number"],
      ["gauge_length", "gauge_length", "number"],
      ["final_length", "final_length", "number"],
      ["final_area", "final_area", "number"],
      ["measurement", "measurement", ["extensometer", "crosshead"]],
    ],
  ],
  [
    "preprocess",
    [
      ["start_row", "start_row", "number"],
      ["end_row", "end_row", "number"],
      ["zero", "zero", "checkbox"],
      ["smoothing", "smoothing", "number"],
      ["complete", "complete", "checkbox"],
      ["fracture_row", "fracture_row", "number"],
      ["yield_upper_row", "yield_upper_row", "number"],
      ["yield_lower_row", "yield_lower_row", "number"],
    ],
  ],
  [
    "fit_settings",
    [
      ["auto_elastic", "auto_elastic", "checkbox"],
      ["elastic_min", "elastic_min", "number"],
      ["elastic_max", "elastic_max", "number"],
      ["elastic_limit", "elastic_limit", "number"],
      ["hardening_min", "hardening_min", "number"],
      ["hardening_max", "hardening_max", "number"],
    ],
  ],
  [
    "uncertainty",
    [
      ["area_uncertainty", "area_uncertainty", "number"],
      ["length_uncertainty", "length_uncertainty", "number"],
    ],
  ],
];
function formValues() {
  let c = { ...defaults };
  groups.forEach(([, fields]) =>
    fields.forEach(([key, , type]) => {
      const e = $("f-" + key);
      if (!e) return;
      c[key] =
        type === "checkbox"
          ? e.checked
          : type === "number"
            ? e.value === ""
              ? null
              : Number(e.value)
            : e.value;
    }),
  );
  return c;
}
function buildForm(values = defaults) {
  const open = [...$("settingsForm").querySelectorAll("details[open]")].map(
    (d) => d.dataset.group,
  );
  $("settingsForm").replaceChildren();
  groups.forEach(([name, fields], i) => {
    const d = el("details");
    d.dataset.group = name;
    d.open = open.length ? open.includes(name) : i === 0;
    d.append(el("summary", t(name)));
    const grid = el("div", undefined, "form-grid");
    fields.forEach(([key, label, type]) => {
      const l = el(
        "label",
        undefined,
        type === "checkbox"
          ? "check-label full"
          : ["text", "column"].includes(type) || Array.isArray(type)
            ? "full"
            : "",
      );
      let input;
      if (type === "column" || Array.isArray(type)) {
        input = el("select");
        let opts =
          type === "column"
            ? [
                ["", t("none")],
                ...(state.dataset?.columns || [values[key]])
                  .filter(Boolean)
                  .map((x) => [x, x]),
              ]
            : type.map((x) => (Array.isArray(x) ? [x[0], t(x[1])] : [x, t(x)]));
        opts.forEach(([value, text]) => {
          const option = el("option", text);
          option.value = value;
          input.append(option);
        });
        input.value = values[key] ?? "";
      } else {
        input = el("input");
        input.type = type;
        if (type === "checkbox") input.checked = !!values[key];
        else {
          input.value = values[key] ?? "";
          if (type === "number") input.step = "any";
        }
      }
      input.id = "f-" + key;
      input.name = key;
      l.htmlFor = input.id;
      if (type === "checkbox") l.append(input, el("span", t(label)));
      else l.append(el("span", t(label)), input);
      grid.append(l);
    });
    d.append(grid);
    $("settingsForm").append(d);
  });
  $("f-mode").addEventListener("change", fieldVisibility);
  $("f-geometry").addEventListener("change", fieldVisibility);
  fieldVisibility();
}
function fieldVisibility() {
  const mode = $("f-mode").value,
    geo = $("f-geometry").value;
  ["force_column", "extension_column", "force_unit", "length_unit"].forEach(
    (k) => ($("f-" + k).parentElement.hidden = mode !== "force"),
  );
  ["stress_column", "strain_column", "stress_unit", "strain_unit"].forEach(
    (k) => ($("f-" + k).parentElement.hidden = mode !== "stress"),
  );
  ["area", "width", "thickness", "diameter"].forEach(
    (k) =>
      ($("f-" + k).parentElement.hidden = !(geo === "area"
        ? k === "area"
        : geo === "rectangle"
          ? ["width", "thickness"].includes(k)
          : k === "diameter")),
  );
}
function translate() {
  document.documentElement.lang = state.lang;
  document.title = t("app_title");
  document
    .querySelectorAll("[data-i18n]")
    .forEach((e) => (e.textContent = t(e.dataset.i18n)));
  $("language").value = state.lang;
  $("theme").value = state.theme;
  document.documentElement.dataset.theme = state.theme;
  $("methodText").replaceChildren(
    el("h2", t("method")),
    ...[
      "method_intro",
      "method_elastic",
      "method_energy",
      "method_resilience",
      "method_true",
      "method_hardening",
      "method_poisson",
      "method_ductility",
      "method_data",
      "method_compare",
    ].map((k) => el("p", t(k))),
  );
  for (const option of $("example").options)
    option.textContent = t(option.value);
  $("decimal").parentElement.firstChild.textContent = t("decimal") + " ";
}
function table(headers, rows) {
  const table = el("table"),
    head = el("thead"),
    tr = el("tr");
  headers.forEach((v) => tr.append(el("th", v)));
  head.append(tr);
  table.append(head);
  const body = el("tbody");
  rows.forEach((row) => {
    const tr = el("tr");
    row.forEach((v) => tr.append(el("td", v)));
    body.append(tr);
  });
  table.append(body);
  return table;
}
function renderMetrics() {
  if (!state.result) return;
  const r = state.result,
    m = r.metrics;
  $("metrics").replaceChildren();
  for (const k of ["E_GPa", "proof_MPa", "UTS_MPa", "toughness_MJ_m3"]) {
    const div = el("article", undefined, "metric-card");
    div.append(el("div", t(k), "metric-label"));
    const value = el("div", number(m[k], 2), "metric-value");
    value.append(el("small", m[k] === null ? "" : units[k]));
    div.append(
      value,
      el(
        "div",
        k === "E_GPa"
          ? `R² ${number(r.elastic.r2, 5)}`
          : k === "toughness_MJ_m3" && !r.quality.complete_energy
            ? t("partial_energy")
            : k === "proof_MPa"
              ? "Rp0.2"
              : k === "UTS_MPa"
                ? "Rm"
                : "",
        "metric-caption",
      ),
    );
    $("metrics").append(div);
  }
  $("sampleTitle").textContent = r.settings.sample_name;
  $("sourceBadge").textContent = t(r.settings.source);
  $("pointCount").textContent =
    `${number(r.quality.used_rows)} ${t("used_rows").toLowerCase()}`;
  $("quality").replaceChildren();
  for (const k of [
    "input_rows",
    "used_rows",
    "dropped_rows",
    "area_mm2",
    "peak_row",
    "fracture_row",
    "fracture_confirmed",
  ])
    $("quality").append(
      el("dt", t(k)),
      el(
        "dd",
        typeof r.quality[k] === "boolean"
          ? t(String(r.quality[k]))
          : number(r.quality[k]),
      ),
    );
  $("allMetrics").replaceChildren(
    table(
      [t("metric"), t("value"), t("unit")],
      Object.entries(m).map(([k, v]) => [
        t(k),
        v === null ? t("not_available") : number(v, 6),
        units[k],
      ]),
    ),
  );
  $("warnings").replaceChildren(...r.warnings.map((w) => el("li", t(w))));
  $("warningCount").textContent = `(${r.warnings.length})`;
  $("fitStats").replaceChildren(
    ...[
      `E = ${number(m.E_GPa, 4)} GPa`,
      `R² = ${number(r.elastic.r2, 6)}`,
      `b = ${number(r.elastic.intercept, 4)} MPa`,
      `n = ${r.elastic.n}`,
    ].map((x) => el("span", x)),
  );
  $("yieldCandidates").replaceChildren(
    r.yield_candidates.length
      ? table(
          [t("row"), t("upper_yield"), t("lower_yield")],
          r.yield_candidates.map((p) => [
            `${p.upper_row} / ${p.lower_row}`,
            number(p.upper_MPa),
            number(p.lower_MPa),
          ]),
        )
      : el("p", t("not_available"), "hint"),
  );
  const sens = r.sensitivity;
  $("sensitivity").replaceChildren(
    table(
      [t("metric"), t("range")],
      [
        [
          t("E_GPa"),
          `${number(sens.E_GPa_low)} – ${number(sens.E_GPa_high)} GPa`,
        ],
        [
          t("UTS_MPa"),
          `${number(sens.UTS_MPa_low)} – ${number(sens.UTS_MPa_high)} MPa`,
        ],
      ],
    ),
    table(
      [t("trim"), t("E_GPa")],
      sens.elastic_ranges.map((v) => [
        `${number(v.trim_percent)}%`,
        `${number(v.E_GPa, 5)} GPa`,
      ]),
    ),
  );
  const s = r.series;
  $("dataPreview").replaceChildren(
    table(
      [
        t("row"),
        t("axial_axis"),
        t("stress_axis"),
        t("force_axis"),
        t("extension_axis"),
      ],
      s.strain
        .slice(0, 20)
        .map((v, i) => [
          s.row[i],
          number(v, 7),
          number(s.stress[i], 5),
          number(s.force[i], 4),
          number(s.extension[i], 6),
        ]),
    ),
  );
}
function colors() {
  const c = getComputedStyle(document.documentElement);
  return {
    bg: c.getPropertyValue("--surface").trim(),
    text: c.getPropertyValue("--text").trim(),
    muted: c.getPropertyValue("--muted").trim(),
    grid: c.getPropertyValue("--border").trim(),
    accent: c.getPropertyValue("--accent").trim(),
    series: [
      "--accent",
      "--series2",
      "--series3",
      "--series4",
      "--series5",
      "--series6",
    ].map((x) => c.getPropertyValue(x).trim()),
  };
}
function plot(id, traces, xTitle, yTitle, extra = {}) {
  const c = colors();
  const layout = {
    paper_bgcolor: c.bg,
    plot_bgcolor: c.bg,
    font: { family: "Arial, sans-serif", size: 11, color: c.text },
    margin: { l: 62, r: 18, t: 20, b: 63 },
    xaxis: {
      title: { text: t(xTitle), standoff: 12 },
      gridcolor: c.grid,
      zerolinecolor: c.grid,
      automargin: true,
    },
    yaxis: {
      title: { text: t(yTitle), standoff: 10 },
      gridcolor: c.grid,
      zerolinecolor: c.grid,
      automargin: true,
    },
    legend: { orientation: "h", y: 1.17, x: 0, font: { size: 10 } },
    hovermode: "closest",
    colorway: c.series,
    showlegend: traces.length > 1,
    ...extra,
  };
  return Plotly.react(id, traces, layout, {
    responsive: true,
    displaylogo: false,
    modeBarButtonsToRemove: ["lasso2d", "select2d"],
    modeBarButtonsToAdd: [
      {
        name: t("svg_export"),
        icon: Plotly.Icons.camera,
        click: (graph) =>
          Plotly.downloadImage(graph, {
            format: "svg",
            filename: "tensile-chart",
          }),
      },
    ],
    toImageButtonOptions: {
      format: "png",
      filename: "tensile-chart",
      scale: 2,
    },
    locale: state.lang,
  });
}
function line(x, y, name, extra = {}) {
  return {
    x,
    y,
    name: t(name),
    type: "scatter",
    mode: "lines",
    line: { width: 2 },
    ...extra,
  };
}
function emptyChart(id, key = "not_available") {
  Plotly.purge(id);
  $(id).replaceChildren(el("div", t(key), "empty"));
}
function renderCharts() {
  if (!state.result) return;
  const r = state.result,
    s = r.series,
    m = r.metrics,
    c = colors();
  const x = s.strain.map((e) => e * 100);
  const peak = s.stress.indexOf(Math.max(...s.stress));
  if (state.tab === "overview") {
    const traces = [
      line(x, s.stress, "processed", {
        fill: "tozeroy",
        fillcolor:
          state.theme === "dark"
            ? "rgba(88,205,194,.08)"
            : "rgba(0,125,130,.07)",
      }),
    ];
    if (r.settings.smoothing)
      traces.unshift(
        line(x, s.raw_stress, "raw", { line: { color: c.muted, width: 1 } }),
      );
    traces.push({
      x: [x[peak]],
      y: [s.stress[peak]],
      type: "scatter",
      mode: "markers",
      marker: { size: 9, color: c.series[1] },
      name: t("peak"),
    });
    traces.push({
      x: [x.at(-1)],
      y: [s.stress.at(-1)],
      type: "scatter",
      mode: "markers",
      marker: { size: 8, symbol: "diamond", color: c.series[2] },
      name: t(r.quality.fracture_confirmed ? "fracture" : "candidate"),
    });
    plot("engineeringChart", traces, "strain_axis", "stress_axis");
    plot(
      "forceChart",
      [line(s.extension, s.force, "processed")],
      "extension_axis",
      "force_axis",
    );
  }
  if (state.tab === "elastic") {
    let ceiling = Math.max(
      r.settings.elastic_max * 1.8,
      r.proof ? r.proof.strain * 1.25 : 0.004,
    );
    ceiling = Math.min(ceiling, Math.max(...s.strain));
    const inds = s.strain
      .map((e, i) => (e <= ceiling ? i : -1))
      .filter((i) => i >= 0);
    const xe = inds.map((i) => x[i]);
    const ys = inds.map((i) => s.stress[i]);
    let end = ceiling;
    const fitXs = [r.settings.elastic_min, r.settings.elastic_max];
    let os = [0.002, Math.min(end, 0.002 + Math.max(...ys) / r.elastic.slope)];
    const tr = [
      line(xe, ys, "processed"),
      line(
        fitXs.map((e) => e * 100),
        fitXs.map((e) => r.elastic.slope * e + r.elastic.intercept),
        "fit",
        { line: { color: c.series[1], width: 3 } },
      ),
      line(
        os.map((e) => e * 100),
        os.map((e) => r.elastic.slope * (e - 0.002) + r.elastic.intercept),
        "offset",
        { line: { color: c.series[2], dash: "dash", width: 1.5 } },
      ),
    ];
    if (r.proof)
      tr.push({
        x: [r.proof.strain * 100],
        y: [r.proof.stress],
        mode: "markers",
        marker: { size: 8 },
        name: "Rp0.2",
      });
    if (r.metrics.resilience_MJ_m3 !== null) {
      const lim = r.settings.elastic_limit ?? r.metrics.proof_MPa;
      tr.unshift(
        line([0, (lim / r.elastic.slope) * 100], [0, lim], "resilience_MJ_m3", {
          fill: "tozeroy",
          fillcolor:
            state.theme === "dark"
              ? "rgba(237,184,128,.14)"
              : "rgba(191,135,84,.16)",
          line: { width: 0 },
        }),
      );
    }
    plot("elasticChart", tr, "strain_axis", "stress_axis", {
      dragmode: "select",
      selectdirection: "h",
    }).then(() => {
      const g = $("elasticChart");
      g.removeAllListeners("plotly_selected");
      g.on("plotly_selected", (ev) => {
        if (!ev?.range?.x) return;
        $("f-auto_elastic").checked = false;
        $("f-elastic_min").value = ev.range.x[0] / 100;
        $("f-elastic_max").value = ev.range.x[1] / 100;
        run();
      });
    });
    const em = s.strain
      .map((v, i) =>
        v >= r.settings.elastic_min && v <= r.settings.elastic_max ? i : -1,
      )
      .filter((v) => v >= 0);
    plot(
      "residualChart",
      [
        line(
          em.map((i) => x[i]),
          em.map(
            (i) =>
              s.stress[i] - r.elastic.slope * s.strain[i] - r.elastic.intercept,
          ),
          "residuals",
          { mode: "markers", marker: { size: 4 } },
        ),
      ],
      "strain_axis",
      "residual_axis",
    );
  }
  if (state.tab === "advanced") {
    plot(
      "trueChart",
      [line(s.true_strain, s.true_stress, "processed")],
      "true_strain_axis",
      "true_stress_axis",
    );
    if (r.hardening) {
      const inds = s.plastic_strain
        .map((e, i) =>
          e >= r.settings.hardening_min && e <= r.settings.hardening_max
            ? i
            : -1,
        )
        .filter((i) => i >= 0);
      const xp = inds.map((i) => s.plastic_strain[i]);
      plot(
        "hardeningChart",
        [
          line(
            xp,
            inds.map((i) => s.true_stress[i]),
            "processed",
            { mode: "markers", marker: { size: 3 } },
          ),
          line(
            xp,
            xp.map((e) => r.hardening.K_MPa * e ** r.hardening.n),
            "model_fit",
          ),
        ],
        "plastic_axis",
        "stress_axis",
      );
    } else emptyChart("hardeningChart");
    if (r.poisson_fit) {
      const inds = s.strain
        .map((v, i) =>
          v >= r.settings.elastic_min &&
          v <= r.settings.elastic_max &&
          s.lateral[i] !== null
            ? i
            : -1,
        )
        .filter((i) => i >= 0);
      const px = inds.map((i) => s.strain[i]);
      plot(
        "poissonChart",
        [
          line(
            px,
            inds.map((i) => s.lateral[i]),
            "processed",
            { mode: "markers", marker: { size: 4 } },
          ),
          line(
            px,
            px.map((e) => r.poisson_fit.slope * e + r.poisson_fit.intercept),
            "fit",
          ),
        ],
        "axial_axis",
        "lateral_axis",
      );
    } else emptyChart("poissonChart");
    if (s.rate.some((v) => v !== null)) {
      const v = s.rate.filter((x) => x !== null),
        lo = Math.min(...v),
        hi = Math.max(...v),
        pad = Math.max((hi - lo) * 0.1, Math.abs(m.mean_rate_s) * 0.05, 1e-9);
      plot(
        "rateChart",
        [line(s.time, s.rate, "processed")],
        "time_axis",
        "rate_axis",
        {
          yaxis: {
            title: { text: t("rate_axis") },
            gridcolor: c.grid,
            range: [lo - pad, hi + pad],
            tickformat: ".2e",
            automargin: true,
          },
        },
      );
    } else emptyChart("rateChart");
    plot(
      "partitionChart",
      [
        line(
          x.slice(0, peak + 1),
          s.elastic_strain.slice(0, peak + 1).map((e) => e * 100),
          "elastic_component",
        ),
        line(
          x.slice(0, peak + 1),
          s.permanent_strain.slice(0, peak + 1).map((e) => e * 100),
          "plastic_component",
        ),
      ],
      "strain_axis",
      "strain_axis",
    );
  }
}
async function renderComparison() {
  const box = $("compareList");
  box.replaceChildren();
  state.comparisons.forEach((r, i) => {
    const row = el("span", undefined, "compare-item");
    row.append(el("span", r.settings.sample_name));
    const b = el("button", t("remove"));
    b.addEventListener("click", () => {
      state.comparisons.splice(i, 1);
      renderComparison();
    });
    row.append(b);
    box.append(row);
  });
  if (!state.comparisons.length) {
    emptyChart("comparisonChart", "compare_empty");
    $("statistics").replaceChildren();
    return;
  }
  const traces = state.comparisons.map((r) =>
    line(
      r.series.strain.map((e) => e * 100),
      r.series.stress,
      r.settings.sample_name,
    ),
  );
  await plot("comparisonChart", traces, "strain_axis", "stress_axis");
  const response = await api("/api/compare", {
    results: state.comparisons.map((r) => ({
      settings: r.settings,
      metrics: r.metrics,
    })),
  });
  const stats = await response.json();
  $("statistics").replaceChildren();
  for (const group of stats) {
    $("statistics").append(el("h3", `${group.group} · n=${group.count}`));
    $("statistics").append(
      table(
        [t("metric"), t("count"), t("mean"), t("std")],
        ["E_GPa", "proof_MPa", "UTS_MPa", "toughness_MJ_m3"].map((k) => [
          t(k),
          group.statistics[k].n,
          number(group.statistics[k].mean, 4),
          number(group.statistics[k].std, 4),
        ]),
      ),
    );
  }
}
function render() {
  translate();
  if (state.dataset)
    $("fileSummary").textContent =
      `${state.dataset.name} · ${state.dataset.rows} ${t("input_rows").toLowerCase()}`;
  renderMetrics();
  renderCharts();
  if (state.tab === "compare")
    renderComparison().catch((e) => error(e.message));
}
async function run() {
  if (!state.dataset) {
    error("session_expired");
    return;
  }
  $("error").hidden = true;
  $("analyze").disabled = true;
  $("status").textContent = t("analyzing");
  try {
    const response = await api("/api/analyze", {
      id: state.dataset.id,
      settings: formValues(),
    });
    state.result = await response.json();
    $("f-elastic_min").value = state.result.settings.elastic_min;
    $("f-elastic_max").value = state.result.settings.elastic_max;
    render();
    $("status").textContent = t("ready");
  } catch (e) {
    error(e.message);
  } finally {
    $("analyze").disabled = false;
  }
}
function inferColumns(data) {
  const c = {
    ...defaults,
    sample_name: data.name,
    source: data.source,
    material: "",
    group: "",
    complete: false,
  };
  const keys = data.columns;
  const pick = (names, fallback) =>
    keys.find((x) => names.some((n) => x.toLowerCase().includes(n))) ||
    fallback;
  c.force_column = pick(["force", "load", "kraft"], "");
  c.extension_column = pick(
    ["extension", "elongation", "uzama", "verlängerung"],
    "",
  );
  c.stress_column = pick(["stress", "spannung", "gerilme"], "");
  c.strain_column = pick(["strain", "dehnung"], "");
  c.time_column = pick(["time", "zeit", "zaman"], "");
  c.lateral_column = pick(["transverse", "lateral", "enine", "quer"], "");
  if (!c.force_column && c.stress_column) c.mode = "stress";
  if (c.strain_column.includes("percent")) c.strain_unit = "percent";
  return c;
}
async function loadExample() {
  try {
    $("status").textContent = t("loading");
    const name = $("example").value;
    const response = await api("/api/example", { name });
    state.dataset = await response.json();
    const c = {
      ...defaults,
      sample_name: name,
      complete: name !== "incomplete",
      elastic_limit:
        name === "aluminium_model" ? 160 : name === "brittle" ? 280 : 250,
      material:
        name === "aluminium_model"
          ? "Model A1"
          : name === "brittle"
            ? "Model B1"
            : "Model M1",
      group: ["reference", "noisy", "replicate"].includes(name) ? "M1" : name,
    };
    buildForm(c);
    $("fileSummary").textContent =
      `${name}.csv · ${state.dataset.rows} ${t("input_rows").toLowerCase()}`;
    $("sheetLabel").hidden = true;
    await run();
  } catch (e) {
    error(e.message);
  }
}
async function uploadFile() {
  if (!state.file) return;
  try {
    const f = new FormData();
    f.append("file", state.file);
    f.append("decimal", $("decimal").value);
    if ($("sheet").value) f.append("sheet", $("sheet").value);
    state.dataset = await (await api("/api/upload", f)).json();
    const selected = $("sheet").value;
    $("sheet").replaceChildren(
      ...state.dataset.sheets.map((x) => {
        const o = el("option", x);
        o.value = x;
        return o;
      }),
    );
    if (state.dataset.sheets.includes(selected)) $("sheet").value = selected;
    $("sheetLabel").hidden = !state.dataset.sheets.length;
    buildForm(inferColumns(state.dataset));
    $("fileSummary").textContent =
      `${state.file.name} · ${state.dataset.rows} ${t("input_rows").toLowerCase()}`;
    await run();
  } catch (e) {
    error(e.message);
  }
}
async function download(kind) {
  if (!state.result) return;
  try {
    const response = await api("/api/export/" + kind, {
      result: state.result,
      lang: state.lang,
    });
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = el("a");
    a.href = url;
    a.download = `tensile-analysis-${state.lang}.${kind}`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  } catch (e) {
    error(e.message);
  }
}
async function init() {
  for (const lang of ["en", "tr", "de"])
    state.locales[lang] = await (
      await fetch(`/static/locales/${lang}.json`)
    ).json();
  if (!state.locales[state.lang]) state.lang = "en";
  if (!["light", "dark"].includes(state.theme)) state.theme = "light";
  const examples = await (await fetch("/api/examples")).json();
  examples.forEach((x) => {
    const o = el("option", t(x.id));
    o.value = x.id;
    $("example").append(o);
  });
  buildForm();
  translate();
  $("language").addEventListener("change", () => {
    const v = formValues();
    state.lang = $("language").value;
    localStorage.setItem("tensile-language", state.lang);
    buildForm(v);
    render();
    $("status").textContent = t("ready");
  });
  $("theme").addEventListener("change", () => {
    state.theme = $("theme").value;
    localStorage.setItem("tensile-theme", state.theme);
    render();
  });
  $("loadExample").addEventListener("click", loadExample);
  $("analyze").addEventListener("click", run);
  $("settingsForm").addEventListener("submit", (e) => {
    e.preventDefault();
    run();
  });
  $("upload").addEventListener("change", () => {
    state.file = $("upload").files[0];
    $("sheet").replaceChildren();
    uploadFile();
  });
  $("sheet").addEventListener("change", uploadFile);
  $("decimal").addEventListener("change", () => {
    if (state.file) uploadFile();
  });
  $("tabs")
    .querySelectorAll("button")
    .forEach((b) =>
      b.addEventListener("click", () => {
        state.tab = b.dataset.tab;
        document
          .querySelectorAll(".panel")
          .forEach((p) => (p.hidden = p.id !== "panel-" + state.tab));
        $("tabs")
          .querySelectorAll("button")
          .forEach((x) => x.classList.toggle("active", x === b));
        render();
      }),
    );
  $("addCompare").addEventListener("click", () => {
    if (state.result && state.comparisons.length < 30) {
      state.comparisons.push(structuredClone(state.result));
      $("addCompare").textContent =
        `${t("add_compare")} (${state.comparisons.length})`;
      if (state.tab === "compare") renderComparison();
    }
  });
  $("clearCompare").addEventListener("click", () => {
    state.comparisons = [];
    renderComparison();
  });
  document
    .querySelectorAll("[data-export]")
    .forEach((b) =>
      b.addEventListener("click", () => download(b.dataset.export)),
    );
  $("restore").addEventListener("change", async () => {
    try {
      const r = JSON.parse(await $("restore").files[0].text());
      if (!r.metrics || !r.series?.strain || !r.settings || !r.elastic)
        throw Error("invalid_file");
      state.result = r;
      state.dataset = await (await api("/api/restore", r)).json();
      buildForm(r.settings);
      render();
      $("status").textContent = t("imported");
    } catch {
      error("invalid_file");
    }
  });
  await loadExample();
}
init().catch((e) => error(e.message));
