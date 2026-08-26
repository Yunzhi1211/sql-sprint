const SQLJS_CDN = "https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.11.0/";
const $ = (id) => document.getElementById(id);

let SQLEngine;
let setupSql = "";
let data = { tasks: [], quiz: [] };
let cur = { kind: "sql", id: 1 };
let hintLv = 0;

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
    return {
      pass: false,
      message: "数据对了，但排序/行序不对。看题目 ORDER BY。",
      yours: yours.text,
      expected: exp.text,
      error: "",
    };
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
  db.close();
  if (!rs.length) return { columns: [], rows: [] };
  return { columns: rs[0].columns, rows: rs[0].values };
}

function schemaText() {
  const db = makeDb();
  const names = ["usr", "ordr", "orders", "product_sales"];
  const parts = [];
  for (const table of names) {
    const info = db.exec(`PRAGMA table_info(${table})`);
    const cols = info[0].values.map((r) => `${r[1]} ${r[2]}`).join(", ");
    const n = db.exec(`SELECT COUNT(*) FROM ${table}`)[0].values[0][0];
    parts.push(`${table} (${n} rows): ${cols}`);
  }
  db.close();
  return parts.join("\n");
}

function tableHtml(t) {
  if (!t) return "";
  let h = "<table><tr>" + t.columns.map((c) => `<th>${c}</th>`).join("") + "</tr>";
  for (const row of t.rows) h += "<tr>" + row.map((v) => `<td>${v}</td>`).join("") + "</tr>";
  return h + "</table>";
}

function renderNav() {
  let html = "<h3>SQL 题</h3>";
  for (const t of data.tasks) {
    html += `<button class="item ${cur.kind === "sql" && cur.id === t.n ? "active" : ""}" onclick="openSql(${t.n})">
      ${t.n}. ${t.name}<small>${(t.tags || []).join(" · ")}</small></button>`;
  }
  html += "<h3>口述 / 概率</h3>";
  data.quiz.forEach((q, i) => {
    html += `<button class="item ${cur.kind === "quiz" && cur.id === i ? "active" : ""}" onclick="openQuiz(${i})">
      ${q.name}</button>`;
  });
  $("nav").innerHTML = html;
}

function openSql(n) {
  cur = { kind: "sql", id: n };
  hintLv = 0;
  renderNav();
  const t = data.tasks.find((x) => x.n === n);
  $("main").innerHTML = `
    <pre class="desc">${t.desc}</pre>
    <textarea id="sql" placeholder="在此写 SQL，方言是 SQLite（date(x,'+6 days'), strftime, AVG() OVER）"></textarea>
    <div class="bar">
      <button class="act" onclick="runJudge()">运行并判题</button>
      <button class="ghost" onclick="showHint()">下一层提示</button>
      <button class="ghost" onclick="showRef()">看参考答案</button>
    </div>
    <div id="hint" class="msg info" style="display:none"></div>
    <div id="verdict"></div>
    <div id="yours" class="out" style="display:none"></div>
  `;
}

function openQuiz(i) {
  cur = { kind: "quiz", id: i };
  renderNav();
  const q = data.quiz[i];
  const opts = q.options
    .map((o, k) => `<label><input type="radio" name="opt" value="${k}"/> ${o}</label>`)
    .join("");
  $("main").innerHTML = `
    <pre class="desc">${q.q}</pre>
    <div class="quiz">${opts}</div>
    <div class="bar"><button class="act" onclick="gradeQuiz()">提交</button></div>
    <div id="verdict"></div>
  `;
}

function runJudge() {
  const sql = $("sql").value;
  const r = judge(cur.id, sql);
  const v = $("verdict");
  v.className = "msg " + (r.pass ? "ok" : "bad");
  v.textContent = r.message + (r.error ? " | " + r.error : "");
  const y = $("yours");
  y.style.display = "block";
  y.textContent = "你的输出\n" + (r.yours || "") + (r.pass ? "" : "\n\n标准输出\n" + (r.expected || ""));
}

function showHint() {
  const t = data.tasks.find((x) => x.n === cur.id);
  hintLv = Math.min(hintLv + 1, t.hints.length);
  const el = $("hint");
  el.style.display = "block";
  el.textContent = t.hints.slice(0, hintLv).join("\n");
}

function showRef() {
  const t = data.tasks.find((x) => x.n === cur.id);
  const db = makeDb();
  const out = execSelects(db, t.ref);
  db.close();
  const y = $("yours");
  y.style.display = "block";
  y.textContent = t.ref + "\n\n--- 输出 ---\n" + out.text;
}

function gradeQuiz() {
  const sel = document.querySelector("input[name=opt]:checked");
  const v = $("verdict");
  if (!sel) {
    v.className = "msg bad";
    v.textContent = "先选一个";
    return;
  }
  const q = data.quiz[cur.id];
  const pick = q.options[Number(sel.value)];
  const ok = pick === q.answer;
  v.className = "msg " + (ok ? "ok" : "bad");
  v.textContent = (ok ? "正确。 " : "不对。答案是「" + q.answer + "」。 ") + q.explain;
}

(async () => {
  try {
    SQLEngine = await initSqlJs({ locateFile: (f) => SQLJS_CDN + f });
    const [qRes, sRes] = await Promise.all([fetch("questions.json"), fetch("setup.sql")]);
    data = await qRes.json();
    setupSql = await sRes.text();
    $("schema").textContent = schemaText();
    $("t_usr").innerHTML = tableHtml(preview("usr"));
    $("t_ordr").innerHTML = tableHtml(preview("ordr"));
    renderNav();
    openSql(1);
  } catch (e) {
    $("main").innerHTML = `<div class="msg bad">加载失败：${e}</div>`;
  }
})();
