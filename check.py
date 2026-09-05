#!/usr/bin/env python3
"""
PDD SQL 突击训练 - 判题器 (内存 SQLite)

用法:
    python check.py              # 看全部参考答案输出
    python check.py 1            # 只看第1题
    python check.py hint 1       # 第1题分层提示
    python check.py 1 my.sql     # 用你的答案文件判题
    python check.py run 1 my.sql # 同上
    python app.py                # 打开浏览器练习应用
"""
import json
import sqlite3
import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.abspath(__file__))
SETUP = os.path.join(ROOT, "setup.sql")


def new_db():
    con = sqlite3.connect(":memory:", check_same_thread=False)
    with open(SETUP, encoding="utf-8") as f:
        con.executescript(f.read())
    return con


CONN = new_db()
CUR = CONN.cursor()


def q(query):
    try:
        rows = CUR.execute(query).fetchall()
        cols = [d[0] for d in CUR.description] if CUR.description else []
        print(" | ".join(cols))
        print("-" * 60)
        for r in rows:
            print(" | ".join(str(x) for x in r))
    except Exception as e:
        print("报错:", e)


def reset():
    global CONN, CUR
    CONN = new_db()
    CUR = CONN.cursor()
    print("数据库已重置")


TASKS = {
    1: {
        "name": "用户激活7日支付总额 & 下单次数 & 来源均值差值",
        "tags": ["笔试原题", "窗口函数", "时间窗"],
        "desc": """
usr 表 + ordr 表。
计算每个用户：① 激活后 7 天内支付总额 ② 下单次数
③ 该用户 7 日支付总额 与 其所在来源(source)所有用户 7 日平均支付总额 的差值。
返回: user_id, source, pay_7d, order_cnt, source_avg_pay_7d, diff
  """,
        "ref": """
WITH user_7d AS (
    SELECT
        u.user_id,
        u.source,
        COALESCE(SUM(CASE WHEN o.status = 'paid' THEN o.ordr_amt END), 0) AS pay_7d,
        COUNT(CASE WHEN o.status = 'paid' THEN o.order_id END) AS order_cnt
    FROM usr u
    LEFT JOIN ordr o
      ON u.user_id = o.user_id
     AND o.order_date >= u.reg_date
     AND o.order_date <= date(u.reg_date, '+6 days')
    GROUP BY u.user_id, u.source
)
SELECT
    user_id,
    source,
    pay_7d,
    order_cnt,
    AVG(pay_7d) OVER (PARTITION BY source) AS source_avg_pay_7d,
    pay_7d - AVG(pay_7d) OVER (PARTITION BY source) AS diff
FROM user_7d
ORDER BY user_id;
  """,
    },
    2: {
        "name": "Cohort 留存分析 (month_0 ~ month_3)",
        "tags": ["笔试原题", "透视", "日期差"],
        "desc": """
【笔试题】orders 表。每个用户首次下单月为 cohort_month，
统计每个 cohort 在第 0/1/2/3 月仍有下单的去重用户数。
返回: cohort_month, month_0, month_1, month_2, month_3
  """,
        "ref": """
WITH first_m AS (
    SELECT user_id, MIN(strftime('%Y-%m', order_date)) AS cohort_month
    FROM orders GROUP BY user_id
),
activity AS (
    SELECT o.user_id, f.cohort_month,
           (strftime('%Y', o.order_date) - substr(f.cohort_month,1,4))*12
         + (strftime('%m', o.order_date) - substr(f.cohort_month,6,2)) AS month_diff
    FROM orders o JOIN first_m f USING(user_id)
)
SELECT cohort_month,
       COUNT(DISTINCT CASE WHEN month_diff=0 THEN user_id END) AS month_0,
       COUNT(DISTINCT CASE WHEN month_diff=1 THEN user_id END) AS month_1,
       COUNT(DISTINCT CASE WHEN month_diff=2 THEN user_id END) AS month_2,
       COUNT(DISTINCT CASE WHEN month_diff=3 THEN user_id END) AS month_3
FROM activity
WHERE month_diff BETWEEN 0 AND 3
GROUP BY cohort_month ORDER BY cohort_month;
  """,
    },
    3: {
        "name": "DENSE_RANK 销量 Top3",
        "tags": ["笔试原题", "排名"],
        "desc": """
【笔试题】product_sales。用 DENSE_RANK 取销量排名前 3 的商品。
返回: product_name, sales_cnt, rnk，按 rnk, product_id 排序。
并列不跳号；前 3 名有并列时行数可以 > 3。
  """,
        "ref": """
SELECT product_name, sales_cnt, rnk
FROM (
    SELECT product_id, product_name, sales_cnt,
           DENSE_RANK() OVER (ORDER BY sales_cnt DESC) AS rnk
    FROM product_sales
) ranked
WHERE rnk <= 3
ORDER BY rnk, product_id;
  """,
    },
    4: {
        "name": "连续活跃天数",
        "tags": ["面经分享", "日期-行号"],
        "desc": """
orders 表。找出 2026-01 内连续活跃（下单）>=2 天的用户片段。
返回: user_id, consec_days，按 user_id 排序。
  """,
        "ref": """
WITH d AS (
    SELECT DISTINCT user_id, order_date
    FROM orders WHERE order_date BETWEEN '2026-01-01' AND '2026-01-31'
),
g AS (
    SELECT user_id, order_date,
           date(order_date,'-'||(row_number() OVER (PARTITION BY user_id ORDER BY order_date))||' days') AS grp
    FROM d
)
SELECT user_id, COUNT(*) AS consec_days
FROM g GROUP BY user_id, grp
HAVING COUNT(*) >= 2
ORDER BY user_id;
  """,
    },
    5: {
        "name": "按来源：7日转化率与人均 GMV",
        "tags": ["面经分享", "异动下钻"],
        "desc": """
基于 usr + ordr。
按 source 统计：
- users: 该来源用户数
- pay_users: 激活 7 日内至少 1 笔 paid 的用户数
- cvr_7d: 7 日转化率 = pay_users / users
- gmv_7d: 7 日内 paid 总额
- arpu_7d: 7 日人均 GMV = gmv_7d / users（注意分母是全部用户不是付费用户）

时间窗、paid 口径与第 1 题相同。
返回: source, users, pay_users, cvr_7d, gmv_7d, arpu_7d，按 gmv_7d 降序。
  """,
        "ref": """
WITH user_7d AS (
    SELECT
        u.user_id,
        u.source,
        COALESCE(SUM(CASE WHEN o.status = 'paid' THEN o.ordr_amt END), 0) AS pay_7d
    FROM usr u
    LEFT JOIN ordr o
      ON u.user_id = o.user_id
     AND o.order_date >= u.reg_date
     AND o.order_date <= date(u.reg_date, '+6 days')
    GROUP BY u.user_id, u.source
)
SELECT
    source,
    COUNT(*) AS users,
    SUM(CASE WHEN pay_7d > 0 THEN 1 ELSE 0 END) AS pay_users,
    1.0 * SUM(CASE WHEN pay_7d > 0 THEN 1 ELSE 0 END) / COUNT(*) AS cvr_7d,
    SUM(pay_7d) AS gmv_7d,
    1.0 * SUM(pay_7d) / COUNT(*) AS arpu_7d
FROM user_7d
GROUP BY source
ORDER BY gmv_7d DESC;
  """,
    },
    6: {
        "name": "激活后次日复购（D1）",
        "tags": ["面经分享", "留存"],
        "desc": """
usr + ordr。用户激活日为 D0。
统计每个 source：
- users
- d1_users: 激活次日（reg_date+1）有 paid 订单的去重用户数
- d1_rate: d1_users / users

返回: source, users, d1_users, d1_rate，按 source 排序。
  """,
        "ref": """
SELECT
    u.source,
    COUNT(DISTINCT u.user_id) AS users,
    COUNT(DISTINCT CASE WHEN o.status = 'paid' THEN u.user_id END) AS d1_users,
    1.0 * COUNT(DISTINCT CASE WHEN o.status = 'paid' THEN u.user_id END)
        / COUNT(DISTINCT u.user_id) AS d1_rate
FROM usr u
LEFT JOIN ordr o
  ON u.user_id = o.user_id
 AND o.order_date = date(u.reg_date, '+1 day')
GROUP BY u.source
ORDER BY u.source;
  """,
    },
}

HINTS = {
    1: [
        "[1] 激活日 = usr.reg_date，不要用 MIN(order_date) 顶替；两张表都给了就是让你 JOIN。没下单用户也要保留。",
        "[2] 时间窗：reg_date <= order_date <= reg_date+6 天（含激活当天共 7 天）。日期条件写在 ON 上，写在 WHERE 会把 LEFT JOIN 打成 INNER。",
        "[3] 支付总额只计 status='paid'。SUM(CASE WHEN status='paid' THEN ordr_amt END)，cancel 那笔不能进。",
        "[4] 无订单用户 pay_7d=0。差值：pay_7d - AVG(pay_7d) OVER (PARTITION BY source)，是渠道内「用户 7 日 GMV」的平均，不是订单金额的平均。",
    ],
    2: [
        "[1] Cohort 三步：首单月 → 每笔相对月份差 → COUNT DISTINCT + CASE 透视。",
        "[2] SQLite 无 TIMESTAMPDIFF，用 (年差)*12 + 月差。",
        "[3] COUNT(DISTINCT CASE WHEN month_diff=0 THEN user_id END) 是固定写法。",
        "[4] month_0 应等于该 cohort 总用户数，可自检。",
    ],
    3: [
        "[1] DENSE_RANK 并列不跳号；RANK 会跳号；ROW_NUMBER 永不并列。",
        "[2] 窗口函数不能直接 WHERE rnk<=3，要包一层子查询。",
        "[3] ORDER BY rnk, product_id。",
        "[4] 并列时行数可以多于 3，面试要主动说清。",
    ],
    4: [
        "[1] 连续天数：日期减去行号，差值相同就是同一段连续。",
        "[2] 先 DISTINCT 去掉同一天多单。",
        "[3] date(order_date, '-' || rn || ' days') 做分组键。",
        "[4] HAVING COUNT(*) >= 2 筛连续片段。",
    ],
    5: [
        "[1] 先做成「用户 × 7日 GMV」一人一行，再按 source 聚合。",
        "[2] 转化率分母是全部用户；ARPU 本题要求分母也是全部用户（含 0）。",
        "[3] 付费用户：pay_7d > 0。不要用 COUNT(订单) 当用户数。",
        "[4] 1.0 * 整数 / 整数，避免 SQLite 整除变 0。",
    ],
    6: [
        "[1] D1 = order_date 恰好等于 date(reg_date,'+1 day')，不是 7 日窗。",
        "[2] LEFT JOIN，没次日订单的来源 users 仍要在。",
        "[3] COUNT(DISTINCT CASE WHEN paid THEN user_id) 计 D1 用户。",
        "[4] 和「7 日内任意一天复购」不是同一指标，面试别混。",
    ],
}

QUIZ = [
    {
        "id": "p1",
        "name": "甲乙箱次品",
        "q": "甲箱 3 正 3 次，乙箱 3 正。从甲随机取 3 件放入乙，再从乙随机抽 1 件，是次品的概率？",
        "options": ["1/6", "1/4", "1/3", "1/2"],
        "answer": "1/4",
        "explain": "全概率（超几何）：转入 k 件次品后从乙 6 件中抽到次品的概率为 k/6。P=0+9/120+18/120+3/120=1/4。巧记：必须抽到转入的 3 件(3/6)×转入件是次品(3/6)=1/4。",
    },
    {
        "id": "p2",
        "name": "A/B 实验周期",
        "q": "A/B 实验周期怎么定，下列哪条最完整？",
        "options": [
            "跑满 3 天就够，看 p 值小于 0.05 即可停",
            "先算样本量（MDE+功效），再至少覆盖 1 个完整周周期，避免周末效应，不peeking提前停",
            "谁先达到显著谁赢，随时看后台",
            "周期越长越好，至少跑两个月",
        ],
        "answer": "先算样本量（MDE+功效），再至少覆盖 1 个完整周周期，避免周末效应，不peeking提前停",
        "explain": "样本量由 MDE、α、功效事先算好；业务有周周期必须含完整周；反复偷看 p 值会抬高一类错误。",
    },
    {
        "id": "p3",
        "name": "p 值含义",
        "q": "在原假设 H0 为真的前提下，p 值最准确的含义是？",
        "options": [
            "实验成功（方案更好）的概率",
            "H0 为真的概率",
            "若 H0 为真，得到当前结果或更极端结果的概率",
            "效应量有多大",
        ],
        "answer": "若 H0 为真，得到当前结果或更极端结果的概率",
        "explain": "p 不是「方案赢了的概率」，也不是效应大小。p 小只说明「这么极端不太像随机」，效应要看提升幅度和置信区间。",
    },
    {
        "id": "p4",
        "name": "一类错误与二类错误",
        "q": "A/B 测试里，把「其实没差异」判成「有显著差异」，属于？",
        "options": [
            "一类错误（假阳性，α）",
            "二类错误（假阴性，β）",
            "功效不足",
            "辛普森悖论",
        ],
        "answer": "一类错误（假阳性，α）",
        "explain": "一类错误：冤枉（无效果却上线）。二类错误：漏掉真效果。功效=1-β。peeking、多重比较会抬高一类错误。",
    },
    {
        "id": "p5",
        "name": "相关与因果",
        "q": "两个指标 Pearson 相关系数 r=0.8，可以得出？",
        "options": [
            "二者一定存在因果关系",
            "二者有较强线性相关，但不能直接当因果",
            "二者完全独立",
            "一定是非线性关系",
        ],
        "answer": "二者有较强线性相关，但不能直接当因果",
        "explain": "Pearson 只刻画线性相关。因果需要实验或识别策略。增长岗常问：相关≠因果。",
    },
    {
        "id": "p6",
        "name": "均值还是中位数",
        "q": "用户客单价严重右偏（少数大额订单），描述「典型用户花多少」更稳妥的是？",
        "options": ["均值", "中位数", "众数一定最好", "极差"],
        "answer": "中位数",
        "explain": "右偏时均值被头部大单拉高。异常值多、长尾用中位数；要对齐 GMV 总额时仍看均值/总和。",
    },
    {
        "id": "p7",
        "name": "疾病检测贝叶斯",
        "q": "某病患病率 1%。检测真阳性率 99%，假阳性率 1%。随机一人检测阳性，真正患病的概率最接近？",
        "options": ["99%", "50%", "1%", "90%"],
        "answer": "50%",
        "explain": "10000 人中约 100 真患者（约 99 检出），9900 健康人中约 99 假阳性。阳性里真病 ≈99/(99+99)=50%。低患病率会稀释阳性预测值。",
    },
    {
        "id": "p8",
        "name": "辛普森悖论",
        "q": "整体转化率实验组更高，但分男女看对照组都更高。最可能是？",
        "options": [
            "一定是数据算错",
            "辛普森悖论：分组结构不同，总体趋势可与分层相反",
            "p 值一定小于 0.05",
            "必须用均值而不是转化率",
        ],
        "answer": "辛普森悖论：分组结构不同，总体趋势可与分层相反",
        "explain": "分流不均或人群结构不同会导致总体与分层结论相反。A/B 要做 SRM 检查，并看关键分层。",
    },
    {
        "id": "p9",
        "name": "RANK 与 DENSE_RANK",
        "q": "销量并列第一的两件商品，下一名用 DENSE_RANK 应是？",
        "options": ["1", "2", "3", "随机"],
        "answer": "2",
        "explain": "DENSE_RANK 并列不跳号：1,1,2。RANK 跳号：1,1,3。ROW_NUMBER 永不并列。",
    },
    {
        "id": "p10",
        "name": "留存分母",
        "q": "计算 D7 留存率，分母通常应是？",
        "options": [
            "第 7 天还在的用户",
            "当天活跃用户",
            "队列起始日的新增/激活用户（且已满 7 天观察窗）",
            "历史全部注册用户",
        ],
        "answer": "队列起始日的新增/激活用户（且已满 7 天观察窗）",
        "explain": "留存是队列指标：分母是同一天进入的用户，且必须已过观察窗口，否则未满 7 天的人会把留存算低。",
    },
]


def schema_text(con=None):
    own = con is None
    con = con or new_db()
    cur = con.cursor()
    parts = []
    for table in ["usr", "ordr", "orders", "product_sales"]:
        cols = cur.execute(f"PRAGMA table_info({table})").fetchall()
        col_s = ", ".join(f"{c[1]} {c[2]}" for c in cols)
        n = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        parts.append(f"{table} ({n} rows): {col_s}")
    if own:
        con.close()
    return "\n".join(parts)


def run_sql(sql, con=None):
    con = con or CONN
    cur = con.cursor()
    out = []
    for stmt in [s for s in sql.split(";") if s.strip()]:
        try:
            rows = cur.execute(stmt).fetchall()
            cols = [d[0] for d in cur.description] if cur.description else []
            out.append(("OK", cols, rows))
        except Exception as e:
            out.append(("ERR", str(e), []))
    return out


def last_select(out):
    selects = [x for x in out if x[0] == "OK" and x[1]]
    return selects[-1] if selects else None


def cell(x):
    if x is None:
        return None
    if isinstance(x, float):
        return round(x, 4)
    if isinstance(x, int):
        return x
    try:
        return round(float(x), 4)
    except (TypeError, ValueError):
        return str(x)


def norm_rows(rows):
    return [tuple(cell(v) for v in r) for r in rows]


def fmt(out):
    s = []
    for tag, cols, rows in out:
        if tag == "ERR":
            s.append("报错: " + cols)
            continue
        if cols:
            s.append(" | ".join(cols))
        for r in rows:
            s.append(" | ".join(str(x) for x in r))
    return "\n".join(s)


def judge(n, sql):
    """在隔离的内存库上判题。返回 dict: pass, message, yours, expected, error."""
    if n not in TASKS:
        return {"pass": False, "message": "没有这道题", "yours": "", "expected": "", "error": ""}
    con = new_db()
    yours_out = run_sql(sql, con)
    err = next((c for t, c, _ in yours_out if t == "ERR"), None)
    if err:
        return {"pass": False, "message": "SQL 执行失败", "yours": fmt(yours_out), "expected": "", "error": err}

    got = last_select(yours_out)
    if not got:
        return {"pass": False, "message": "没有 SELECT 结果", "yours": fmt(yours_out), "expected": "", "error": ""}

    ref_out = run_sql(TASKS[n]["ref"], new_db())
    _, exp_cols, exp_rows = last_select(ref_out)
    _, got_cols, got_rows = got

    exp_n, got_n = norm_rows(exp_rows), norm_rows(got_rows)
    expected_s = fmt(ref_out)
    yours_s = fmt(yours_out)

    if got_n == exp_n:
        return {"pass": True, "message": "通过（行列顺序一致）", "yours": yours_s, "expected": expected_s, "error": ""}
    if sorted(got_n) == sorted(exp_n):
        return {
            "pass": False,
            "message": "数据对了，但排序/行序不对。看题目 ORDER BY。",
            "yours": yours_s,
            "expected": expected_s,
            "error": "",
        }
    if len(got_n) != len(exp_n):
        msg = f"行数不对：你 {len(got_n)} 行，标准 {len(exp_n)} 行。检查 JOIN 类型、时间窗、paid 过滤。"
    elif got_n and exp_n and len(got_n[0]) != len(exp_n[0]):
        msg = f"列数不对：你 {len(got_n[0])} 列，标准 {len(exp_n[0])} 列 {exp_cols}。"
    else:
        msg = "结果与标准答案不一致。对照时间窗、分母、是否含 0 用户。"
    return {"pass": False, "message": msg, "yours": yours_s, "expected": expected_s, "error": ""}


def preview_table(name, limit=12):
    con = new_db()
    cur = con.cursor()
    cols = [c[1] for c in cur.execute(f"PRAGMA table_info({name})").fetchall()]
    rows = cur.execute(f"SELECT * FROM {name} LIMIT {limit}").fetchall()
    con.close()
    return {"columns": cols, "rows": [list(r) for r in rows]}


def export_web(path="questions.json"):
    payload = {
        "tasks": [
            {
                "n": n,
                "name": t["name"],
                "desc": t["desc"].strip(),
                "tags": t.get("tags", []),
                "ref": t["ref"].strip(),
                "hints": HINTS[n],
            }
            for n, t in TASKS.items()
        ],
        "quiz": QUIZ,
    }
    with open(os.path.join(ROOT, path), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print("已写出", path)


def main():
    args = sys.argv[1:]
    if args and args[0] == "export":
        export_web(args[1] if len(args) > 1 else "questions.json")
        return
    if args and args[0] == "hint":
        n = int(args[1])
        print(f"第{n}题分层提示:\n")
        for h in HINTS[n]:
            print("  " + h)
        return
    if args and args[0] == "reset":
        reset()
        return
    if args and args[0] == "schema":
        print(schema_text())
        return

    # python check.py run 1 my.sql  或  python check.py 1 my.sql
    file_args = args
    if args and args[0] == "run":
        file_args = args[1:]
    if len(file_args) >= 2 and file_args[0].isdigit() and os.path.isfile(file_args[1]):
        n = int(file_args[0])
        sql = open(file_args[1], encoding="utf-8").read()
        r = judge(n, sql)
        print(("通过: " if r["pass"] else "未通过: ") + r["message"])
        print("\n--- 你的输出 ---\n" + r["yours"])
        if not r["pass"] and r["expected"]:
            print("\n--- 标准输出 ---\n" + r["expected"])
        return
    if args and args[0] == "run" and len(args) == 2:
        print("请指定题号: python check.py 1 my.sql")
        return

    targets = [int(args[0])] if args and args[0].isdigit() else sorted(TASKS)
    for n in targets:
        t = TASKS[n]
        print("=" * 66)
        print(f"题 {n}: {t['name']}")
        print(t["desc"])
        print("--- 参考答案输出 ---")
        print(fmt(run_sql(t["ref"])))
        print("卡住看提示:  python check.py hint", n)
        print()


if __name__ == "__main__":
    main()
