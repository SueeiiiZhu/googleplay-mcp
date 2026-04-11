# 暂时屏蔽的 MCP 工具接口

以下 7 个接口通过注释 `@mcp.tool()` 装饰器暂时屏蔽，函数代码保留完整。
恢复时搜索 `# TODO: 暂时屏蔽` 取消注释对应的 `@mcp.tool(...)` 行即可。

## 写入接口（防止误操作）

| 接口 | 文件 | 说明 |
|---|---|---|
| `googleplay_reviews_reply` | `tools/reviews.py` | 回复用户评论 |
| `googleplay_purchases_product_acknowledge` | `tools/purchases.py` | 确认应用内商品购买 |

## 需要真实购买数据的接口

| 接口 | 文件 | 说明 |
|---|---|---|
| `googleplay_subscriptions_get` | `tools/monetization.py` | 获取单个订阅配置详情 |
| `googleplay_orders_get` | `tools/orders.py` | 获取订单详情（费用/税金/退款） |
| `googleplay_purchases_product_get` | `tools/purchases.py` | 验证应用内商品购买状态 |
| `googleplay_purchases_subscription_get` | `tools/purchases.py` | 验证订阅购买状态 (v1 API) |
| `googleplay_purchases_subscription_v2_get` | `tools/purchases.py` | 验证订阅购买状态 (v2 API) |
