#!/usr/bin/env python3
"""本地练习应用: 浏览器写 SQL、分层提示、自动判题。python app.py"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

import check

HOST, PORT = "127.0.0.1", 8765

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>SQL Sprint · Temu 增长岗</title>
<style>
  :root { --bg:#0f1419; --panel:#1a2332; --line:#2a3a4f; --txt:#e7eef8; --muted:#8aa0b8;
          --acc:#3d9cf0; --ok:#3ecf8e; --bad:#f07178; --warn:#e6c07b; }
  * { box-sizing:border-box; }
  body { margin:0; font-family: "Segoe UI", "PingFang SC", sans-serif; background:var(--bg); color:var(--txt); }
  header { padding:14px 20px; border-bottom:1px solid var(--line); display:flex; gap:16px; align-items:baseline; }
  header h1 { font-size:16px; margin:0; font-weight:600; }
  header span { color:var(--muted); font-size:13px; }
  .layout { display:grid; grid-template-columns: 240px 1fr 320px; height:calc(100vh - 52px); }
  nav { border-right:1px solid var(--line); overflow:auto; padding:10px; }
  nav h3 { font-size:11px; color:var(--muted); letter-spacing:.08em; margin:12px 8px 6px; }
  .item { display:block; width:100%; text-align:left; background:transparent; border:0; color:var(--txt);
          padding:10px 10px; border-radius:8px; cursor:pointer; font-size:13px; }
  .item:hover { background:#243044; }
  .item.active { background:#1e3a5f; }
  .item small { display:block; color:var(--muted); margin-top:3px; font-size:11px; }
  main { padding:16px 18px; overflow:auto; display:flex; flex-direction:column; gap:10px; }
  pre.desc { white-space:pre-wrap; background:var(--panel); border:1px solid var(--line); border-radius:10px;
             padding:12px 14px; margin:0; font-size:13px; line-height:1.5; color:#c5d4e8; }
  textarea { width:100%; min-height:220px; background:#0c1118; color:#d6e4f5; border:1px solid var(--line);
             border-radius:10px; padding:12px; font-family: Consolas, "Cascadia Mono", monospace; font-size:13px; }
  .bar { display:flex; gap:8px; flex-wrap:wrap; }
  button.act { background:var(--acc); color:#041018; border:0; padding:8px 14px; border-radius:8px;
               font-weight:600; cursor:pointer; }
  button.ghost { background:transparent; color:var(--txt); border:1px solid var(--line); padding:8px 14px;
                 border-radius:8px; cursor:pointer; }
  .msg { padding:10px 12px; border-radius:8px; font-size:13px; }
  .ok { background:#143326; color:var(--ok); }
  .bad { background:#3a1d22; color:var(--bad); }
  .info { background:var(--panel); color:var(--warn); }
  aside { border-left:1px solid var(--line); overflow:auto; padding:12px; font-size:12px; }
  aside h3 { margin:8px 0 6px; font-size:12px; color:var(--muted); }
  table { width:100%; border-collapse:collapse; font-size:11px; }
  th, td { border:1px solid var(--line); padding:4px 6px; text-align:left; }
  th { color:var(--muted); }
  .out { background:#0c1118; border:1px solid var(--line); border-radius:8px; padding:10px;
         white-space:pre-wrap; font-family: Consolas, monospace; font-size:12px; max-height:220px; overflow:auto; }
  .quiz label { display:block; background:var(--panel); border:1px solid var(--line); border-radius:8px;
                padding:8px 10px; margin:6px 0; cursor:pointer; }
</style>
</head>
<body>
<header>
  <h1>SQL Sprint</h1>
  <span>Temu 用户增长 · 激活 7 日 / Cohort / 窗口函数 · 本地判题</span>
</header>
<div class="layout">
  <nav id="nav"></nav>
  <main id="main"></main>
  <aside>
    <h3>表结构</h3>
    <pre id="schema" class="out" style="max-height:none"></pre>
    <h3>usr 预览</h3>
    <div id="t_usr"></div>
    <h3>ordr 预览</h3>
    <div id="t_ordr"></div>
  </aside>
</div>
<script>
const $ = id => document.getElementById(id);
let data = { tasks: [], quiz: [] };
let cur = { kind: "sql", id: 1 };
let hintLv = 0;

async function api(path, body) {
  const opt = body ? { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(body) } : {};
  const r = await fetch(path, opt);
  return r.json();
}

function tableHtml(t) {
  if (!t) return "";
  let h = "<table><tr>" + t.columns.map(c => `<th>${c}</th>`).join("") + "</tr>";
  for (const row of t.rows) h += "<tr>" + row.map(v => `<td>${v}</td>`).join("") + "</tr>";
  return h + "</table>";
}

function renderNav() {
  let html = "<h3>SQL 题</h3>";
  for (const t of data.tasks) {
    html += `<button class="item ${cur.kind==="sql"&&cur.id===t.n?"active":""}" onclick="openSql(${t.n})">
      ${t.n}. ${t.name}<small>${(t.tags||[]).join(" · ")}</small></button>`;
  }
  html += "<h3>口述 / 概率</h3>";
  data.quiz.forEach((q,i) => {
    html += `<button class="item ${cur.kind==="quiz"&&cur.id===i?"active":""}" onclick="openQuiz(${i})">
      ${q.name}</button>`;
  });
  $("nav").innerHTML = html;
}

function openSql(n) {
  cur = { kind:"sql", id:n }; hintLv = 0; renderNav();
  const t = data.tasks.find(x => x.n===n);
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
  cur = { kind:"quiz", id:i }; renderNav();
  const q = data.quiz[i];
  const opts = q.options.map((o,k) =>
    `<label><input type="radio" name="opt" value="${k}"/> ${o}</label>`).join("");
  $("main").innerHTML = `
    <pre class="desc">${q.q}</pre>
    <div class="quiz">${opts}</div>
    <div class="bar"><button class="act" onclick="gradeQuiz()">提交</button></div>
    <div id="verdict"></div>
  `;
}

async function runJudge() {
  const sql = $("sql").value;
  const r = await api("/api/judge", { n: cur.id, sql });
  const v = $("verdict");
  v.className = "msg " + (r.pass ? "ok" : "bad");
  v.textContent = r.message + (r.error ? " | " + r.error : "");
  const y = $("yours");
  y.style.display = "block";
  y.textContent = "你的输出\n" + (r.yours || "") + (r.pass ? "" : "\n\n标准输出\n" + (r.expected||""));
}

async function showHint() {
  const t = data.tasks.find(x => x.n===cur.id);
  hintLv = Math.min(hintLv + 1, t.hints.length);
  const el = $("hint");
  el.style.display = "block";
  el.textContent = t.hints.slice(0, hintLv).join("\n");
}

async function showRef() {
  const r = await api("/api/ref", { n: cur.id });
  const y = $("yours");
  y.style.display = "block";
  y.textContent = r.sql + "\n\n--- 输出 ---\n" + r.out;
}

async function gradeQuiz() {
  const sel = document.querySelector("input[name=opt]:checked");
  const v = $("verdict");
  if (!sel) { v.className="msg bad"; v.textContent="先选一个"; return; }
  const q = data.quiz[cur.id];
  const pick = q.options[Number(sel.value)];
  const ok = pick === q.answer;
  v.className = "msg " + (ok ? "ok" : "bad");
  v.textContent = (ok ? "正确。 " : "不对。答案是「" + q.answer + "」。 ") + q.explain;
}

(async () => {
  data = await api("/api/meta");
  $("schema").textContent = data.schema;
  $("t_usr").innerHTML = tableHtml(data.preview.usr);
  $("t_ordr").innerHTML = tableHtml(data.preview.ordr);
  renderNav();
  openSql(1);
})();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))

    def _json(self, obj, code=200):
        raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _html(self, text):
        raw = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._html(HTML)
            return
        if path == "/api/meta":
            tasks = []
            for n, t in check.TASKS.items():
                tasks.append(
                    {
                        "n": n,
                        "name": t["name"],
                        "desc": t["desc"].strip(),
                        "tags": t.get("tags", []),
                        "hints": check.HINTS[n],
                    }
                )
            self._json(
                {
                    "tasks": tasks,
                    "quiz": check.QUIZ,
                    "schema": check.schema_text(),
                    "preview": {
                        "usr": check.preview_table("usr"),
                        "ordr": check.preview_table("ordr"),
                    },
                }
            )
            return
        self._json({"error": "not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        if path == "/api/judge":
            self._json(check.judge(int(body["n"]), body.get("sql") or ""))
            return
        if path == "/api/ref":
            nq = int(body["n"])
            sql = check.TASKS[nq]["ref"]
            self._json({"sql": sql.strip(), "out": check.fmt(check.run_sql(sql))})
            return
        self._json({"error": "not found"}, 404)


def main():
    httpd = HTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}/"
    print("练习应用:", url, flush=True)
    print("浏览器打开后左侧选题，中间写 SQL，右侧看表。Ctrl+C 结束。")
    try:
        import webbrowser

        webbrowser.open(url)
    except Exception:
        pass
    httpd.serve_forever()


if __name__ == "__main__":
    main()
