-- ============================================================
-- PDD Temu 用户增长岗 - SQL 突击训练 数据环境
-- 数据结构完全对标面试/笔试题：
--   1) usr 用户表 + ordr 订单表 (激活7日、来源均值、窗口函数avg over partition)
--   2) orders 表 (Cohort 留存分析)
--   3) product_sales 表 (DENSE_RANK TopN)
-- ============================================================

DROP TABLE IF EXISTS usr;
DROP TABLE IF EXISTS ordr;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS product_sales;

-- ---------- 1. 用户表 ----------
CREATE TABLE usr (
    user_id     INTEGER PRIMARY KEY,
    source      VARCHAR(20),   -- 渠道来源: ad / organic / referral / koc
    reg_date    DATE,          -- 注册(激活)日期
    country     VARCHAR(10)
);

-- ---------- 2. 订单表 ----------
CREATE TABLE ordr (
    order_id    INTEGER PRIMARY KEY,
    user_id     INTEGER,
    order_date  DATE,
    ordr_amt    DECIMAL(10,2),
    status      VARCHAR(10)   -- paid / cancel
);

-- ---------- 3. 通用订单表(留存分析用) ----------
CREATE TABLE orders (
    order_id    INTEGER PRIMARY KEY,
    user_id     INTEGER,
    order_date  DATE,
    amount      DECIMAL(10,2)
);

-- ---------- 4. 商品销量表(TopN) ----------
CREATE TABLE product_sales (
    product_id   INTEGER PRIMARY KEY,
    product_name VARCHAR(30),
    sales_cnt    INTEGER
);

-- ================= 用户数据 =================
INSERT INTO usr VALUES
 (1,'ad',      '2026-01-01','US'),
 (2,'organic', '2026-01-01','US'),
 (3,'referral','2026-01-02','GB'),
 (4,'ad',      '2026-01-05','US'),
 (5,'koc',     '2026-01-05','DE'),
 (6,'organic', '2026-01-08','US'),
 (7,'ad',      '2026-01-10','US'),
 (8,'referral','2026-01-15','GB'),
 (9,'ad',      '2026-02-01','US'),
 (10,'organic','2026-02-03','US');

-- ================= 订单数据 (usr/ordr 激活7日题) =================
-- user1 激活01-01, 7日内(01-01~01-07)有订单
INSERT INTO ordr VALUES
 (101,1,'2026-01-02', 120.00,'paid'),
 (102,1,'2026-01-03',  80.00,'paid'),
 (103,1,'2026-01-06',  50.00,'paid'),   -- 7日内共3单 250
 (104,1,'2026-01-20', 200.00,'paid'),   -- 超出7日,不算
 (105,2,'2026-01-01', 300.00,'paid'),   -- organic 7日内
 (106,2,'2026-01-04', 100.00,'paid'),
 (107,3,'2026-01-02',  60.00,'paid'),   -- referral 7日内
 (108,4,'2026-01-06', 400.00,'paid'),   -- ad
 (109,4,'2026-01-09', 100.00,'paid'),   -- ad 激活01-05，窗到01-11，此单算
 (110,4,'2026-01-12', 250.00,'paid'),   -- 超出7日,不算
 (111,5,'2026-01-05', 500.00,'paid'),   -- koc 7日内(激活=01-05)
 (112,5,'2026-01-06',  50.00,'cancel'), -- 取消单：支付总额不计
 (113,6,'2026-01-09', 150.00,'paid'),   -- organic 7日内
 (114,7,'2026-01-11',  90.00,'paid'),   -- ad 激活01-10, 7日到01-16
 (115,9,'2026-02-01', 1000.00,'paid');  -- ad 激活02-01

-- ================= orders 表(留存分析用, 与上面是不同数据集) =================
INSERT INTO orders VALUES
 (201,1,'2026-01-05',99),
 (202,1,'2026-01-20',99),   -- M0=Jan
 (203,1,'2026-02-10',99),   -- M1
 (204,1,'2026-03-15',99),   -- M2
 (205,2,'2026-01-08',88),
 (206,2,'2026-02-01',88),   -- M0=Jan
 (207,3,'2026-01-10',77),
 (208,3,'2026-01-25',77),
 (209,3,'2026-03-01',77),   -- M0=Jan
 (210,4,'2026-02-02',66),
 (211,4,'2026-02-20',66),   -- M0=Feb
 (212,5,'2026-02-05',55),
 (213,5,'2026-04-01',55),   -- M0=Feb
 (214,6,'2026-03-01',44),  -- M0=Mar
 -- 连续下单测试数据 (user7 在2026-01-10/11/12 连续3天, user8 在01-20/21 连续2天)
 (215,7,'2026-01-10',10),
 (216,7,'2026-01-11',10),
 (217,7,'2026-01-12',10),
 (218,8,'2026-01-20',20),
 (219,8,'2026-01-21',20);

-- ================= 商品销量(TopN DENSE_RANK) =================
INSERT INTO product_sales VALUES
 (1,'iPhone',100),
 (2,'iPad',100),
 (3,'MacBook',80),
 (4,'AirPods',80),
 (5,'AppleWatch',80),
 (6,'HomePod',50),
 (7,'iMac',50),
 (8,'MagicMouse',30);
