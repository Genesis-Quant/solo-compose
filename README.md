# Solo Compose

Solo 个人量化研究工作台的部署仓库，通过 Git submodule 固定各组件版本。

| 目录 | 仓库 |
| --- | --- |
| `backend` | [solo-backend](https://gitee.com/genesis-quant/solo-backend) |
| `frontend` | [solo-frontend](https://gitee.com/genesis-quant/solo-frontend) |
| `jupyter` | [solo-jupyter](https://gitee.com/genesis-quant/solo-jupyter) |
| `runtime` | [solo-runtime](https://gitee.com/genesis-quant/solo-runtime) |
| `backtest` | [backtest](https://gitee.com/genesis-quant/backtest) |
| `algos` | [solo-algos](https://gitee.com/genesis-quant/solo-algos) |
| `algos/scheme` | [solo-algo-scheme](https://gitee.com/genesis-quant/solo-algo-scheme)，由 `algos` 管理 |

## 获取代码

```bash
git clone --recurse-submodules https://gitee.com/genesis-quant/solo-compose.git
cd solo-compose
```

默认仓库位于 Gitee；GitHub 保留同步副本。本机各仓库的 `origin` 从 Gitee 拉取，
配置两个 push URL，普通 `git push` 会依次推送 Gitee 和 GitHub。
`gitee`、`github` 是分别操作单端的 remote。双端推送不是原子操作，失败时需检查两端结果后重试。
这些设置属于本机 Git 配置，新克隆的仓库需同样配置（子模块也需逐个配置）：

```bash
git remote add gitee https://gitee.com/genesis-quant/solo-compose.git
git remote add github https://github.com/Genesis-Quant/solo-compose.git
git remote set-url --add --push origin https://gitee.com/genesis-quant/solo-compose.git
git remote set-url --add --push origin https://github.com/Genesis-Quant/solo-compose.git
git config remote.pushDefault origin
git config push.followTags true
```

已有工作区更新到仓库固定的组件版本：

```bash
git pull --ff-only
git submodule update --init --recursive
```

## 本地运行

使用 Docker Desktop / WSL2。连接本机现有 PostgreSQL 容器，提前创建 `solo`、`solo_ds` 数据库并配置访问账号。

复制 `.env.example` 为 `.env`，填写 PostgreSQL、DolphinDB、DolphinScheduler 凭据和 `JUPYTER_TOKEN`。DolphinScheduler 登录密码使用 16 位随机字符，Gateway token 使用独立长随机值。首次启动还需生成 Jupyter 凭据库密钥（PowerShell）：

```powershell
New-Item -ItemType Directory -Force .secrets | Out-Null
if (-not (Test-Path .secrets/jupyter-keyring-password)) {
    $keyringPassword = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
    [IO.File]::WriteAllText((Join-Path $PWD '.secrets/jupyter-keyring-password'), $keyringPassword)
}
```

如构建需要代理，在 `.env` 中设置 `BUILD_HTTP_PROXY`、`BUILD_HTTPS_PROXY`，例如 `http://host.docker.internal:7897`。Jupyter 运行代理使用独立的 `JUPYTER_HTTP_PROXY`、`JUPYTER_HTTPS_PROXY`，默认留空。然后在根目录执行：

```bash
docker compose up -d --build --wait
```

- 前端：<http://127.0.0.1:5174>
- 后端文档：<http://127.0.0.1:8010/docs>
- 健康检查：<http://127.0.0.1:8010/health>
- Jupyter：<http://127.0.0.1:8888/lab>，使用根目录 `.env` 中的 `JUPYTER_TOKEN` 登录。
- DolphinScheduler：<http://127.0.0.1:12346/dolphinscheduler/ui>，使用 `.env` 中的 `DOLPHINSCHEDULER_USERNAME/PASSWORD` 登录。

根目录 Compose 启动 Backend、Frontend、Jupyter 和 DolphinScheduler 3.2.2 单机服务，使用 Solo 自己的 Docker 网络。项目管理已连接 PostgreSQL；报告组件保留固定示例。调度层已接入 Runtime，Jupyter 插件的研究提交界面尚未接入。

`runtime/src/solo_runtime/apps` 提供五类项目及策略组装的六个任务入口；各入口准备任务环境、启动对应 Scheme 计算并核验完成清单。
Jupyter 通过 `scheme.execute` 调用研究 SDK；Worker 使用 `solo-manage apps <应用名> --input-file ...` 启动对应任务，
报告写入共享目录。任务环境、包版本和 wheel 校验规则见 [Runtime README](runtime/README.md)，
输入示例见 [factor.json](runtime/examples/factor.json)、[strategy.json](runtime/examples/strategy.json)。

## 创建研究项目

前端选择项目类型、填写名称并选择 `solo-algos` 仓库的 Git Tag。后端按 Tag 对应的 commit 下载模板，生成独立包名和模块名，执行 `uv sync` 安装项目依赖，注册独立 Kernel 后保存项目记录。创建成功后点击“打开 Jupyter”，直接进入项目的 `research.ipynb`。

项目目录为 `/shared/projects/<项目类型>/<项目名>/`，例如 `/shared/projects/model/动量策略/`。同类项目名称不能重复；名称修改会同步移动目录并重建环境，删除项目只隐藏记录，目录保留。

创建项目时先选择 Scheme 版本，再选择同大版本的 Algo 模板版本。后端记录双方 Tag/commit；发布依赖声明整个 Scheme 大版本范围，项目 uv source 与锁文件固定实际使用的 commit。前端按运行清单中的实际 Scheme 大版本选择报告适配器，未知版本不回退解释。

项目根目录 `.solo` 是供插件读取的 JSON 文件，字段为 `project_id`、`name`、`kind`、`scheme_version`、`scheme_commit`、`algo_version`、`algo_commit`；项目 ID 在改名后保持不变。每个项目保存独立 `.venv`、`uv.lock`。Python 解释器保存在 `/home/jovyan/.python`，Kernel 注册信息保存在 `/home/jovyan/.jupyter/kernels`，代码补全临时文件保存在 `/home/jovyan/.virtual_documents`；通过卷挂载在容器重建后保留，不占用 `projects` 目录。

`GITEE_TOKEN` 可选；`JUPYTER_URL` 是浏览器访问 Jupyter 的地址，修改端口时需同步调整。首次创建需要下载 Python 与依赖，安装失败时页面显示错误并清理未完成的项目目录。

## 共享目录

| Docker 命名卷 | 容器路径 | 用途 | 挂载服务 |
| --- | --- | --- | --- |
| `solo_solo-projects` | `/shared/projects` | 研究项目源码、Notebook、项目 uv 环境 | Backend、Jupyter，均可读写 |
| `solo_solo-runs` | `/shared/runs` | 任务输入、wheel、uv.lock、隔离环境和报告 Parquet | Backend、Jupyter、DolphinScheduler Worker，均可读写 |
| `solo_jupyter-keyrings` | `/home/jovyan/.local/share/keyrings` | 加密凭据库 | Jupyter |
| `solo_codex-home` | `/home/jovyan/.codex` | Codex 配置和登录状态 | Jupyter |
| `solo_dolphinscheduler-resources` | `/tmp/dolphinscheduler` | 调度执行目录 | DolphinScheduler |
| `solo_dolphinscheduler-logs` | `/opt/dolphinscheduler/logs` | 服务与任务日志 | DolphinScheduler |

Backend 和 Jupyter 统一使用 `SOLO_SHARED_DIR=/shared`。Jupyter 文件浏览器根目录为 `/shared`，项目链接使用 `/lab/tree/projects/<项目类型>/<项目名>/research.ipynb`。Frontend 不直接挂载共享卷。Worker 只挂载 runs 卷，不访问项目源码卷。

Backend 和 Jupyter 均以 root 运行，无独立初始化服务。Jupyter 直接启动，不经过镜像切换到 jovyan 的入口脚本，HOME 仍为 `/home/jovyan`，沿用已有配置、凭据库和 Codex 登录状态。命名卷保存在 Docker Desktop 的 Linux 文件系统中，适合项目虚拟环境；不是 Windows 源码目录的映射。Jupyter 配置仍由 `jupyter/config` 持久化。

`docker compose down` 保留数据，`docker compose down -v` 会删除上述命名卷。备份加密凭据库时同时保存 `.secrets/jupyter-keyring-password`，已有密钥不要重新生成。`.env` 和 `.secrets` 均不提交到 Git。

## DolphinScheduler 工作流

部署方式与 Arena 一致：3.2.2 standalone + PostgreSQL。Solo 使用 `solo_ds`，宿主机 API 端口 `12346`、Python Gateway 端口 `25334`，容器内端口仍为 `12345 / 25333`。`dolphinscheduler-schema-initializer` 仅初始化/升级 DS 数据库表，完成后退出；共享目录仍由 Jupyter 设置权限，没有共享目录 init 服务。

Backend 启动时通过 Python Gateway 同步 `solo-runtime` 项目下的 `factor`、`model`、`optimize`、`control`、`execution`、`strategy` 六个工作流，与 Runtime apps 一一对应。它们均为手动触发的单 Shell 任务，不设置定时计划，不自动重试。Worker 内置 `solo-runtime==1.0.0`，任务以 `root` 租户运行。

工作流仅接收 `input_file`，例如 `/shared/runs/<run-id>/input.json`。输入包含全部运行参数、候选 wheel、锁文件和输出路径；不得含密钥。正式调用前准备该次任务的 `environment/pyproject.toml` 和 `environment/uv.lock`，不使用项目可变源码目录。Runtime 按锁文件安装独立依赖并启动任务环境中的 scheme；scheme 核对版本、wheel 哈希及接口，写出 Parquet 和 `run.json`，Runtime 核验完成清单和报告哈希。每次运行使用独立任务目录；已有成功报告的输出目录不会被覆盖。

```bash
# 同步工作流；同名定义保持原 code，更新定义版本
docker compose exec backend python -m core.scheduler sync

# 提交任务
docker compose exec backend python -m core.scheduler start factor --input-file /shared/runs/<run-id>/input.json
docker compose exec backend python -m core.scheduler start strategy --input-file /shared/runs/<run-id>/input.json

# 查询实例、任务和日志（ID 取自上一条查询）
docker compose exec backend python -m core.scheduler instances factor
docker compose exec backend python -m core.scheduler instance <instance-id>
docker compose exec backend python -m core.scheduler tasks <instance-id>
docker compose exec backend python -m core.scheduler log <task-id> --offset 0 --limit 1000

```

调度日志通过 DS API 获取，不另存业务日志表。

策略组装固定选中的 Algo 版本和 Model 成果中的 Scheme 来源，按包的依赖声明解析公共依赖并生成独立锁文件。当前使用 Scheme 1.0.0 接口，不提供历史接口适配、Scheme 替换或任务类型转换。报告必须明确提供 `report_kind`，`input.kind` 必须与实际项目类型一致。

## 更新组件

在子仓库中提交并推送改动后，再在本仓库提交对应 submodule 的版本指针。嵌套的 `scheme` 改动需依次推送 `scheme`、`algos` 和本仓库。
