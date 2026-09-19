# 分析服务合同 v2

本合同描述公开作品集的实际请求、结果及执行边界。所有业务演示数据均为固定种子合成数据；原有业务经历通过独立链接展示。

## 业务域与输入

`onboarding` 为新用户增长主域，`experiments` 为随机实验评审，`repurchase` 为电商复购，`growth` 保留早期次7日内回访案例。

领域模块提供 `metadata()`、`build_database(path)`、`analyze(request, db_path)`。业务数据库由各领域独立管理。事件和实验数据集之间没有同一干预的因果关联。

`POST /api/v1/analyze` 接受问题、业务域、任务、运行模式、日期和筛选；结构化日期和筛选为明确约束，模型不得静默覆盖。有效枚举和默认窗口由 `/api/v1/catalog` 返回。增长与复购使用各自比较合同，实验使用预注册窗口而不接受增长比较期。

- `mode=demo`：有限语义路由和真实 SQL/Python 计算。
- `mode=live`：服务端 OpenAI Responses 工具循环；无凭据时明确返回失败，不自动替换为演示。
- 静态页面：只读取保存的实际计算结果，标记 `static_snapshot=true`。

## 通用输出

| 字段 | 内容 |
|---|---|
| status / title / summary | 执行状态与摘要；技术完成不等于允许策略上线 |
| metric_contract | 指标定义、日期、人群、成熟与版本 |
| kpis | 指标ID、名称、值、单位、对比值和变化 |
| tables / charts | 完整结果与图表数据；缺失值保持null |
| findings | 事实、待验证解释与动作，关联证据ID |
| evidence | SQL、参数、结果行、数据源、指标版本 |
| trace | 实际工具动作、执行状态和耗时 |
| limitations / suggestions | 适用边界与后续动作 |
| provenance | 应用版本、合成数据标识与来源信息 |

运行接口增加 `run_id`、`created_at`、`duration_ms`、`request`。首次响应返回一次性取得的 `feedback_token`；服务器仅保存其哈希，运行回读与报告不返回该凭证。

新用户结果增加 `plan`、`data_quality`、`funnel`、`hypotheses` 和 `decision`。实验增加 `checks`、`experiment_contract`、`experiment_statistics` 与规范化决策。所有生成的经营数字由 SQL/Python 计算，模型只能选择已校验的报告事实。

## 状态与决策

- `needs_clarification`：指标、日期或参数冲突，需补齐条件。
- `insufficient_data`：无有效观察、超范围或样本证据不足；不补造0。
- `data_quality_blocked`：增长批次、到数或事件合同未通过，停止受影响业务判断。
- `invalid_data`：实验数据或配置无效，先修复实验。
- `waiting_for_maturity`：实验观察未成熟，保留等待状态。
- `completed`：请求的计算完成；实验是否具备灰度条件另由 `decision.code` 决定。

实验决策可能是修复数据、等待成熟、证据不足、停止或调整、提交人工灰度评审。接口不执行营销触达、生产策略下发或自动放量。

## 存储与访问

业务库只读查询使用允许表、AST校验、SQLite只读连接、授权回调、行数与执行时间限制。该边界不等价于企业租户隔离或行列权限。

运行、监控、反馈及每日模型请求配额分别持久化。模型令牌仅在后端；部署访问令牌只保存在当前页面内存。公开示例允许合成结果回读；企业数据接入前需另行实现身份、结果授权和保留策略。

页面处理加载、失败、澄清、参数变化后的旧结果、取消请求、键盘导航与窄屏。具体的已执行验证及未验证范围见 [验证记录](docs/ui-verification.md)。
