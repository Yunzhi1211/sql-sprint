-- 我的练习答案: DENSE_RANK Top3
SELECT product_name, sales_cnt, rnk
FROM (
    SELECT product_id, product_name, sales_cnt,
           DENSE_RANK() OVER (ORDER BY sales_cnt DESC) AS rnk
    FROM product_sales
) ranked
WHERE rnk <= 3
ORDER BY rnk, product_id;
