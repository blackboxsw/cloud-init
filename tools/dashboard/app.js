"use strict";

var DASH = DASH || {};

DASH.state = {
  index: null,
  summary: null,
  tests: null,
  filter: "",
  platforms: {},
  releases: {},
  window: "30",
  sort: "flakiness",
  onlyFlaky: false,
  onlyFailing: false,
  includeManual: false,
  groupParams: false,
  rowCap: 200,
  rowsShown: 0,
};

DASH.OUTCOMES = {
  P: { color: "P", glyph: "\u2714", label: "Pass" },
  F: { color: "F", glyph: "\u2718", label: "Fail" },
  E: { color: "E", glyph: "\u26a0", label: "Error" },
  S: { color: "S", glyph: "\u2013", label: "Skip" },
  X: { color: "X", glyph: "\u00d7", label: "Xfail" },
  I: { color: "I", glyph: "\u26ab", label: "Infra" },
  "-": { color: "-", glyph: "\u00b7", label: "Absent" },
};

DASH.GITHUB_RUN_URL = (
  "https://github.com/canonical/cloud-init/actions/runs/"
);

DASH.SVG_NS = "http" + "://www.w3.org/2000/svg";

DASH.init = function () {
  DASH.loadHashState();
  DASH.bindControls();
  DASH.loadData().then(function () {
    DASH.renderAll();
  }).catch(function (err) {
    DASH.showError(err);
  });
};

DASH.loadData = function () {
  return fetch("data/index.json")
    .then(function (r) {
      if (!r.ok) throw new Error("index.json not found");
      return r.json();
    })
    .then(function (idx) {
      DASH.state.index = idx;
      DASH.initChips(idx);
    })
    .then(function () {
      return fetch("data/summary.json");
    })
    .then(function (r) {
      if (!r.ok) throw new Error("summary.json not found");
      return r.json();
    })
    .then(function (sum) {
      DASH.state.summary = sum;
    })
    .then(function () {
      return fetch("data/tests.json");
    })
    .then(function (r) {
      if (!r.ok) throw new Error("tests.json not found");
      return r.json();
    })
    .then(function (t) {
      DASH.state.tests = t;
    });
};

DASH.initChips = function (idx) {
  var pc = document.getElementById("platform-chips");
  var rc = document.getElementById("release-chips");
  pc.textContent = "";
  rc.textContent = "";
  idx.platforms.forEach(function (p) {
    var chip = document.createElement("span");
    chip.className = "chip active";
    chip.textContent = p;
    chip.onclick = function () {
      chip.classList.toggle("active");
      DASH.state.platforms[p] = chip.classList.contains("active");
      DASH.renderAll();
      DASH.saveHashState();
    };
    DASH.state.platforms[p] = true;
    pc.appendChild(chip);
  });
  idx.releases.forEach(function (r) {
    var chip = document.createElement("span");
    chip.className = "chip active";
    chip.textContent = r.codename;
    chip.onclick = function () {
      chip.classList.toggle("active");
      DASH.state.releases[r.codename] =
        chip.classList.contains("active");
      DASH.renderAll();
      DASH.saveHashState();
    };
    DASH.state.releases[r.codename] = true;
    rc.appendChild(chip);
  });
};

DASH.bindControls = function () {
  var fi = document.getElementById("filter-input");
  var ws = document.getElementById("window-select");
  var ss = document.getElementById("sort-select");
  var of = document.getElementById("only-flaky");
  var ofa = document.getElementById("only-failing");
  var im = document.getElementById("include-manual");
  var gp = document.getElementById("group-params");
  var lm = document.getElementById("load-more");
  var dc = document.getElementById("detail-close");

  var debounceTimer = null;
  fi.oninput = function () {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(function () {
      DASH.state.filter = fi.value;
      DASH.renderAll();
      DASH.saveHashState();
    }, 200);
  };
  ws.onchange = function () {
    DASH.state.window = ws.value;
    DASH.renderAll();
    DASH.saveHashState();
  };
  ss.onchange = function () {
    DASH.state.sort = ss.value;
    DASH.renderAll();
    DASH.saveHashState();
  };
  of.onchange = function () {
    DASH.state.onlyFlaky = of.checked;
    DASH.renderAll();
    DASH.saveHashState();
  };
  ofa.onchange = function () {
    DASH.state.onlyFailing = ofa.checked;
    DASH.renderAll();
    DASH.saveHashState();
  };
  im.onchange = function () {
    DASH.state.includeManual = im.checked;
    DASH.renderAll();
    DASH.saveHashState();
  };
  gp.onchange = function () {
    DASH.state.groupParams = gp.checked;
    DASH.renderAll();
    DASH.saveHashState();
  };
  lm.onclick = function () {
    DASH.state.rowCap += 200;
    DASH.renderTable();
  };
  dc.onclick = function () {
    document.getElementById("detail-drawer").style.display = "none";
  };
};

DASH.renderAll = function () {
  DASH.renderHealthStrip();
  DASH.renderWorstOffenders();
  DASH.renderTable();
};

DASH.renderHealthStrip = function () {
  var strip = document.getElementById("health-strip");
  strip.textContent = "";
  if (!DASH.state.index) return;
  DASH.state.index.workflows.forEach(function (wf) {
    var badge = document.createElement("span");
    badge.className = "wf-badge";
    var concl = wf.last_conclusion || "unknown";
    if (concl === "failure") {
      badge.style.borderColor = "var(--fail)";
    }
    var now = new Date().getTime();
    var lastRun = wf.last_run
      ? new Date(wf.last_run).getTime()
      : 0;
    var daysSince = (now - lastRun) / 86400000;
    if (daysSince > 7) {
      badge.classList.add("stale");
      badge.textContent = wf.platform + " STALE";
    } else {
      badge.textContent = wf.platform + " " + concl;
    }
    badge.title = wf.path + " last: " + wf.last_run;
    strip.appendChild(badge);
  });
};

DASH.renderWorstOffenders = function () {
  var panel = document.getElementById("worst-offenders");
  panel.textContent = "";
  if (!DASH.state.summary) return;
  var tests = DASH.state.summary.tests || [];
  var scored = tests.map(function (t, i) {
    var maxFlips = 0;
    var maxFails = 0;
    var nodeid = DASH.state.tests
      ? DASH.state.tests.ids[i]
      : "test_" + i;
    if (t.c) {
      Object.keys(t.c).forEach(function (k) {
        if (t.c[k].flips > maxFlips) maxFlips = t.c[k].flips;
        if (t.c[k].f > maxFails) maxFails = t.c[k].f;
      });
    }
    return { nodeid: nodeid, flips: maxFlips, fails: maxFails };
  });
  var byFlakiness = scored.slice().sort(function (a, b) {
    return b.flips - a.flips;
  }).slice(0, 5);
  var byFails = scored.slice().sort(function (a, b) {
    return b.fails - a.fails;
  }).slice(0, 5);
  var h2 = document.createElement("h2");
  h2.textContent = "Worst offenders";
  panel.appendChild(h2);
  var flakyList = document.createElement("div");
  flakyList.className = "offender-list";
  byFlakiness.forEach(function (t) {
    if (t.flips === 0) return;
    var item = document.createElement("span");
    item.className = "offender-item";
    item.textContent = t.flips + " flips: " + DASH.shortName(t.nodeid);
    item.title = t.nodeid;
    item.onclick = function () {
      document.getElementById("filter-input").value = t.nodeid;
      DASH.state.filter = t.nodeid;
      DASH.renderAll();
      DASH.saveHashState();
    };
    flakyList.appendChild(item);
  });
  panel.appendChild(flakyList);
  var failList = document.createElement("div");
  failList.className = "offender-list";
  byFails.forEach(function (t) {
    if (t.fails === 0) return;
    var item = document.createElement("span");
    item.className = "offender-item";
    item.textContent = t.fails + " fails: " + DASH.shortName(t.nodeid);
    item.title = t.nodeid;
    item.onclick = function () {
      document.getElementById("filter-input").value = t.nodeid;
      DASH.state.filter = t.nodeid;
      DASH.renderAll();
      DASH.saveHashState();
    };
    failList.appendChild(item);
  });
  panel.appendChild(failList);
};

DASH.renderTable = function () {
  var thead = document.getElementById("table-head");
  var tbody = document.getElementById("table-body");
  var lmContainer = document.getElementById("load-more-container");
  thead.textContent = "";
  tbody.textContent = "";

  if (!DASH.state.summary || !DASH.state.tests) {
    var empty = document.createElement("tr");
    var td = document.createElement("td");
    td.textContent = "No data available yet. Data appears after the" +
      " first scheduled run with junit artifact upload.";
    empty.appendChild(td);
    tbody.appendChild(empty);
    return;
  }

  var cols = DASH.getActiveColumns();
  var th;
  th = document.createElement("th");
  th.textContent = "Test";
  th.onclick = function () {
    DASH.state.sort = "name";
    document.getElementById("sort-select").value = "name";
    DASH.renderAll();
    DASH.saveHashState();
  };
  thead.appendChild(th);
  ["Pass", "Fail", "Skip", "Rate", "Flips", "Runs"].forEach(
    function (label) {
      th = document.createElement("th");
      th.textContent = label;
      thead.appendChild(th);
    }
  );
  cols.forEach(function (c) {
    th = document.createElement("th");
    th.textContent = c.platform + "\n" + c.release;
    th.title = c.platform + " / " + c.release;
    thead.appendChild(th);
  });

  var tests = DASH.state.summary.tests || [];
  var ids = DASH.state.tests.ids || [];
  var rows = [];
  for (var i = 0; i < tests.length; i++) {
    var nodeid = ids[i] || "unknown_" + i;
    if (DASH.state.filter) {
      try {
        if (!new RegExp(DASH.state.filter).test(nodeid)) continue;
      } catch (e) {
        if (nodeid.indexOf(DASH.state.filter) === -1) continue;
      }
    }
    var displayId = DASH.state.groupParams
      ? nodeid.replace(/\[.*\]$/, "")
      : nodeid;
    var cells = tests[i] ? (tests[i].c || {}) : {};
    var totals = DASH.computeTotals(cells, cols);
    if (DASH.state.onlyFlaky && totals.flips === 0) continue;
    if (DASH.state.onlyFailing && totals.fails === 0) continue;
    rows.push({
      nodeid: nodeid,
      displayId: displayId,
      cells: cells,
      totals: totals,
      index: i,
    });
  }

  rows.sort(DASH.getComparator());
  DASH.state.rowsShown = 0;
  var frag = document.createDocumentFragment();
  var limit = Math.min(DASH.state.rowCap, rows.length);
  for (var r = 0; r < limit; r++) {
    frag.appendChild(DASH.createRow(rows[r], cols));
    DASH.state.rowsShown++;
  }
  tbody.appendChild(frag);

  if (rows.length > DASH.state.rowCap) {
    lmContainer.style.display = "block";
  } else {
    lmContainer.style.display = "none";
  }
};

DASH.getActiveColumns = function () {
  var cols = [];
  if (!DASH.state.index) return cols;
  DASH.state.index.platforms.forEach(function (p) {
    if (!DASH.state.platforms[p]) return;
    DASH.state.index.releases.forEach(function (r) {
      if (!DASH.state.releases[r.codename]) return;
      cols.push({
        platform: p,
        release: r.codename,
        key: p + "|" + r.codename,
      });
    });
  });
  return cols;
};

DASH.computeTotals = function (cells, cols) {
  var totals = { pass: 0, fail: 0, skip: 0, flips: 0, runs: 0 };
  cols.forEach(function (c) {
    var cell = cells[c.key];
    if (cell) {
      totals.pass += cell.p || 0;
      totals.fail += cell.f || 0;
      totals.skip += cell.s || 0;
      totals.flips += cell.flips || 0;
      totals.runs += cell.n || 0;
    }
  });
  totals.rate = (totals.pass + totals.fail) > 0
    ? Math.round(totals.pass * 100 / (totals.pass + totals.fail))
    : 0;
  return totals;
};

DASH.getComparator = function () {
  switch (DASH.state.sort) {
  case "fail":
    return function (a, b) { return b.totals.fail - a.totals.fail; };
  case "rate":
    return function (a, b) { return a.totals.rate - b.totals.rate; };
  case "name":
    return function (a, b) {
      return a.displayId.localeCompare(b.displayId);
    };
  case "flakiness":
  default:
    return function (a, b) {
      return b.totals.flips - a.totals.flips;
    };
  }
};

DASH.createRow = function (row, cols) {
  var tr = document.createElement("tr");
  var td;

  td = document.createElement("td");
  td.className = "nodeid-cell";
  td.textContent = DASH.shortName(row.displayId);
  td.title = row.nodeid;
  tr.appendChild(td);

  td = document.createElement("td");
  td.textContent = String(row.totals.pass);
  tr.appendChild(td);

  td = document.createElement("td");
  td.textContent = String(row.totals.fail);
  if (row.totals.fail > 0) td.style.color = "var(--fail)";
  tr.appendChild(td);

  td = document.createElement("td");
  td.textContent = String(row.totals.skip);
  tr.appendChild(td);

  td = document.createElement("td");
  var rateBar = document.createElement("span");
  rateBar.className = "rate-bar";
  var fill = document.createElement("span");
  fill.className = "rate-bar-fill";
  fill.style.width = row.totals.rate + "%";
  if (row.totals.rate < 50) {
    fill.style.background = "var(--fail)";
  }
  rateBar.appendChild(fill);
  td.appendChild(rateBar);
  td.appendChild(document.createTextNode(" " + row.totals.rate + "%"));
  tr.appendChild(td);

  td = document.createElement("td");
  td.textContent = String(row.totals.flips);
  if (row.totals.flips > 0) td.style.color = "var(--xfail)";
  tr.appendChild(td);

  td = document.createElement("td");
  td.textContent = String(row.totals.runs);
  tr.appendChild(td);

  cols.forEach(function (c) {
    td = document.createElement("td");
    td.className = "matrix-cell";
    var cell = row.cells[c.key];
    if (!cell || cell.n === 0) {
      td.className = "matrix-cell empty-cell";
      td.textContent = "\u2013";
    } else {
      td.appendChild(DASH.createSparkline(cell));
      td.onclick = function () {
        DASH.showDetail(row.nodeid, c.key, cell);
      };
    }
    tr.appendChild(td);
  });

  return tr;
};

DASH.createSparkline = function (cell) {
  var svg = document.createElementNS(
    DASH.SVG_NS, "svg"
  );
  svg.setAttribute("class", "sparkline");
  svg.setAttribute("width", "60");
  svg.setAttribute("height", "14");
  var history = cell.h || "";
  var maxLen = 15;
  if (history.length > maxLen) {
    history = history.slice(-maxLen);
  }
  for (var i = 0; i < history.length; i++) {
    var rect = document.createElementNS(
      DASH.SVG_NS, "rect"
    );
    rect.setAttribute("x", String(i * 4));
    rect.setAttribute("y", "0");
    rect.setAttribute("class", history[i]);
    rect.setAttribute(
      "title",
      DASH.OUTCOMES[history[i]]
        ? DASH.OUTCOMES[history[i]].label
        : "?"
    );
    svg.appendChild(rect);
  }
  return svg;
};

DASH.showDetail = function (nodeid, cellKey, cell) {
  var drawer = document.getElementById("detail-drawer");
  var content = document.getElementById("detail-content");
  content.textContent = "";

  var h3 = document.createElement("h3");
  h3.textContent = DASH.shortName(nodeid);
  h3.title = nodeid;
  content.appendChild(h3);

  var keyParts = cellKey.split("|");
  var p = document.createElement("p");
  p.textContent = keyParts[0] + " / " + keyParts[1];
  content.appendChild(p);

  var stats = document.createElement("p");
  stats.textContent =
    "P:" + (cell.p || 0) + " F:" + (cell.f || 0) +
    " S:" + (cell.s || 0) + " E:" + (cell.e || 0) +
    " X:" + (cell.x || 0) +
    " Rate:" + (cell.rate || 0) + "%" +
    " Flips:" + (cell.flips || 0);
  content.appendChild(stats);

  var rids = cell.rids || [];
  var history = cell.h || "";
  var ul = document.createElement("ul");
  var maxShow = Math.min(rids.length, history.length, 30);
  for (var i = 0; i < maxShow; i++) {
    var li = document.createElement("li");
    var oc = history[history.length - 1 - i];
    var label = DASH.OUTCOMES[oc]
      ? DASH.OUTCOMES[oc].label
      : "?";
    li.textContent = label + " ";
    if (rids.length > i) {
      var a = document.createElement("a");
      var runId = rids[rids.length - 1 - i];
      a.href = DASH.GITHUB_RUN_URL + runId;
      a.textContent = "run #" + runId;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      li.appendChild(a);
    }
    ul.appendChild(li);
  }
  content.appendChild(ul);

  drawer.style.display = "block";
};

DASH.shortName = function (nodeid) {
  var parts = nodeid.split("::");
  if (parts.length >= 2) {
    return parts[parts.length - 2] + "::" + parts[parts.length - 1];
  }
  return nodeid;
};

DASH.showError = function (err) {
  var body = document.querySelector("body");
  var div = document.createElement("div");
  div.textContent = "Error loading dashboard data: " + err.message;
  div.style.color = "var(--fail)";
  body.appendChild(div);
};

DASH.loadHashState = function () {
  var hash = window.location.hash.slice(1);
  if (!hash) return;
  var params = {};
  hash.split("&").forEach(function (pair) {
    var kv = pair.split("=", 2);
    if (kv.length === 2) params[kv[0]] = decodeURIComponent(kv[1]);
  });
  if (params.filter) {
    DASH.state.filter = params.filter;
    var fi = document.getElementById("filter-input");
    if (fi) fi.value = params.filter;
  }
  if (params.window) {
    DASH.state.window = params.window;
    var ws = document.getElementById("window-select");
    if (ws) ws.value = params.window;
  }
  if (params.sort) {
    DASH.state.sort = params.sort;
    var ss = document.getElementById("sort-select");
    if (ss) ss.value = params.sort;
  }
  if (params.flaky) {
    DASH.state.onlyFlaky = params.flaky === "1";
    var of = document.getElementById("only-flaky");
    if (of) of.checked = DASH.state.onlyFlaky;
  }
  if (params.failing) {
    DASH.state.onlyFailing = params.failing === "1";
    var ofa = document.getElementById("only-failing");
    if (ofa) ofa.checked = DASH.state.onlyFailing;
  }
  if (params.manual) {
    DASH.state.includeManual = params.manual === "1";
    var im = document.getElementById("include-manual");
    if (im) im.checked = DASH.state.includeManual;
  }
  if (params.merge) {
    DASH.state.groupParams = params.merge === "1";
    var gp = document.getElementById("group-params");
    if (gp) gp.checked = DASH.state.groupParams;
  }
};

DASH.saveHashState = function () {
  var parts = [];
  if (DASH.state.filter) {
    parts.push("filter=" + encodeURIComponent(DASH.state.filter));
  }
  if (DASH.state.window !== "30") {
    parts.push("window=" + DASH.state.window);
  }
  if (DASH.state.sort !== "flakiness") {
    parts.push("sort=" + DASH.state.sort);
  }
  if (DASH.state.onlyFlaky) parts.push("flaky=1");
  if (DASH.state.onlyFailing) parts.push("failing=1");
  if (DASH.state.includeManual) parts.push("manual=1");
  if (DASH.state.groupParams) parts.push("merge=1");
  window.location.hash = parts.join("&");
};

document.addEventListener("DOMContentLoaded", DASH.init);
