const SQLJS_CDN = "https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.11.0/";
const $ = (id) => document.getElementById(id);
const TABLES = {
  1: ["usr", "ordr"],
  2: ["orders"],
  3: ["product_sales"],
  4: ["orders"],
  5: ["usr", "ordr"],
  6: ["usr", "ordr"],
};

let SQLEngine;
let setupSql = "";
let data = { tasks: [], quiz: [] };
let cur = { kind: "sql", id: 1 };
let hintLv = 0;
let ptab = "desc";
let drafts = JSON.parse(localStorage.getItem("sqlsprint.drafts") || "{}");

function draftKey() {
  return cur.kind + "-" + cur.id;
}
function saveDraft() {
  const el = $("sql");
  if (!el || cur.kind !== "sql") return;
  drafts[draftKey()] = el.value;
  localStorage.setItem("sqlsprint.drafts", JSON.stringify(drafts));
}
function makeDb() {
  const db = new SQLEngine.Database();
  db.run(setupSql);
  return db;
}
function execSelects(db, sql) {
  const stmts = sql.split(";").map((s) => s.trim()).filter(Boolean);
  let last = null;
  const lines = [];
  for (const stmt of stmts) {
    try {
      const rs = db.exec(stmt);
      if (!rs.length) {
        lines.push("(无结果集)");
        continue;
      }
      const { columns, values } = rs[rs.length - 1];
      last = { columns, values };
      lines.push(columns.join(" | "));
      for (const row of values) lines.push(row.map(String).join(" | "));
    } catch (e) {
      return { error: String(e.message || e), last: null, text: lines.join("\n") };
    }
  }
  return { error: "", last, text: lines.join("\n") };
}
function cell(x) {
  if (typeof x === "number") return Math.round(x * 10000) / 10000;
  return x;
}
function normRows(values) {
  return (values || []).map((r) => r.map(cell));
}
function rowsEqual(a, b) {
  return JSON.stringify(a) === JSON.stringify(b);
}
function judge(n, sql) {
  const task = data.tasks.find((t) => t.n === n);
  if (!task) return { pass: false, message: "没有这道题", yours: "", expected: "", error: "" };
  const yoursDb = makeDb();
  const yours = execSelects(yoursDb, sql || "");
  yoursDb.close();
  if (yours.error) {
    return { pass: false, message: "SQL 执行失败", yours: yours.text, expected: "", error: yours.error };
  }
  if (!yours.last) {
    return { pass: false, message: "没有 SELECT 结果", yours: yours.text, expected: "", error: "" };
  }
  const refDb = makeDb();
  const exp = execSelects(refDb, task.ref);
  refDb.close();
  const gotN = normRows(yours.last.values);
  const expN = normRows(exp.last.values);
  if (rowsEqual(gotN, expN)) {
    return { pass: true, message: "通过（行列顺序一致）", yours: yours.text, expected: exp.text, error: "" };
  }
  const sortFn = (x, y) => JSON.stringify(x).localeCompare(JSON.stringify(y));
  if (rowsEqual([...gotN].sort(sortFn), [...expN].sort(sortFn))) {
    return { pass: false, message: "数据对了，但排序/行序不对。看题目 ORDER BY。", yours: yours.text, expected: exp.text, error: "" };
  }
  let message = "结果与标准答案不一致。对照时间窗、分母、是否含 0 用户。";
  if (gotN.length !== expN.length) {
    message = `行数不对：你 ${gotN.length} 行，标准 ${expN.length} 行。检查 JOIN 类型、时间窗、paid 过滤。`;
  } else if (gotN[0] && expN[0] && gotN[0].length !== expN[0].length) {
    message = `列数不对：你 ${gotN[0].length} 列，标准 ${expN[0].length} 列 ${exp.last.columns.join(", ")}。`;
  }
  return { pass: false, message, yours: yours.text, expected: exp.text, error: "" };
}
function preview(table, limit = 12) {
  const db = makeDb();
  const rs = db.exec(`SELECT * FROM ${table} LIMIT ${limit}`);
  const info = db.exec(`PRAGMA table_info(${table})`);
  db.close();
  if (!rs.length) return { columns: [], rows: [], schema: [] };
  return {
    columns: rs[0].columns,
    rows: rs[0].values,
    schema: info[0].values.map((r) => r[1] + " " + r[2]),
  };
}
function tableHtml(t) {
  if (!t) return "";
  let h = "<table><tr>" + t.columns.map((c) => `<th>${c}</th>`).join("") + "</tr>";
  for (const row of t.rows) h += "<tr>" + row.map((v) => `<td>${v}</td>`).join("") + "</tr>";
  return h + "</table>";
}

function allItems() {
  const items = data.tasks.map((t) => ({ kind: "sql", id: t.n, name: t.name, tags: t.tags, no: "SQL" + t.n }));
  data.quiz.forEach((q, i) => items.push({ kind: "quiz", id: i, name: q.name, tags: ["选择题"], no: "选" + (i + 1) }));
  return items;
}
function currentIndex() {
  return allItems().findIndex((x) => x.kind === cur.kind && x.id === cur.id);
}
function renderNav() {
  const written = data.tasks.filter((t) => t.n <= 3);
  const jingyan = data.tasks.filter((t) => t.n > 3);
  let html = "<h3>笔试原题</h3>";
  for (const t of written) {
    html += navBtn("sql", t.n, "SQL" + t.n, t.name, "笔试原题");
  }
  html += "<h3>面经分享</h3>";
  for (const t of jingyan) {
    html += navBtn("sql", t.n, "SQL" + t.n, t.name, "面经分享");
  }
  html += "<h3>选择题</h3>";
  data.quiz.forEach((q, i) => {
    html += navBtn("quiz", i, "选" + (i + 1), q.name, "选择题");
  });
  $("nav").innerHTML = html;
}
function navBtn(kind, id, no, name, tag) {
  const active = cur.kind === kind && cur.id === id ? "active" : "";
  const click = kind === "sql" ? `openSql(${id})` : `openQuiz(${id})`;
  return `<button class="item ${active}" onclick="${click}">
      <span class="no">${no}</span>${name}<small>${tag}</small></button>`;
}
function setTop() {
  const items = allItems();
  const i = currentIndex();
  const it = items[i];
  $("topTitle").textContent = it ? it.no + "  " + it.name : "";
  $("btnPrev").disabled = i <= 0;
  $("btnNext").disabled = i >= items.length - 1;
}
function goPrev() {
  const i = currentIndex();
  if (i <= 0) return;
  const it = allItems()[i - 1];
  it.kind === "sql" ? openSql(it.id) : openQuiz(it.id);
}
function goNext() {
  const items = allItems();
  const i = currentIndex();
  if (i >= items.length - 1) return;
  const it = items[i + 1];
  it.kind === "sql" ? openSql(it.id) : openQuiz(it.id);
}

function problemTabs() {
  return `<div class="ptabs">
    <button class="ptab ${ptab === "desc" ? "on" : ""}" onclick="setPtab('desc')">题目</button>
    <button class="ptab ${ptab === "hint" ? "on" : ""}" onclick="setPtab('hint')">提示</button>
    <button class="ptab ${ptab === "sol" ? "on" : ""}" onclick="setPtab('sol')">题解</button>
  </div>`;
}
function setPtab(name) {
  ptab = name;
  renderProblem();
}
function renderProblem() {
  if (cur.kind === "quiz") {
    const q = data.quiz[cur.id];
    const opts = q.options
      .map((o, k) => `<label><input type="radio" name="opt" value="${k}"/> ${o}</label>`)
      .join("");
    $("problemPane").innerHTML = `
      <h2 class="p-title">选${cur.id + 1} ${q.name}</h2>
      <div class="meta"><span class="tag">选择题</span></div>
      <pre class="desc">${q.q}</pre>
      <div class="quiz">${opts}</div>
      <button class="act" onclick="gradeQuiz()">提交</button>`;
    return;
  }
  const t = data.tasks.find((x) => x.n === cur.id);
  const tags = (t.tags || []).map((x) => `<span class="tag">${x}</span>`).join(" ");
  let body = "";
  if (ptab === "desc") {
    const names = TABLES[t.n] || [];
    body = `<pre class="desc">${t.desc}</pre>`;
    for (const name of names) {
      const pv = preview(name);
      body += `<div class="block"><h4>${name} 表</h4>
        <div class="muted tiny">${pv.schema.join(" · ")}</div>${tableHtml(pv)}</div>`;
    }
  } else if (ptab === "hint") {
    body = (t.hints || []).map((h) => `<div class="hint-line">${h}</div>`).join("") || "<p class='muted'>暂无提示</p>";
  } else {
    body = `<p class="muted">先自己写。看完请再默写一遍。</p><pre class="ref">${t.ref}</pre>`;
  }
  $("problemPane").innerHTML = `
    <h2 class="p-title">SQL${t.n} ${t.name}</h2>
    <div class="meta">${tags}</div>
    ${problemTabs()}
    ${body}`;
}

function setWorkspaceSql(on) {
  $("editorWrap").classList.toggle("hidden", !on);
  $("quizEditor").classList.toggle("on", !on);
  $("sql").disabled = !on;
  const runBtns = document.querySelector(".console-bar .ghost").parentElement;
  document.querySelectorAll(".console-bar .ghost, .console-bar .act").forEach((b) => {
    if (b.textContent.includes("自测") || b.textContent.includes("保存")) {
      b.style.display = on ? "" : "none";
    }
  });
}

function openSql(n) {
  saveDraft();
  cur = { kind: "sql", id: n };
  hintLv = 0;
  ptab = "desc";
  setWorkspaceSql(true);
  $("sql").value = drafts[draftKey()] || "";
  renderNav();
  setTop();
  renderProblem();
  setConsole("写完 SQL 后点「自测运行」看输出，或「保存并提交」对照标准答案。", "");
}

function openQuiz(i) {
  saveDraft();
  cur = { kind: "quiz", id: i };
  ptab = "desc";
  setWorkspaceSql(false);
  renderNav();
  setTop();
  renderProblem();
  setConsole("左侧选择答案后点提交。", "");
}

function setConsole(text, cls) {
  const el = $("consoleBody");
  el.className = "console-body " + (cls || "muted");
  el.textContent = text;
}
function showConsole() {}

function runTest() {
  if (cur.kind !== "sql") return;
  saveDraft();
  const db = makeDb();
  const out = execSelects(db, $("sql").value);
  db.close();
  if (out.error) setConsole("报错: " + out.error, "msg-bad");
  else setConsole(out.text || "(无结果)", "");
}
function runJudge() {
  if (cur.kind !== "sql") return;
  saveDraft();
  const r = judge(cur.id, $("sql").value);
  const extra = r.pass
    ? "\n\n" + r.yours
    : "\n\n--- 你的输出 ---\n" + (r.yours || "") + "\n\n--- 标准输出 ---\n" + (r.expected || "");
  setConsole(r.message + (r.error ? " | " + r.error : "") + extra, r.pass ? "msg-ok" : "msg-bad");
}
function resetSql() {
  $("sql").value = "";
  saveDraft();
}
function gradeQuiz() {
  const sel = document.querySelector("input[name=opt]:checked");
  if (!sel) {
    setConsole("先选一个选项。", "msg-bad");
    return;
  }
  const q = data.quiz[cur.id];
  const pick = q.options[Number(sel.value)];
  const ok = pick === q.answer;
  setConsole((ok ? "正确。 " : "不对。答案是「" + q.answer + "」。 ") + q.explain, ok ? "msg-ok" : "msg-bad");
}

(async () => {
  try {
    SQLEngine = await initSqlJs({ locateFile: (f) => SQLJS_CDN + f });
    const [qRes, sRes] = await Promise.all([fetch("questions.json?v=4"), fetch("setup.sql?v=4")]);
    data = await qRes.json();
    setupSql = await sRes.text();
    $("sql").addEventListener("input", saveDraft);
    openSql(1);
  } catch (e) {
    $("problemPane").innerHTML = `<p class="msg-bad">加载失败：${e}</p>`;
  }
})();
