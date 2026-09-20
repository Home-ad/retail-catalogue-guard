const $ = (selector) => document.querySelector(selector);
const number = (value) => new Intl.NumberFormat("en-GB").format(value || 0);
const escapeHtml = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (character) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        character
      ],
  );
const readable = (value) => String(value || "").replaceAll("_", " ");
let page = 1;
let catalogueText = "";
let currentTrend = [];

async function request(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : `Request failed (${response.status})`,
    );
  }
  return response;
}

function reportError(error) {
  $("#error").hidden = false;
  $("#error").textContent = error.message || String(error);
  $("#error").scrollIntoView({ behavior: "smooth", block: "center" });
}

async function action(operation) {
  $("#error").hidden = true;
  try {
    await operation();
  } catch (error) {
    reportError(error);
  }
}

function showView(id) {
  document
    .querySelectorAll(".view")
    .forEach((view) => (view.hidden = view.id !== id));
  document
    .querySelectorAll(".nav")
    .forEach((button) =>
      button.classList.toggle("active", button.dataset.view === id),
    );
  if (id === "catalogue") action(loadProducts);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function metric(label, value, note, accent = false) {
  return `<div class="metric ${accent ? "accent" : ""}"><div class="label">${escapeHtml(label)}</div><strong>${number(value)}</strong><small>${escapeHtml(note)}</small></div>`;
}

function bars(target, values) {
  const max = Math.max(...values.map((row) => row.value), 1);
  $(target).innerHTML = values
    .map(
      (row) =>
        `<div class="bar"><div class="bar-label"><span title="${escapeHtml(row.label)}">${escapeHtml(row.label)}</span><b>${number(row.value)}</b></div><div class="track"><div class="fill" style="width:${Math.max((row.value / max) * 100, 0.4)}%"></div></div></div>`,
    )
    .join("");
}

function lineChart(target, rows, suffix = "") {
  if (!rows.length) {
    $(target).innerHTML =
      '<p class="empty">No observations in this snapshot.</p>';
    return;
  }
  const max = Math.max(...rows.map((row) => Number(row.value)), 1);
  const coordinates = rows.map((row, index) => [
    28 + (index / Math.max(rows.length - 1, 1)) * 520,
    156 - (Number(row.value) / max) * 126,
  ]);
  const points = coordinates.map((point) => point.join(",")).join(" ");
  const circles = rows
    .map(
      (row, index) =>
        `<circle cx="${coordinates[index][0]}" cy="${coordinates[index][1]}" r="3" fill="#176448"><title>${escapeHtml(row.label)}: ${number(row.value)} ${escapeHtml(suffix)}</title></circle>`,
    )
    .join("");
  $(target).innerHTML =
    `<svg class="line-chart" viewBox="0 0 575 180" role="img" aria-label="${escapeHtml(rows.length + " observations; maximum " + number(max) + " " + suffix)}"><path d="M28 30H548 M28 93H548 M28 156H548" fill="none" stroke="#e2e8de"/><polygon points="28,156 ${points} ${coordinates.at(-1)[0]},156" fill="#eaf2de"/><polyline points="${points}" fill="none" stroke="#176448" stroke-width="2.5"/>${circles}<text x="28" y="17" font-size="10" fill="#68786f">${number(max)} ${escapeHtml(suffix)}</text></svg><div class="chart-axis"><span>${escapeHtml(rows[0].label)}</span><span>${escapeHtml(rows.at(-1).label)}</span></div>`;
}

function badge(status) {
  const kind =
    status.includes("conflict") || status.includes("invalid")
      ? "conflict"
      : status.includes("recall")
        ? "warn"
        : "";
  return `<span class="badge ${kind}">${escapeHtml(readable(status))}</span>`;
}

function safeUrl(value) {
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) ? url.href : "#";
  } catch {
    return "#";
  }
}

async function loadOverview() {
  const data = await (await request("/api/overview")).json();
  const counts = data.report.counts;
  if (data.report.scope === "demo")
    $("#overview h1").innerHTML =
      "Real records.<br><em>One clearer picture.</em>";
  $("#snapshot").textContent =
    `${data.report.scope.toUpperCase()} SNAPSHOT · ${data.report.built_at.slice(0, 10)}`;
  $("#metrics").innerHTML =
    metric(
      data.report.scope === "demo"
        ? "Demo product records"
        : "Product source records",
      counts.product_source,
      data.report.scope === "demo"
        ? "Selected from the full build"
        : "Before identifier validation",
    ) +
    metric(
      "Price observations",
      counts.price_source,
      data.report.scope === "demo"
        ? "Selected accepted observations"
        : "Before quality exclusions",
    ) +
    metric(
      "Food recall notices",
      counts.notices,
      "Latest record per notice ID",
    ) +
    metric(
      "Linked across all 3 sources",
      counts.three_source_overlap,
      "Candidate barcode matches",
      true,
    );
  bars("#coverage-chart", data.coverage);
  bars("#countries-chart", data.countries);
  bars("#categories-chart", data.categories);
  lineChart("#timeline-chart", data.months, "notices");
  const names = {
    products: "Open Food Facts · Product catalogue",
    prices: "Open Prices · Price observations",
    recalls: "RappelConso · Recall notices",
  };
  $("#source-list").innerHTML = data.report.sources
    .map(
      (source) =>
        `<article class="source"><h3>${escapeHtml(names[source.source] || source.source)}</h3><p><a href="${escapeHtml(safeUrl(source.url))}" target="_blank" rel="noopener">Original downloadable source ↗</a></p><p>Retrieved ${escapeHtml(source.retrieved_at)} · ${number(source.bytes)} bytes</p><code>SHA-256 ${escapeHtml(source.sha256)}</code></article>`,
    )
    .join("");
  if (data.report.scope === "demo")
    $("#source-list").insertAdjacentHTML(
      "afterbegin",
      '<div class="callout"><b>Curated real-data demo</b><p>This database is a selected subset. Dashboard counts describe only this subset, not the full source datasets.</p></div>',
    );
}

async function loadProducts() {
  $("#products-body").innerHTML =
    '<tr><td colspan="5" class="empty">Loading products…</td></tr>';
  const params = new URLSearchParams({
    q: $("#search").value,
    status: $("#status").value,
    page,
  });
  const data = await (await request("/api/products?" + params)).json();
  $("#results-count").textContent =
    `${number(data.total)} ${data.total === 1 ? "product" : "products"}`;
  $("#products-body").innerHTML = data.rows.length
    ? data.rows
        .map(
          (row) =>
            `<tr><td><button class="product-link" data-code="${escapeHtml(row.gtin)}">${escapeHtml(row.name || "Unnamed product")}</button><small>${escapeHtml(row.raw_code)} · ${escapeHtml(row.quantity || "Pack size unknown")}</small></td><td>${escapeHtml(row.brand || "—")}</td><td>${number(row.price_count)}</td><td>${number(row.notice_count)}</td><td>${badge(row.review_status)}</td></tr>`,
        )
        .join("")
    : '<tr><td colspan="5" class="empty">No products match these filters. Try another name or barcode.</td></tr>';
  $("#page-number").textContent =
    `Page ${page} of ${Math.max(1, Math.ceil(data.total / data.page_size))}`;
  $("#previous").disabled = page === 1;
  $("#next").disabled = page * data.page_size >= data.total;
}

function updateTrend() {
  const key = $("#trend-choice").value;
  const rows = currentTrend
    .filter((row) => `${row.currency}|${row.unit}` === key)
    .map((row) => ({ label: row.month, value: Number(row.median_price) }));
  lineChart("#price-trend", rows, key.replace("|", " / "));
}

async function openProduct(code) {
  const data = await (
    await request("/api/products/" + encodeURIComponent(code))
  ).json();
  const product = data.product;
  currentTrend = data.trend;
  const groups = [
    ...new Set(data.trend.map((row) => `${row.currency}|${row.unit}`)),
  ];
  $("#product-detail").innerHTML =
    `<h2>${escapeHtml(product.name || "Unnamed product")}</h2><p class="detail-meta">${escapeHtml(product.brand || "Brand unknown")} · ${escapeHtml(product.raw_code)} · ${escapeHtml(product.quantity || "Pack size unknown")}</p>${badge(product.review_status)}<p><a class="text-link" href="https://world.openfoodfacts.org/product/${encodeURIComponent(product.raw_code)}" target="_blank" rel="noopener">Open Food Facts record ↗</a></p><h3>Historical recall candidates (${number(data.notices.length)})</h3><p class="caption">Check the original product description and batch identifiers. A historical notice does not establish whether current stock is affected.</p>${data.notices.length ? data.notices.map((notice) => `<article class="notice"><b>${escapeHtml(notice.name)}</b><p>${escapeHtml((notice.published_at || "").slice(0, 10))} · ${escapeHtml(notice.reason || "Reason not supplied")}</p>${notice.name_conflict ? badge("description_conflict") : ""}<details><summary>Original product and batch block</summary><pre>${escapeHtml(notice.raw_blocks)}</pre></details><p><a href="${escapeHtml(safeUrl(notice.source_url))}" target="_blank" rel="noopener">Original recall notice ↗</a></p></article>`).join("") : '<p class="caption">No matching notice in this snapshot. This is not a safety guarantee.</p>'}<h3>Observed price history</h3><p class="caption">Monthly median for the same code, currency and reported price unit. Changes in pack size or historical metadata are not resolved. No currency conversion.</p>${groups.length ? `<label>Currency and price unit<select id="trend-choice">${groups.map((key) => `<option value="${escapeHtml(key)}">${escapeHtml(key.replace("|", " / "))}</option>`).join("")}</select></label><div id="price-trend"></div>` : '<p class="empty">No price observations for this code.</p>'}<h3>Latest price observations</h3><div class="table-wrap"><table><thead><tr><th>Date</th><th>Price</th><th>Unit</th><th>Location</th><th>Source</th></tr></thead><tbody>${data.prices.map((row) => `<tr><td>${escapeHtml(row.observed_on)}</td><td>${Number(row.price).toFixed(2)} ${escapeHtml(row.currency)}${row.discounted ? " · discount" : ""}</td><td>${escapeHtml(row.price_per || "Unspecified")}</td><td>${escapeHtml(row.city || row.country || "Unknown")}</td><td><a href="https://prices.openfoodfacts.org/prices/${row.price_id}" target="_blank" rel="noopener">Observation ↗</a></td></tr>`).join("") || '<tr><td colspan="5">No observations available.</td></tr>'}</tbody></table></div>`;
  if (groups.length) {
    $("#trend-choice").addEventListener("change", updateTrend);
    updateTrend();
  }
  $("#product-dialog").showModal();
}

async function runReview(text) {
  catalogueText = text;
  $("#review-results").hidden = true;
  const data = await (
    await request("/api/review", {
      method: "POST",
      headers: { "Content-Type": "text/csv" },
      body: text,
    })
  ).json();
  $("#review-metrics").innerHTML =
    metric("Catalogue rows", data.summary.rows, "Original row order retained") +
    metric(
      "Matched product records",
      data.summary.matched_products,
      "A code match, not a batch decision",
    ) +
    metric(
      "Rows needing review",
      data.summary.review_required,
      "Multiple issues may apply",
      true,
    );
  $("#review-body").innerHTML = data.rows
    .map(
      (row) =>
        `<tr><td>${escapeHtml(row.sku || "Missing SKU")}<small>${escapeHtml(row.barcode)}</small></td><td>${row.product_name ? `<button class="product-link" data-code="${escapeHtml(row.gtin)}">${escapeHtml(row.product_name)}</button>` : "Not matched"}</td><td>${row.issues.length ? row.issues.map(badge).join("") : badge("no_issue_detected")}</td><td>${number(row.notice_count)}</td><td>${escapeHtml(readable(row.batch_status))}</td></tr>`,
    )
    .join("");
  $("#review-results").hidden = false;
}

document
  .querySelectorAll(".nav")
  .forEach((button) =>
    button.addEventListener("click", () => showView(button.dataset.view)),
  );
$("#start-review").addEventListener("click", () => showView("review"));
$("#search-form").addEventListener("submit", (event) => {
  event.preventDefault();
  page = 1;
  action(loadProducts);
});
$("#previous").addEventListener("click", () => {
  page--;
  action(loadProducts);
});
$("#next").addEventListener("click", () => {
  page++;
  action(loadProducts);
});
document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-code]");
  if (button) action(() => openProduct(button.dataset.code));
});
$("#close-dialog").addEventListener("click", () =>
  $("#product-dialog").close(),
);
$("#demo-review").addEventListener("click", () =>
  action(async () => {
    $("#file-name").textContent = "Demo: 25 selected public products";
    await runReview(await (await request("/api/demo-catalogue")).text());
  }),
);
$("#csv-file").addEventListener("change", () =>
  action(async () => {
    const file = $("#csv-file").files[0];
    if (!file) return;
    if (file.size > 2_000_000)
      throw new Error("CSV must be smaller than 2 MB.");
    $("#file-name").textContent = file.name;
    await runReview(await file.text());
  }),
);
$("#export-review").addEventListener("click", () =>
  action(async () => {
    const response = await request("/api/review.csv", {
      method: "POST",
      headers: { "Content-Type": "text/csv" },
      body: catalogueText,
    });
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = "catalogue_review.csv";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }),
);
action(loadOverview);
