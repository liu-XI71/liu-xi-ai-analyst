# 来源与第三方说明

本项目新增代码以仓库MIT许可证提供。运行依赖保留各自许可证；仓库没有重新声明这些依赖的所有权。

## 业务方法归属

- 刘希既有[增长分析与实验作品](https://github.com/liu-XI71/liu-xi-growth-analytics-portfolio)：增长业务问题、指标口径和证据组织方式的来源。
- 刘希既有[复购运营作品](https://github.com/liu-XI71/liu-xi-evidence-analytics)：次7/30日成熟队列、正向交易额与历史时点分群口径的来源。本项目重新实现SQL与合成数据生成，没有复制UCI交易数据。
- 刘希既有[CSV分析工作台](https://github.com/liu-XI71/liu-xi-csv-analyst)：作为已有业务工具单独链接；新项目没有将旧链接或内容替换为AI版本。

合成增长和复购数据不属于任何企业真实经营数据。合成实验差异、预算计划和自然复购不能归为个人历史业绩或营销增量。

## 软件依赖

依赖名称和版本范围见`requirements.txt`、`requirements-dev.txt`。各组件的作者与许可分别见官方仓库：

- [FastAPI](https://github.com/fastapi/fastapi)
- [Uvicorn](https://github.com/encode/uvicorn)
- [HTTPX](https://github.com/encode/httpx)
- [OpenAI Python SDK](https://github.com/openai/openai-python)
- [python-dotenv](https://github.com/theskumar/python-dotenv)
- [SQLGlot](https://github.com/tobymao/sqlglot)
- [pytest](https://github.com/pytest-dev/pytest)
- [Python](https://www.python.org/psf/license/)及标准库SQLite接口

GitHub Actions使用GitHub官方的checkout、setup-python、upload-artifact、configure-pages、upload-pages-artifact和deploy-pages组件。部署配置参考[GitHub Pages官方工作流文档](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)与[Render官方Blueprint文档](https://render.com/docs/blueprint-spec)。

## Skill与模型说明

`skills/`为本项目的业务规则文件，由应用实际读取到模型上下文；不是从某个第三方Skill仓库整包复制。之前调研过的Anthropic、K-Dense、WrenAI、DB-GPT等资源属于设计参考，不表示本仓库安装、依赖或集成了这些项目。

真实模型调用使用OpenAI Responses API，其服务条款、可用性和费用独立于本仓库MIT许可证。确定性演示无需模型密钥；发布的静态回放不运行真实模型。
