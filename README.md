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

复制 `.env.example` 为 `.env`，填写 PostgreSQL、DolphinDB、DolphinScheduler 凭据、`JUPYTER_TOKEN` 和 `JUPYTER_KEYRING_PASSWORD`。DolphinScheduler 登录密码使用 16 位随机字符，Gateway token 和首次创建凭据库的解锁密码使用独立长随机值。已有加密凭据库必须沿用原解锁密码，不能重新生成。所有本地凭据统一放在 `.env`，不需要额外的密码目录或文件。Compose 在同一个 D-Bus 会话中解锁凭据库，然后直接启动镜像原生的 `start-notebook.py`。

迁移已有解锁密码时必须保留原值的全部字节，包括原本参与解锁的换行；可在 `.env` 的双引号值中用 `\r`、`\n` 转义表示，不要去除它们。

如构建需要代理，在 `.env` 中设置 `BUILD_HTTP_PROXY`、`BUILD_HTTPS_PROXY`，例如 `http://host.docker.internal:7897`。Jupyter 运行代理使用独立的 `JUPYTER_HTTP_PROXY`、`JUPYTER_HTTPS_PROXY`，默认留空。然后在根目录执行：

```bash
docker compose up -d --build --wait
```

- 前端：<http://127.0.0.1:5174>
- 后端文档：<http://127.0.0.1:8010/docs>
- 健康检查：<http://127.0.0.1:8010/health>
- Jupyter：<http://127.0.0.1:8888/lab>，使用根目录 `.env` 中的 `JUPYTER_TOKEN` 登录。
- DolphinScheduler：<http://127.0.0.1:12346/dolphinscheduler/ui>，使用 `.env` 中的 `DOLPHINSCHEDULER_USERNAME/PASSWORD` 登录。

根目录 Compose 启动 Backend、Frontend、Jupyter 和 DolphinScheduler 3.2.2 单机服务，使用 Solo 自己的 Docker 网络。项目管理、Jupyter 研究提交、策略组装与任务记录已连接 Backend；报告读取真实运行清单及其声明的 Parquet，不用示例数据替代研究结果。

`runtime/src/solo_runtime/apps` 提供五类项目及策略组装的六个任务入口；各入口准备任务环境、启动对应 Scheme 计算并核验完成清单。
Jupyter 通过 `scheme.execute` 调用研究 SDK；Worker 使用 `solo-manage apps <应用名> --input-file ...` 启动对应任务，
报告写入共享目录。任务环境、包版本和 wheel 校验规则见 [Runtime README](runtime/README.md)，
输入示例见 [factor.json](runtime/examples/factor.json)、[strategy.json](runtime/examples/strategy.json)。

## 创建研究项目

前端选择项目类型、填写名称并选择 `solo-algos` 仓库的 Git Tag。后端按 Tag 对应的 commit 下载模板，生成独立包名和模块名，执行 `uv sync` 安装项目依赖，注册独立 Kernel 后保存项目记录。创建成功后点击“打开 Jupyter”，直接进入项目的 `research.ipynb`。

项目目录为 `/shared/projects/<项目类型>/<项目名>/`，例如 `/shared/projects/model/动量策略/`。同类项目名称不能重复；名称修改会同步移动目录并重建环境，删除项目只隐藏记录，目录保留。

创建项目时先选择 Scheme 版本，再选择主版本、次版本均一致的 Algo 模板，补丁版本不必相同。项目间安装和策略组装也遵循同一规则，例如 1.2.0 与 1.2.7 可互调，不能混用 1.1.x 或 1.3.x。后端记录双方 Tag/commit；发布依赖覆盖整个补丁系列，如 `scheme>=1.2.0,<1.3.0`，不限定更高的补丁下界。项目 uv source 与锁文件仍精确固定实际使用的 commit，不自动升级已有环境。前端报告继续按运行清单中的 Scheme **主版本**选择适配器，未知主版本不回退解释。

项目根目录 `.solo` 是供插件读取的 JSON 文件，字段为 `project_id`、`name`、`kind`、`scheme_version`、`scheme_commit`、`algo_version`、`algo_commit`；项目 ID 在改名后保持不变。每个项目保存独立 `.venv`、`uv.lock`。Python 解释器保存在 `/home/jovyan/.python`，Kernel 注册信息保存在 `/home/jovyan/.jupyter/kernels`，代码补全临时文件保存在 `/home/jovyan/.virtual_documents`；通过卷挂载在容器重建后保留，不占用 `projects` 目录。

`GITEE_TOKEN` 可选；`JUPYTER_URL` 是浏览器访问 Jupyter 的地址，修改端口时需同步调整。首次创建需要下载 Python 与依赖，安装失败时页面显示错误并清理未完成的项目目录。

## 版本退役

退役政策唯一来源为 [backend/version-policy.json](backend/version-policy.json)，通过 `GET /api/v1/version-policy` 查询。Scheme 0.1.0、1.0.0、1.0.1、1.1.0 与 Algo 模板 0.1.0、1.0.0、1.0.1 已退役；新项目使用 Scheme / Algo 1.2.0 及满足契约的后续版本。退役与主次版本兼容是两个独立条件：同系列也不能新增使用已退役来源。

退役版本不出现在新建、上游安装或策略组装候选中。Backend 在新建、保存、提交与组装入口校验政策，Jupyter 在执行项目表单和安装前调用中央准入接口，Runtime 在安装任务环境前核验 Backend 管理的 Run UUID、输入和锁文件 SHA256，并与提交前保存的数据库哈希匹配；服务不可用或版本来源不明时拒绝执行。旧任务不能用原输入另行重放来绕过退役。

历史项目、Notebook、源码、锁文件、wheel 和报告原样保留，不改为归档，不移动或删除 Git Tag，不自动迁移依赖。历史报告继续按 Scheme 主版本渲染。发布切换时没有未完成任务，政策不启用基于创建时间或 `queued` 状态的例外放行。更新 Jupyter 插件和 Worker 需要构建相应镜像；有正在使用的 Kernel 时不要为了更新直接重启 Jupyter。

上游安装先把已保存源码及所需本地运行时依赖构建为 wheel，保留原始 `Requires-Dist`，不继承上游 `tool.uv.sources.scheme`，不使用 Scheme override 覆盖依赖要求。完整安装在隔离环境解析与验证后才提交；当前 Scheme source 和实际补丁版本保持不变，提交失败恢复配置、锁文件及原 `.venv`。

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

`docker compose down` 保留数据，`docker compose down -v` 会删除上述命名卷。备份加密凭据库时同时保存 `.env` 中的 `JUPYTER_KEYRING_PASSWORD`，已有解锁密码不要重新生成。`.env` 不提交到 Git，并应限制宿主机读取权限；通过环境变量传入的凭据可被有 Docker 管理权限的人查看。

## DolphinScheduler 工作流

部署方式与 Arena 一致：3.2.2 standalone + PostgreSQL。Solo 使用 `solo_ds`，宿主机 API 端口 `12346`、Python Gateway 端口 `25334`，容器内端口仍为 `12345 / 25333`。`dolphinscheduler-schema-initializer` 仅初始化/升级 DS 数据库表，完成后退出；共享目录仍由 Jupyter 设置权限，没有共享目录 init 服务。

Backend 启动时通过 Python Gateway 同步 `solo-runtime` 项目下的 `factor`、`model`、`optimize`、`control`、`execution`、`strategy` 六个工作流，与 Runtime apps 一一对应。它们均为手动触发的单 Shell 任务，不设置定时计划，不自动重试。Worker 内置 `solo-runtime==1.1.0`，任务以 `root` 租户运行，并通过 `SOLO_BACKEND_URL=http://backend:8000` 查询执行准入。

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

调度日志只通过 DS API 获取，Backend 不挂载或直接读取调度器日志卷，也不另存业务日志表。Worker 用 Compose 服务名 `dolphinscheduler-standalone:1234` 注册地址，新任务不再记录会随容器重建变化的 IP。已有任务记录中的旧 IP 不会被该配置改写；如果旧地址失效，应通过调度器运维恢复原日志服务，而不是由 Backend 绕过接口读文件或静默改写调度数据库。

策略组装固定选中的 Algo 版本和 Model 成果中的 Scheme 来源，按包的依赖声明解析公共依赖并生成独立锁文件。新模板使用 Scheme 1.2.0 参数与版本契约；已有成果保留冻结的 Scheme 和报告，退役来源不能用于新策略，不提供自动源码迁移、Scheme 替换或任务类型转换。报告必须明确提供 `report_kind`，`input.kind` 必须与实际项目类型一致。

## 更新组件

在子仓库中提交并推送改动后，再在本仓库提交对应 submodule 的版本指针。嵌套的 `scheme` 改动需依次推送 `scheme`、`algos` 和本仓库。
