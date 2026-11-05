// =====================================================
// script.js - what the NutriScan dashboard DOES
// =====================================================
// This file does the same EDA steps as eda_analysis.py, but in JavaScript,
// so the results show up in the browser:
//   STEP 1  helper functions (mean, median, ...)
//   STEP 2  key numbers (the 4 cards at the top)
//   STEP 3  averages by food group
//   STEP 4  draw the 5 charts (with SVG, no extra library needed)
//   STEP 5  statistics tables
//   STEP 6  top 5 products
//   STEP 7  search and sort products
//   STEP 8  write the key findings
//
// PRODUCTS comes from data.js (85 products). Each product looks like:
//   { product_name: "Nutella", food_group: "Spreads", sugars_g: 56.3, ... }
// A missing value is null.

// The nutrient columns we analyse, with a nice name and a unit
const NUTRIENTS = [
  { key: "energy_kcal",     label: "Calories",      unit: "kcal" },
  { key: "sugars_g",        label: "Sugar",         unit: "g" },
  { key: "proteins_g",      label: "Protein",       unit: "g" },
  { key: "carbohydrates_g", label: "Carbohydrates", unit: "g" },
  { key: "fat_g",           label: "Fat",           unit: "g" },
  { key: "saturated_fat_g", label: "Saturated fat", unit: "g" },
  { key: "salt_g",          label: "Salt",          unit: "g" },
];


// =====================================================
// STEP 1: HELPER FUNCTIONS
// =====================================================

// Get all values of one column, and SKIP missing ones (like Pandas does)
function getValues(products, key) {
  return products.map(p => p[key]).filter(v => v !== null && v !== undefined);
}

// Mean = add everything up, divide by how many
function mean(values) {
  if (values.length === 0) return null;
  let total = 0;
  for (const v of values) total += v;
  return total / values.length;
}

// Median = the middle value after sorting.
// With an even number of values, it is the average of the 2 middle values.
function median(values) {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 0) {
    return (sorted[middle - 1] + sorted[middle]) / 2;
  }
  return sorted[middle];
}

// Pearson correlation (r) between two columns.
// Only products that have BOTH values are used.
//   r near +1 : both go up together
//   r near  0 : no relation
//   r near -1 : one goes up, the other goes down
function correlation(products, keyX, keyY) {
  const pairs = products.filter(p => p[keyX] !== null && p[keyY] !== null);
  const xs = pairs.map(p => p[keyX]);
  const ys = pairs.map(p => p[keyY]);
  const mx = mean(xs), my = mean(ys);
  let top = 0, sumX = 0, sumY = 0;
  for (let i = 0; i < xs.length; i++) {
    top  += (xs[i] - mx) * (ys[i] - my);
    sumX += (xs[i] - mx) ** 2;
    sumY += (ys[i] - my) ** 2;
  }
  return top / Math.sqrt(sumX * sumY);
}

// Show a number with a fixed number of decimals, or "-" if missing
function fmt(value, decimals = 1) {
  if (value === null || value === undefined) return "-";
  return Number(value).toFixed(decimals);
}

// Make text safe to put inside HTML (so names like "M&M's" show correctly)
function safe(text) {
  return String(text ?? "").replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}


// =====================================================
// STEP 2: KEY NUMBERS (top cards)
// =====================================================
const groupNames = [...new Set(PRODUCTS.map(p => p.food_group))];
const avgSugar = mean(getValues(PRODUCTS, "sugars_g"));
const r = correlation(PRODUCTS, "sugars_g", "energy_kcal");

document.getElementById("kpi-products").textContent = PRODUCTS.length;
document.getElementById("kpi-groups").textContent = groupNames.length;
document.getElementById("kpi-sugar").textContent = fmt(avgSugar, 2) + " g";
document.getElementById("kpi-corr").textContent = fmt(r, 2);


// =====================================================
// STEP 3: AVERAGES BY FOOD GROUP (like df.groupby in Pandas)
// =====================================================
const groupStats = groupNames.map(name => {
  const items = PRODUCTS.filter(p => p.food_group === name);
  return {
    group: name,
    count: items.length,
    sugar: mean(getValues(items, "sugars_g")),
    calories: mean(getValues(items, "energy_kcal")),
    protein: mean(getValues(items, "proteins_g")),
  };
});
// Sort from most sugar to least sugar (same order as the Python output)
groupStats.sort((a, b) => b.sugar - a.sugar);


// =====================================================
// STEP 4: CHARTS
// =====================================================
// Each chart is an SVG picture that we build as text and put in a <div>.
// Every bar/dot has a "data-tip" attribute; the tooltip shows that text.

const tooltip = document.getElementById("tooltip");

// Show the tooltip for anything inside "box" that has data-tip
function addTooltips(box) {
  box.querySelectorAll("[data-tip]").forEach(el => {
    el.addEventListener("mousemove", e => {
      tooltip.innerHTML = el.getAttribute("data-tip");
      tooltip.style.left = (e.clientX + 14) + "px";
      tooltip.style.top = (e.clientY + 14) + "px";
      tooltip.style.opacity = 1;
    });
    el.addEventListener("mouseleave", () => { tooltip.style.opacity = 0; });
  });
}

// Pick a "nice" top value for an axis, e.g. 56 -> 60, 574 -> 600
function niceMax(value) {
  if (value <= 0) return 1;
  const step = Math.pow(10, Math.floor(Math.log10(value)));
  return Math.ceil(value / step * 2) / 2 * step;
}

// ---------- Horizontal bar chart (charts 1, 2 and 5) ----------
// rows = [{ label: "Spreads", value: 21.4, tip: "..." }, ...]
function drawHorizontalBars(boxId, rows, unit, decimals = 1) {
  const box = document.getElementById(boxId);
  const W = box.clientWidth, H = box.clientHeight;
  const left = 120, right = 60, top = 10, bottom = 10;  // space around the bars
  const maxValue = niceMax(Math.max(...rows.map(r => r.value)));
  const rowHeight = (H - top - bottom) / rows.length;
  const barHeight = rowHeight * 0.65;

  let svg = `<svg viewBox="0 0 ${W} ${H}">`;
  rows.forEach((row, i) => {
    const y = top + i * rowHeight + (rowHeight - barHeight) / 2;
    const w = (row.value / maxValue) * (W - left - right);
    svg += `<text class="axis-text" x="${left - 8}" y="${y + barHeight / 2 + 4}" text-anchor="end">${safe(row.label)}</text>`;
    svg += `<rect class="bar" x="${left}" y="${y}" width="${Math.max(w, 1)}" height="${barHeight}" rx="3"
              data-tip="${safe(row.tip)}"></rect>`;
    svg += `<text class="value-text" x="${left + w + 6}" y="${y + barHeight / 2 + 4}">${fmt(row.value, decimals)} ${unit}</text>`;
  });
  svg += `</svg>`;
  box.innerHTML = svg;
  addTooltips(box);
}

// ---------- Histogram (chart 3) ----------
// Puts sugar values into bins of 5 g: 0-5, 5-10, ... 60-65
function drawHistogram(boxId) {
  const box = document.getElementById(boxId);
  const W = box.clientWidth, H = box.clientHeight;
  const left = 40, right = 10, top = 10, bottom = 40;

  // Count how many products fall in each bin
  const binSize = 5, binCount = 13;
  const counts = new Array(binCount).fill(0);
  for (const v of getValues(PRODUCTS, "sugars_g")) {
    const bin = Math.min(Math.floor(v / binSize), binCount - 1);
    counts[bin]++;
  }

  const maxCount = niceMax(Math.max(...counts));
  const plotW = W - left - right, plotH = H - top - bottom;
  const barW = plotW / binCount;

  let svg = `<svg viewBox="0 0 ${W} ${H}">`;
  // horizontal grid lines + y-axis numbers
  for (let t = 0; t <= 4; t++) {
    const value = maxCount * t / 4;
    const y = top + plotH - (value / maxCount) * plotH;
    svg += `<line class="grid-line" x1="${left}" x2="${W - right}" y1="${y}" y2="${y}"></line>`;
    svg += `<text class="axis-text" x="${left - 6}" y="${y + 4}" text-anchor="end">${Math.round(value)}</text>`;
  }
  // the bars
  counts.forEach((count, i) => {
    const h = (count / maxCount) * plotH;
    const x = left + i * barW;
    const from = i * binSize, to = from + binSize;
    svg += `<rect class="bar" x="${x + 1}" y="${top + plotH - h}" width="${barW - 2}" height="${h}"
              data-tip="${from}-${to} g sugar: <b>${count} products</b>"></rect>`;
    if (i % 2 === 0) {
      svg += `<text class="axis-text" x="${x}" y="${H - bottom + 16}" text-anchor="middle">${from}</text>`;
    }
  });
  svg += `<text class="axis-text" x="${left + plotW / 2}" y="${H - 4}" text-anchor="middle">Sugar (g per 100 g)</text>`;
  svg += `</svg>`;
  box.innerHTML = svg;
  addTooltips(box);
}

// ---------- Scatter plot (chart 4) ----------
// x = sugar, y = calories. One dot per product.
function drawScatter(boxId, highlightGroup) {
  const box = document.getElementById(boxId);
  const W = box.clientWidth, H = box.clientHeight;
  const left = 46, right = 14, top = 10, bottom = 40;
  const plotW = W - left - right, plotH = H - top - bottom;

  const points = PRODUCTS.filter(p => p.sugars_g !== null && p.energy_kcal !== null);
  const maxX = niceMax(Math.max(...points.map(p => p.sugars_g)));
  const maxY = niceMax(Math.max(...points.map(p => p.energy_kcal)));
  const toX = v => left + (v / maxX) * plotW;          // sugar  -> pixel
  const toY = v => top + plotH - (v / maxY) * plotH;   // kcal   -> pixel

  let svg = `<svg viewBox="0 0 ${W} ${H}">`;
  for (let t = 0; t <= 4; t++) {
    const yv = maxY * t / 4, xv = maxX * t / 4;
    svg += `<line class="grid-line" x1="${left}" x2="${W - right}" y1="${toY(yv)}" y2="${toY(yv)}"></line>`;
    svg += `<text class="axis-text" x="${left - 6}" y="${toY(yv) + 4}" text-anchor="end">${Math.round(yv)}</text>`;
    svg += `<text class="axis-text" x="${toX(xv)}" y="${H - bottom + 16}" text-anchor="middle">${Math.round(xv)}</text>`;
  }

  // Trend line (line of best fit): y = a + b * x
  const xs = points.map(p => p.sugars_g), ys = points.map(p => p.energy_kcal);
  const mx = mean(xs), my = mean(ys);
  let sxy = 0, sxx = 0;
  xs.forEach((x, i) => { sxy += (x - mx) * (ys[i] - my); sxx += (x - mx) ** 2; });
  const b = sxy / sxx, a = my - b * mx;
  svg += `<line class="trend" x1="${toX(0)}" y1="${toY(a)}" x2="${toX(maxX)}" y2="${toY(Math.min(a + b * maxX, maxY))}"></line>`;

  // The dots (highlighted group is drawn last so it is on top)
  const ordered = [...points].sort((p, q) => (p.food_group === highlightGroup) - (q.food_group === highlightGroup));
  for (const p of ordered) {
    let cls = "dot";
    if (highlightGroup) cls += p.food_group === highlightGroup ? " on" : " faded";
    const tip = `<b>${safe(p.product_name)}</b><br>${p.food_group}<br>Sugar: ${fmt(p.sugars_g)} g<br>Calories: ${fmt(p.energy_kcal)} kcal`;
    svg += `<circle class="${cls}" cx="${toX(p.sugars_g)}" cy="${toY(p.energy_kcal)}" r="5.5" data-tip="${safe(tip)}"></circle>`;
  }
  svg += `<text class="axis-text" x="${left + plotW / 2}" y="${H - 4}" text-anchor="middle">Sugar (g per 100 g)</text>`;
  svg += `<text class="axis-text" transform="translate(12 ${top + plotH / 2}) rotate(-90)" text-anchor="middle">Calories (kcal)</text>`;
  svg += `</svg>`;
  box.innerHTML = svg;
  addTooltips(box);
}

// Fill the "Highlight a group" dropdowns (scatter + search filter)
const scatterSelect = document.getElementById("scatter-group");
const groupFilter = document.getElementById("group-filter");
[...groupNames].sort().forEach(name => {
  scatterSelect.add(new Option(name, name));
  groupFilter.add(new Option(name, name));
});
scatterSelect.addEventListener("change", () => drawScatter("chart-scatter", scatterSelect.value));

document.getElementById("scatter-text").innerHTML =
  `<b>What it shows:</b> Each dot is one product. r = ${fmt(r, 2)}, a <b>moderate positive</b> relation: ` +
  `more sugar usually means more calories, but not always. Peanut butter and nuts are high in calories with little sugar, because their energy comes from fat.`;

// Missing values per column
const missingRows = NUTRIENTS.map(n => {
  const missing = PRODUCTS.length - getValues(PRODUCTS, n.key).length;
  const percent = missing / PRODUCTS.length * 100;
  return { label: n.label, value: percent, tip: `${n.label}: ${missing} missing (${fmt(percent)}%)` };
}).sort((a, b) => b.value - a.value);

// Draw (or redraw) every chart. Called at the start and when the window size changes.
function drawAllCharts() {
  drawHorizontalBars("chart-sugar",
    groupStats.map(g => ({ label: g.group, value: g.sugar, tip: `<b>${g.group}</b>: ${fmt(g.sugar)} g sugar (${g.count} products)` })),
    "g");
  drawHorizontalBars("chart-calories",
    [...groupStats].sort((a, b) => b.calories - a.calories)
      .map(g => ({ label: g.group, value: g.calories, tip: `<b>${g.group}</b>: ${fmt(g.calories)} kcal (${g.count} products)` })),
    "kcal", 0);
  drawHistogram("chart-hist");
  drawScatter("chart-scatter", scatterSelect.value);
  drawHorizontalBars("chart-missing", missingRows, "%");
}
drawAllCharts();
window.addEventListener("resize", drawAllCharts);


// =====================================================
// STEP 5: STATISTICS TABLES
// =====================================================
let statsHtml = `<thead><tr><th>Nutrient (per 100 g)</th><th class="num">Products with value</th>
  <th class="num">Mean</th><th class="num">Median</th><th class="num">Minimum</th><th class="num">Maximum</th></tr></thead><tbody>`;
for (const n of NUTRIENTS) {
  const v = getValues(PRODUCTS, n.key);
  statsHtml += `<tr><td>${n.label} (${n.unit})</td><td class="num">${v.length}</td>
    <td class="num">${fmt(mean(v), 2)}</td><td class="num">${fmt(median(v), 2)}</td>
    <td class="num">${fmt(Math.min(...v), 2)}</td><td class="num">${fmt(Math.max(...v), 2)}</td></tr>`;
}
document.getElementById("stats-table").innerHTML = statsHtml + "</tbody>";

let groupHtml = `<thead><tr><th>Food group</th><th class="num">Products</th><th class="num">Avg sugar (g)</th>
  <th class="num">Avg calories (kcal)</th><th class="num">Avg protein (g)</th></tr></thead><tbody>`;
for (const g of groupStats) {
  groupHtml += `<tr><td>${g.group}</td><td class="num">${g.count}</td><td class="num">${fmt(g.sugar)}</td>
    <td class="num">${fmt(g.calories)}</td><td class="num">${fmt(g.protein)}</td></tr>`;
}
document.getElementById("group-table").innerHTML = groupHtml + "</tbody>";


// =====================================================
// STEP 6: TOP 5 PRODUCTS (click a button to change nutrient)
// =====================================================
const topNutrients = NUTRIENTS.filter(n => ["sugars_g", "energy_kcal", "fat_g", "salt_g", "proteins_g"].includes(n.key));
const topButtons = document.getElementById("top-buttons");

function showTop(nutrient) {
  // highlight the clicked button
  topButtons.querySelectorAll("button").forEach(btn =>
    btn.classList.toggle("active", btn.dataset.key === nutrient.key));

  const top5 = PRODUCTS.filter(p => p[nutrient.key] !== null)
    .sort((a, b) => b[nutrient.key] - a[nutrient.key])
    .slice(0, 5);

  document.getElementById("top-list").innerHTML = top5.map((p, i) => `
    <li>
      <span class="rank">${i + 1}</span>
      <span><b>${safe(p.product_name)}</b><br><span class="top-group">${p.food_group} &middot; ${safe(p.brand)}</span></span>
      <span class="top-value">${fmt(p[nutrient.key])} ${nutrient.unit}</span>
    </li>`).join("");
}

topNutrients.forEach(n => {
  const btn = document.createElement("button");
  btn.textContent = n.label;
  btn.dataset.key = n.key;
  btn.addEventListener("click", () => showTop(n));
  topButtons.appendChild(btn);
});
showTop(topNutrients[0]);   // show sugar first


// =====================================================
// STEP 7: SEARCH AND SORT PRODUCTS
// =====================================================
const TABLE_COLUMNS = [
  { key: "product_name", label: "Product" },
  { key: "food_group",   label: "Group" },
  ...NUTRIENTS.map(n => ({ key: n.key, label: `${n.label} (${n.unit})`, number: true })),
  { key: "nutrition_grade", label: "Grade" },
];
let sortKey = "product_name";
let sortUp = true;   // true = A to Z / small to big

function showProducts() {
  const text = document.getElementById("search-box").value.toLowerCase().trim();
  const group = groupFilter.value;

  // 1) filter: keep products whose name or brand contains the text, and in the chosen group
  let rows = PRODUCTS.filter(p =>
    (p.product_name + " " + (p.brand || "")).toLowerCase().includes(text) &&
    (group === "" || p.food_group === group));

  // 2) sort: missing values always go to the bottom
  rows.sort((a, b) => {
    const x = a[sortKey], y = b[sortKey];
    if (x === null) return 1;
    if (y === null) return -1;
    const result = typeof x === "number" ? x - y : String(x).localeCompare(String(y));
    return sortUp ? result : -result;
  });

  // 3) build the table
  let html = "<thead><tr>";
  for (const c of TABLE_COLUMNS) {
    const arrow = c.key === sortKey ? (sortUp ? " &#9650;" : " &#9660;") : "";
    html += `<th data-key="${c.key}" class="${c.number ? "num" : ""}">${c.label}${arrow}</th>`;
  }
  html += "</tr></thead><tbody>";
  for (const p of rows) {
    html += "<tr>";
    for (const c of TABLE_COLUMNS) {
      if (c.key === "product_name") {
        html += `<td class="name-cell"><b>${safe(p.product_name)}</b><br><span class="top-group">${safe(p.brand)}</span></td>`;
      } else if (c.key === "nutrition_grade") {
        const g = p.nutrition_grade && "abcde".includes(p.nutrition_grade) ? p.nutrition_grade : null;
        html += `<td><span class="grade grade-${g || "none"}">${g || "?"}</span></td>`;
      } else if (c.number) {
        html += `<td class="num">${fmt(p[c.key])}</td>`;
      } else {
        html += `<td>${safe(p[c.key])}</td>`;
      }
    }
    html += "</tr>";
  }
  const table = document.getElementById("product-table");
  table.innerHTML = html + "</tbody>";
  document.getElementById("result-count").textContent = `${rows.length} of ${PRODUCTS.length} products`;

  // clicking a column title sorts by it (click again to reverse)
  table.querySelectorAll("th").forEach(th => th.addEventListener("click", () => {
    if (sortKey === th.dataset.key) sortUp = !sortUp;
    else { sortKey = th.dataset.key; sortUp = th.classList.contains("num") ? false : true; }
    showProducts();
  }));
}
document.getElementById("search-box").addEventListener("input", showProducts);
groupFilter.addEventListener("change", showProducts);
showProducts();


// =====================================================
// STEP 8: KEY FINDINGS (numbers come from the calculations above)
// =====================================================
const sugarValues = getValues(PRODUCTS, "sugars_g");
const highest = groupStats[0];
const water = groupStats.find(g => g.group === "Waters");
const under10 = sugarValues.filter(v => v < 10).length;
const topSugar = PRODUCTS.filter(p => p.sugars_g !== null).sort((a, b) => b.sugars_g - a.sugars_g)[0];
const maxMissing = missingRows[0];

const findings = [
  `<b>${highest.group}</b> have the highest average sugar (${fmt(highest.sugar)} g per 100 g)` +
    (water ? `, while <b>Waters</b> have ${fmt(water.sugar)} g.` : "."),
  `The product with the most sugar is <b>${safe(topSugar.product_name)}</b> with ${fmt(topSugar.sugars_g)} g per 100 g.`,
  `${under10} of ${sugarValues.length} products (${fmt(under10 / sugarValues.length * 100, 0)}%) have less than 10 g sugar. ` +
    `The mean sugar (${fmt(mean(sugarValues), 2)} g) is higher than the median (${fmt(median(sugarValues), 2)} g), so a few very sweet products pull the average up.`,
  `Sugar and calories have a <b>moderate positive</b> relation (r = ${fmt(r, 2)}). High-fat foods like nut butters break the pattern.`,
  `The data is fairly complete: the most missing column is ${maxMissing.label.toLowerCase()} with only ${fmt(maxMissing.value)}% missing.`,
  `Salt has an extreme outlier: <b>table salt</b> (99 g per 100 g). This makes the mean salt (1.67 g) much bigger than the median (0.14 g).`,
];
document.getElementById("findings-list").innerHTML = findings.map(f => `<li>${f}</li>`).join("");
