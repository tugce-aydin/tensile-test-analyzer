const { chromium } = require("playwright");

const { spawn } = require("child_process");
const fs = require("fs");
const assert = require("assert");
const server = spawn(
  process.env.TENSILE_PYTHON || ".venv/bin/python",
  ["app.py", "--no-browser"],
  { stdio: ["ignore", "pipe", "pipe"] },
);
const output = "docs/screenshots/";
(async () => {
  await new Promise((resolve, reject) => {
    server.stderr.on("data", (d) => {
      if (d.toString().includes("Running on")) resolve();
    });
    server.on("exit", (code) => reject(Error("server " + code)));
    setTimeout(() => reject(Error("server timeout")), 20000).unref();
  });
  const b = await chromium.launch({ headless: true });
  const p = await b.newPage({
    viewport: { width: 1440, height: 1080 },
    acceptDownloads: true,
  });
  let errors = [];
  p.on("pageerror", (e) => errors.push(e.message));
  await p.goto("http://127.0.0.1:8765/");
  await p.waitForFunction(
    () => document.querySelectorAll(".metric-card").length === 4,
  );
  const before = await p.evaluate(() => JSON.stringify(state.result.metrics));
  await p.screenshot({ path: output + "overview-en-light.png" });
  for (const lang of ["de", "tr", "en"]) {
    await p.selectOption("#language", lang);
    assert.strictEqual(
      await p.evaluate(() => JSON.stringify(state.result.metrics)),
      before,
    );
    assert.strictEqual(await p.getAttribute("html", "lang"), lang);
    for (const theme of ["light", "dark"]) {
      await p.selectOption("#theme", theme);
      assert.strictEqual(
        await p.evaluate(() => JSON.stringify(state.result.metrics)),
        before,
      );
      assert.strictEqual(await p.getAttribute("html", "data-theme"), theme);
    }
  }
  await p.selectOption("#theme", "dark");
  await p.screenshot({ path: output + "overview-en-dark.png" });
  await p.selectOption("#language", "en");
  await p.screenshot({ path: output + "overview-en-dark.png" });
  await p.selectOption("#theme", "light");
  await p.locator('[data-tab="elastic"]').click();
  await p.waitForFunction(
    () => document.getElementById("elasticChart").data?.length > 0,
  );
  await p.screenshot({ path: output + "elastic-en-light.png" });
  const coords = await p.evaluate(() => {
    const g = document.getElementById("elasticChart"),
      r = g.getBoundingClientRect(),
      a = g._fullLayout.xaxis;
    return {
      x1: r.x + a._offset + a.l2p(0.015),
      x2: r.x + a._offset + a.l2p(0.085),
      y: r.y + 130,
    };
  });
  await p.mouse.move(coords.x1, coords.y);
  await p.mouse.down();
  await p.mouse.move(coords.x2, coords.y + 70, { steps: 12 });
  await p.mouse.up();
  await p.waitForFunction(() => state.result.settings.auto_elastic === false);
  assert(
    Math.abs((await p.evaluate(() => state.result.metrics.E_GPa)) - 200) <
      0.001,
  );
  await p.selectOption("#language", "en");
  await p.locator('[data-tab="advanced"]').click();
  await p.waitForFunction(
    () => document.getElementById("trueChart").data?.length > 0,
  );
  await p.screenshot({ path: output + "advanced-en-light.png" });
  await p.locator("#addCompare").click();
  await p.selectOption("#example", "replicate");
  await p.locator("#loadExample").click();
  await p.waitForFunction(
    () => state.result.settings.sample_name === "replicate",
  );
  await p.locator("#addCompare").click();
  await p.locator('[data-tab="compare"]').click();
  await p.waitForFunction(() => document.querySelector("#statistics table"));
  assert((await p.locator("#statistics").innerText()).includes("n=2"));
  await p.selectOption("#language", "en");
  await p.screenshot({ path: output + "comparison-en-light.png" });
  await p.locator('[data-tab="data"]').click();
  const down = p.waitForEvent("download");
  await p.locator('[data-export="json"]').click();
  const d = await down;
  await d.saveAs(
    require("path").join(require("os").tmpdir(), "tensile-snapshot.json"),
  );
  assert(
    fs.statSync(
      require("path").join(require("os").tmpdir(), "tensile-snapshot.json"),
    ).size > 1000,
  );
  await p.setInputFiles(
    "#restore",
    require("path").join(require("os").tmpdir(), "tensile-snapshot.json"),
  );
  await p.waitForFunction(
    () =>
      document.getElementById("status").textContent === "Saved analysis opened",
  );
  await p.locator("#analyze").click();
  await p.waitForFunction(
    () => document.getElementById("status").textContent === "Analysis ready",
  );
  await p.selectOption("#example", "incomplete");
  await p.locator("#loadExample").click();
  await p.waitForFunction(
    () => state.result.settings.sample_name === "incomplete",
  );
  assert.strictEqual(
    await p.evaluate(() => state.result.metrics.toughness_MJ_m3),
    null,
  );
  await p.setInputFiles("#upload", "data/reference.xlsx");
  await p.waitForFunction(
    () => document.getElementById("sheet").options.length === 1,
  );
  await p.waitForFunction(() => state.result.settings.source === "user");
  assert(
    Math.abs((await p.evaluate(() => state.result.metrics.E_GPa)) - 200) <
      0.001,
  );
  await p.selectOption("#example", "reference");
  await p.locator("#loadExample").click();
  await p.waitForFunction(() => state.result.settings.source === "synthetic");
  await p.locator('[data-tab="overview"]').click();
  await p.setViewportSize({ width: 390, height: 844 });
  await p.screenshot({ path: output + "mobile-en.png", fullPage: true });
  assert.strictEqual(
    await p.evaluate(() => document.documentElement.scrollWidth > innerWidth),
    false,
  );
  console.log(
    JSON.stringify(
      {
        browser: await b.version(),
        checks: [
          "six language/theme combinations",
          "elastic interval drag",
          "all chart views",
          "replicate comparison",
          "JSON download and restore",
          "incomplete test guard",
          "Excel upload",
          "390px layout",
        ],
        errors,
      },
      null,
      2,
    ),
  );
  assert.deepStrictEqual(errors, []);
  await b.close();
})()
  .catch((e) => {
    console.error(e);
    process.exitCode = 1;
  })
  .finally(() => server.kill());
