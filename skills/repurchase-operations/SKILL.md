---
name: repurchase-operations
description: Diagnose mature repurchase cohorts, build point-in-time customer segments, and propose budget-limited anonymous candidate and random holdout plans from positive retail orders. Use for repurchase operations questions; never infer actual marketing uplift from these simulated transactions.
---

# 复购运营

把业务问题落实为可回放的订单查询、分群或报告。当前数据是固定种子合成订单，无真实联系人、营销授权、触达记录或实际实验结果。

## 选择任务与工具

- `diagnose`：首次观察购买队列的次7日/次30日复购，支持地区与当前/对照日期窗口。
- `segment`：截至`end`的历史分群与预算内候选。`start`控制金额窗口；R、F使用截止日前的全部可见订单。默认召回候选是`cooling`和`dormant`。
- `report`：组合队列诊断、分群、留出计划。明确两者观察时间不同：队列结果统一观察至快照日；候选只能看截止日前历史。
- `experiment`：没有已执行随机触达数据时，说明无法估计增量，转为制定留出计划或请求实际实验结果。

应用通过受控分析工具调用`app.domains.repurchase.analyze`。优先将用户请求转换成明确的任务、窗口和筛选参数，不在语言模型中重算复购率或编造候选。在已有授权范围内生成计划；本工具不执行触达。

## 业务口径

1. 首次观察购买，是当前数据首次出现有效正向订单的日期，不代表真实首购或广告获客。选择队列时先在全量历史识别首次日期，再筛选窗口。
2. 次7日内复购观察D1—D7，次30日内复购观察D1—D30，均排除D0当日再购。分别仅将完整观察7/30日的客户纳入分母；成熟度由数据快照日判断，不能用系统今天补足。
3. 首购起30日人均正向交易额统计D0—D29，采用完整观察D30的队列。交易额未扣退款和成本，不能称净LTV、利润或ROI。
4. R为截止日距最后购买的自然日数；F为全部已观察历史的正向订单数，允许同日多单；M为`start`至`end`的正向金额。F不是购买天数，分群不等同于次7/30日复购事件。
5. 单订单客户按距首次购买是否超过30日分为`first`/`single`。多订单客户按R≤30、31—60、>60划分`active`/`cooling`/`dormant`。候选排序只能使用截止日前特征，不使用后续自然复购结果。
6. 分组前先按窗口金额、历史金额、最近购买和匿名ID确定候选；用固定seed的稳定哈希排序分配留出。处理组计划人数×每人成本不得超过预算。留出只是一份计划，需实际样本量设计和营销条件核验后才能使用。

## 参数与澄清

数据范围、默认窗口、表结构以`metadata()`或目录接口为准。传入ISO日期；对照须同时指定开始和结束。`diagnose`仅接受`region`；其余计划参数使用`segment`或`report`任务。

计划参数：`region`、`segment`、`budget`、`contact_cost`、`holdout_ratio`、`seed`、`limit`。金额以CNY元为单位，预算可为0，每人成本至少0.01元；留出比例0.1—0.5；人数上限1—200。未知筛选不能静默忽略。用户说“复购率”但未指定观察窗口时，澄清7日/30日，或明确并排输出两种口径。没有成熟分母时输出数据不足，不能写0%。

## 交付检查

引用工具返回的证据ID、SQL、参数和口径版本。事实、原因假设、行动建议分开：地区差异和历史变化只能描述，不能推出促销的因果效果。输出候选人数、处理/留出人数、计划成本、seed及观察边界。报告事实保留工具计算值，模型只组织解释。若用户要任意SQL或未经授权的联系信息，说明此工具的数据与能力范围。

数据生成、来源归属和可复现实例见[复购数据说明](../../docs/repurchase-data.md)。
