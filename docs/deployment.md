# 独立作品集与Python服务部署

这个仓库对应新的项目，部署目标不覆盖`https://liu-xi71.github.io/`的旧作品集。静态页面计划位于新的项目子路径；实时服务使用独立Python进程。

本文件交付的是可执行部署配置。是否已经发布、真实域名与模型验证状态，以最终交付记录和实际服务健康检查为准。仅存在`render.yaml`不代表云服务已经创建。

## 三种运行方式

| 方式 | 可做什么 | 数据与模型 |
|---|---|---|
| GitHub Pages | 首页、业务案例、预计算运行回放、离线评测展示 | 静态JSON，无Python进程，不调用模型 |
| 本地Python或Docker | 新问题的确定性取数、筛选、SQL核验、图表、运行记录和报告 | SQLite动态计算；配置Key后可请求真实模型 |
| Render Docker服务 | 托管相同FastAPI应用，可供已授权访客调用 | 需账户实际创建服务并配置Key和访问令牌；免费实例会休眠 |

OpenAI API Key只能放在后端环境变量或本机`.env.local`。静态页面、GitHub Pages产物、浏览器前端、工作流日志与公开报告中均不应包含该Key。页面若需要访问令牌，填的是单独的`LIVE_ACCESS_TOKEN`，不是OpenAI Key。

## 本地复现

要求Python 3.11及以上，推荐3.12。

```bash
git clone https://github.com/liu-XI71/liu-xi-ai-analyst.git
cd liu-xi-ai-analyst
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
python scripts/export_demo.py
sh scripts/start.sh
```

访问`http://127.0.0.1:8765`与`http://127.0.0.1:8765/docs`。启动脚本读取`PORT`，默认8765；`HOST`默认`0.0.0.0`。只希望本机访问时运行`HOST=127.0.0.1 sh scripts/start.sh`。单worker与当前内存限流机制相匹配。

Windows PowerShell激活命令为`.venv\Scripts\Activate.ps1`，随后可直接运行：

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --workers 1
```

首次启动生成固定种子数据库。默认写入`var/`，可以通过`ANALYST_DATA_DIR`修改。运行记录与SQL证据存于该目录；真实模型未配置时live返回明确失败，不会用demo伪装成功。

## 真实模型配置

从`.env.example`复制出`.env.local`，在本机编辑器内填写已获授权的Key，不要粘贴到聊天、终端命令历史或仓库。应用会读取该文件；已经存在的环境变量优先。

| 变量 | 用途与默认 |
|---|---|
| `OPENAI_API_KEY` | 后端OpenAI API Key；无值时只能确定性演示 |
| `OPENAI_MODEL` | 默认`gpt-5-mini`；选择当前账户有权限且支持所用工具接口的模型 |
| `LIVE_ACCESS_TOKEN` | 自己生成的独立访问令牌；配置后所有live请求须带`Authorization: Bearer ...` |
| `ALLOW_LIVE_PUBLIC` | 默认false；未设访问令牌时，远程live请求拒绝 |
| `LIVE_DAILY_LIMIT` | 默认40；单进程过去24小时的live请求次数上限 |
| `CORS_ORIGINS` | 逗号分隔的允许前端来源；GitHub项目页的origin仍是`https://liu-xi71.github.io` |
| `PORT` | 启动端口；本地默认8765，Render配置10000 |
| `ANALYST_DATA_DIR` | 合成SQLite与运行记录目录 |

次数限制存于进程内存，重启会重置，并发多实例也不会共享。因此它不是账单硬上限。当前发布配置使用单进程、访问令牌与有限工具轮次；本项目不承诺固定推理费用。真实模型验证应记录run_id、模型、调用次数、token、SQL证据和结果正确性，不能以mock测试代替成功请求。

## Docker与Compose

镜像从Python 3.12 slim构建，以非root用户运行。Dockerfile显式复制应用、前端、Skill和评测目录；`.dockerignore`排除Key文件、虚拟环境和本地数据库。

```bash
docker build -t liu-xi-ai-analyst .
docker run --rm -p 127.0.0.1:8765:8765 liu-xi-ai-analyst
```

上述无Key方式即可验证完整的确定性后端。Compose使用本机`.env.local`和命名卷保留SQLite；运行前先创建该文件：

```bash
cp .env.example .env.local
docker compose up --build -d
docker compose logs --tail=80 analyst
```

修改`.env.local`后用`docker compose up -d --force-recreate`重建容器环境。Compose默认只绑定本机接口。Docker网络连接的客户端不一定被识别为本机，因此使用live时应在`.env.local`设置独立访问令牌。常规`docker compose down`保留命名卷；加`--volumes`会删除本地运行历史，重启后只能重建合成业务数据。

当前开发环境未提供Docker命令；容器配置可读取并验证，但本地无法声称镜像已构建成功。使用Docker的环境应完成构建、健康检查和一次demo分析后再发布。

## GitHub Pages

新仓库预期名为`liu-XI71/liu-xi-ai-analyst`，独立Pages地址预期为`https://liu-xi71.github.io/liu-xi-ai-analyst/`。实际发布前这些属于目标地址，不是在线承诺。

在**新仓库**Settings → Pages选择GitHub Actions作为Source。`.github/workflows/pages.yml`在main推送时安装依赖、运行无Key测试、执行`python scripts/export_demo.py`并发布`web/`。部署作业仅使用`pages:write`与`id-token:write`；旧首页仓库不在工作流操作范围。[GitHub官方Pages工作流说明](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)

一般CI位于`.github/workflows/ci.yml`，在推送或PR时运行测试与离线导出，将`web/`作为可下载构件保留7日。两个工作流都把`OPENAI_API_KEY`设为空，不需要账户Key。

离线演示只能回放导出时已经计算好的结果。不能把离线卡片标为当前自由输入问题的动态SQL执行，更不能标为真实模型运行。

## Render实时Python服务

`render.yaml`使用`runtime: docker`、`plan: free`、新加坡区域和新仓库main分支，设置`healthCheckPath: /api/health`。后续自动部署等待CI通过。Blueprint首次导入时要求输入`OPENAI_API_KEY`（`sync: false`），同时自动生成独立`LIVE_ACCESS_TOKEN`；`ALLOW_LIVE_PUBLIC`保持false。[Render Blueprint官方字段说明](https://render.com/docs/blueprint-spec)

实际部署步骤：

1. 在有权使用的Render账户中新建Blueprint，选择新仓库及`render.yaml`。
2. 将Key填入Render的秘密环境变量界面；不要提交到仓库。
3. 等待镜像构建完成，确认新服务的`/api/health`返回200。
4. 从服务环境设置取得独立访问令牌，仅提供给已授权的演示使用者。
5. 先运行demo，再发起一个live问题，核对`model_run`、工具轨迹、SQL与报告；成功后记录真实服务URL。

Render要求服务绑定`0.0.0.0`并推荐读取`PORT`。启动脚本满足这一要求；Blueprint设置10000，容器本地默认仍为8765。[Render端口说明](https://render.com/docs/web-services#port-binding)

免费服务空闲15分钟后休眠，恢复可能约一分钟；重启、休眠和重新部署都会丢失临时文件，且免费实例不能挂持久盘。因此合成明细可确定性重建，已保存的运行历史会丢失，报告应及时下载。免费服务有账户配额，适合作品演示；这份配置不承诺持续在线或零费用。[Render免费实例限制](https://render.com/docs/free)

## 发布验收

- 新站地址可打开，旧首页内容仍保持原状。
- `/api/health`为200，数据来源显式标注synthetic。
- 两个场景均能动态筛选、输出SQL与可下载报告。
- 无Key请求live明确失败；访问令牌错误不能调用真实模型。
- Key配置后实际执行的live问题保留可核验运行记录。
- 静态演示、后端demo、真实模型调用在界面和报告中区别清楚。

Render/GitHub官方文档核查日期：2026-09-19。最终发布状态需另行以实际部署结果为准。
