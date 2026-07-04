# GBT Pro · 部署面板规范（原子替换）

> 三件事串起来：环境一致、数据一致、预演与回滚。
> 一句话：所有代码进镜像多维度空间跑通，再在部署面板上切生产。

---

## 1. 环境一致（标准化 + 自动化 + 锁定）
| 项目 | 谁来负责 | 落在哪里 |
|---|---|---|
| Python 运行时 | 不可变镜像 `python:3.12.7-slim-bookworm` | `Dockerfile` 第 1 段 |
| 系统依赖 | `apt-get install` 限定包名 + 清缓存 | `Dockerfile` |
| 第三方库 | 严格 pin 在 `requirements.lock` | 镜像构建器一次性安装 |
| 配置模板 | `deploy/.env.example` | 派生 `.env.preview` / `.env.prod` |
| 密钥 | 由密钥库 → 注入 env_file，**不进 git** | `deploy/.env.prod` |
| 数据目录 | `GBT_DATA_DIR=/app/data` | 容器 volume |
| 日志目录 | `GBT_LOG_DIR=/app/logs` | 容器 volume |

> 校验：所有环境用同一 image tag；任何"看起来一样"差异都通过镜像 hash 强制被剔除。

---

## 2. 数据一致（迁移与回滚成对 + 幂等 + 备份）
- 字段变更只能通过 `deploy/migrate.py` 完成
- 每条迁移都同时实现 `forward` 与 `rollback`
- 所有 state 文件（`token_balance.json`、`auth_users.json`、`paper_account.json`、`autopilot.json`）都被路由到 `/app/data` 下的 snapshot，并带 `.bak` 备份
- 迁移前自动 `.bak`；幂等（重复执行不破坏数据）
- 关键校验通过 `state.json` 中的 `_migrate` 字段追踪

---

## 3. 预演 + 校验 + 自动回滚
1. `deploy/run_atomic.sh <tag>`：
   - 构建不可变镜像 → 启预发栈 → 跑迁移 → 探针验证
   - 灰度（先在 8766 起热备，原 8765 仍是上一个 tag） → 探针 → 切换
2. `deploy/healthcheck.py`：三层判断
   - L1 HTTP 探活 + dashboard 模板关键节点
   - L2 行数 / 校验和 / 关键业务指标对比（±2%）
   - L3 暴露 `POST /api/panel/rollback` 给面板
3. 不一致 → 自动调用 `rollback` 走 `atomic_switch.py` 回退到上一个 tag

---

## 4. 原子替换四原则（落地）
| 原则 | 怎么落地 |
|---|---|
| 接口契约稳定 | `/api/panel/status` 返回的 `version / data_dir / log_dir / release_tag` 与上一 tag 强一致；增减字段走迁移 |
| 数据层隔离 | 同一 image tag 不能跨 volume 共享数据；每次 promote 都用 prod volume |
| 灰度 + 快回滚 | `atomic_switch.py promote` 先热备在 8766，原 8765 仍服务；切不过立即撤回 |
| 真正原子 | image tag + 一次性 `docker compose up -d` + 同一网络端口切换，无"边跑边覆盖" |

---

## 5. 操作面板 SOP（开发者执行）
```bash
# 1) 准备
cp deploy/.env.example deploy/.env.preview
cp deploy/.env.example deploy/.env.prod
# 编辑 deploy/.env.prod 注入 DEEPSEEK_API_KEY 等
export GBT_PREV_TAG="v1.0.6"

# 2) 演练（不动生产）
deploy/run_atomic.sh v1.0.7 --drill

# 3) 真正发布
deploy/run_atomic.sh v1.0.7

# 4) 一键回滚
GBT_PREV_TAG=v1.0.6 python deploy/atomic_switch.py --new-tag v1.0.7 --rollback

# 5) 周期性探针
python deploy/healthcheck.py --url http://127.0.0.1:8765 --baseline data/baseline.json
```

---

## 6. 失败时的"安全网"
- 探针 L2 失败：自动触发 `/api/panel/rollback`
- 镜像构建失败：脚本不会切生产
- 数据迁移失败：launcher 拒绝启动（exit 3）
- 任意阶段超时（>60s）：默认回滚

---

## 7. 这次会话产出的文件清单
- `Dockerfile` — 不可变镜像
- `requirements.lock` — 锁版本
- `deploy/.env.example` — 配置模板
- `deploy/docker-compose.preview.yml` — 预发栈
- `deploy/docker-compose.prod.yml` — 生产栈
- `deploy/launch.py` — 不可变启动入口
- `deploy/migrate.py` — 成对迁移引擎
- `deploy/healthcheck.py` — L1/L2/L3 一致性探针
- `deploy/atomic_switch.py` — 灰度 + 原子切换 + 回滚
- `deploy/run_atomic.sh` — 部署面板入口
- `desktop_app.py` 新增 `/api/panel/status`、`/api/panel/rollback`
