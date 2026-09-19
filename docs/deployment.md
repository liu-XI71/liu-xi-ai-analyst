# 部署与复现

## 静态作品集

`web/` 是独立可发布目录，包含入口、样式、脚本、13个实际计算场景、26份HTML/Markdown报告、监控回放和评测记录。上传目录全部内容至静态托管即可。资源使用相对路径，支持 GitHub Pages 项目子目录。

本仓库 Pages 工作流在测试与回归通过后重新导出数据，再发布 `web/`。静态网站支持场景切换、证据展开、结果筛选、案例阅读和报告下载；自由输入需要连接 Python API。请通过本地 HTTP 服务或静态托管访问；浏览器模块与 fetch 不支持直接双击文件的运行方式。

## Python 服务

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -c constraints-tested.txt
sh scripts/start.sh
```

默认端口8765，可用 `PORT` 修改。`ANALYST_DATA_DIR` 指定运行库与匿名样本存储目录。首次启动按版本生成合成数据，之后幂等复用；修改生成器版本时重新生成业务数据，不覆盖运行与监控库。

Docker 镜像使用非 root 用户，提供健康检查。Compose 配置用于本机复现，Render Blueprint 用于在已连接的账户中创建服务。部署配置文件的存在不表示已有远端实例。

## 环境配置

`constraints-tested.txt` 保存本版实际通过测试的Python依赖版本。安装命令、CI与镜像构建使用这些约束；升级依赖时应重新运行对应测试与公开回归。

| 名称 | 说明 |
|---|---|
| OPENAI_API_KEY | 通过安全配置流程写入本地忽略文件或受信服务端机密设置 |
| OPENAI_MODEL | 默认保留 gpt-5-mini，可按账户可用模型配置 |
| LIVE_ACCESS_TOKEN | 远端模型入口的独立访问令牌，不放入静态资源 |
| ANALYST_ADMIN_TOKEN | 监控批次管理令牌；未单设时可使用 LIVE_ACCESS_TOKEN |
| LIVE_DAILY_LIMIT | 持久化UTC日请求上限，默认40；不是美元账单上限 |
| ALLOW_LIVE_PUBLIC | 默认false；公开入口仍受调用次数和并发限制 |
| CORS_ORIGINS | 允许的作品集来源，逗号分隔；包含协议和域名 |
| ANALYST_DATA_DIR | 数据和运行记录的持久目录 |
| PORT | HTTP监听端口 |

本地环境文件被 Git 排除。前端只接受 API 地址和运行访问令牌；访问令牌仅保存在当前页面内存，不写入localStorage。OpenAI Key始终在服务端。

## 持久化与日级调度

云端需为 `ANALYST_DATA_DIR` 配置持久存储；临时文件系统重启会失去运行、告警、反馈及日请求计数，不适合持续记录。单进程演示的短时限流位于内存，日模型请求计数位于SQLite；多实例部署需统一配额与状态存储。

日级任务调用：

```bash
python scripts/run_monitor.py --scenario business_drop
```

演示回填调用 `late_data` 后再调用 `recovered`。生产接入应让调度器使用获准的数据批次与业务合同，不把固定合成快照误作持续更新数据。

## 发布验收

1. 健康接口返回当前版本，静态首页与所有本地资源可读取。
2. 使用新的日期或切片提交动态请求，取得新运行编号与可复查SQL。
3. 下载HTML/Markdown报告，核对图表、结果行、决策与来源。
4. 检查不成熟、数据缺口、无效参数和无凭据模型请求的错误响应。
5. 真实模型调用需独立记录模型、工具、token、延迟、结果与失败；测试替身不计入。
6. 确认持久化、允许来源、模型与管理员访问边界。

本版本静态包提供完整案例，发布到 Pages 后即可公开浏览。模型凭据和云账户完成配置后才能验收远端模型调用；页面与文档按实际模式显示。
