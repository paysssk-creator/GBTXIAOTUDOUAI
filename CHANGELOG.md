# CHANGELOG · GBT Pro

## SOP 版本
- **v1.0**：5 步流水线（需求卡 → 镜像预演 → 预发 → 灰度 → 归档）
- **v1.1**：6 步流水线 + 同构环境 + 演练套件 + 量化门槛 + 归档审批

## 历史归档索引

| 任务 | 标题 | 发布标签 | 归档 |
|------|------|----------|------|
| T-001 | 镜像空间插件灰度预演 | v1.1.1 | data/release/T-001.json |
| T-002 | desktop_app.py 重构为 13 Blueprint + 全员开发者署名 | v1.1.2 | data/release/T-002.json |
| T-003 | 测试覆盖度提升至 109 用例 + 量化发布红线 | v1.1.3 | data/release/T-003.json |
| T-004 | layout.html 1688 行拆分为 17 partial（字节级 roundtrip） | v1.1.4 | data/release/T-004.json |
| T-005 | _scripts.html 功能域解耦为 6 子模块 | v1.1.5 | data/release/T-005.json |
| T-006 | _script_init 兜底代码 514 行 → 8 行 | v1.1.6 | data/release/T-006.json |
| T-007-A | 镜像空间插件注册 | v1.1.6 | data/release/T-007-A.json |
| T-008 | 治未病 · 移除面板 4 处虚假数据（fake tokens + hardcoded 激活码） | v1.1.6 | data/release/T-008.json |
| T-009 | 治未病 · A 股行情 4 bug 全修复（URL 污染 + int 崩溃 + akshare 缺失 + Sina 字段错位） | v1.1.7 | data/release/T-009.json |
| T-010 | Futurapay 支付集成 · 密钥本地锁 · CNY 试用 · 全支付方式 | v1.1.8 | data/release/T-010.json |
| T-011 | 治未病 · 个股行情 502 透传 + fake 兜底 — 双源降级（东财→新浪/腾讯）+ 错误脱敏 + 禁用 mock | v1.1.9 | data/release/T-011.json |
| T-012 | 首席编程师视角 · 10 阶段全量审计 + 打包基建 + 一键安装（requirements.txt + Dockerfile + .dockerignore + desktop_app.spec + build_exe.py + install.bat + decision_log.py） | v1.1.10 | data/release/T-012.json |
| T-013 | 排查密钥泄露路径 · 修 4 处脱敏漏点（build_exe.py / CHANGELOG.md / Dockerfile / desktop_app.py） · 五层防线激活验证 | v1.1.11 | data/release/T-013.json |
| T-014 | 深度排查 8 维度（B1 源码 / B2 编译 / B3 前端 / B4 数据 / B5 API / B6 镜像空间 / B7 shell / B8 缓存）· 5 处归档脱敏 · 30 API 响应零泄露 | v1.1.12 | data/release/T-014.json |

## [T-010] · 2026-06-30 · Futurapay 支付集成 · 密钥本地锁 · CNY 试用 · 全支付方式

> 任务编号：T-010 · SOP **v1.1** · 状态：**RELEASED-USER-CONFIRMED** · `release_tag = v1.1.8-futurapay-integration`
> 开发者：**自由的风** · 归档：[data/release/T-010.json](file:///c:/Users/ADMIN/Desktop/自主操盘/GBTXIAOTUDOUAI/data/release/T-010.json)

### 用户原始指令（5 轮强化）

| # | 指令 | 落地 |
|---|------|------|
| 主 | `https://futurapay.com/ 把收费的用这个集成进去替换原有的站点 ID 131052833` | site_id=131052833 + apiKey【脱敏·首 4 位】 写入 .env |
| 1 | "打包的时候千万不能把密钥打包进去" | 5 层防线 + 运行时 _lock_keys() + SHA256 hash 校验 |
| 2 | "集成的时候记得把所有的支付方式全部都集成进去别遗漏了，还有收款连接自动生成以及教用户这么付款" | 官方 Widget iframe 自动覆盖未来新增渠道；后端一键加密链接；前端 6 步教学 |
| 3 | "给他部署一个指纹环境，有些地区使用不了，部署好指纹环境自动调节" | pay_widget_probe.py 三层降级（L1 requests → L2 curl_cffi chrome124 → L3 playwright） |
| 4 | "必须把集成支付密钥保护在我本地，只能我的账户才能收款不接受修改" | 模块导入即锁 + 失配 raise + 审计 → 运行期修改 .env 拒绝生效 |
| 5 | "看看这个支付方式里面有没有支持收人民币的看清楚" | 查官方文档：仅 USD/EUR，CNY 不在支持列表 |
| 6 | "他这个项目不是以条纹来做的嘛？你直接开通人民币收款看看行不行？" | CNY 收进接口 EXPERIMENTAL_CURRENCIES，widget 实测决定 |

### 4 个核心模块

| 文件 | 行数 | 用途 |
|------|------|------|
| [gbt/pay_futurapay.py](file:///c:/Users/ADMIN/Desktop/自主操盘/GBTXIAOTUDOUAI/gbt/pay_futurapay.py) | 311 | AES-256-CBC 加密 + 链接生成 + HMAC + 速率锚定 |
| [gbt/payment_lock.py](file:///c:/Users/ADMIN/Desktop/自主操盘/GBTXIAOTUDOUAI/gbt/payment_lock.py) | 90 | 启动 baseline SHA256 + 失配审计 |
| [gbt/pay_widget_probe.py](file:///c:/Users/ADMIN/Desktop/自主操盘/GBTXIAOTUDOUAI/gbt/pay_widget_probe.py) | 152 | 三层降级探测 |
| [gbt/api/payment.py](file:///c:/Users/ADMIN/Desktop/自主操盘/GBTXIAOTUDOUAI/gbt/api/payment.py) | 5 路由 | /status /link /probe /webhook /orders |

### 5 路由验证

| 路由 | 方法 | 实测 |
|------|------|------|
| /api/payment/status | GET | ✅ 200 · lock_status=ok · 3 套餐 · USD/EUR 主 + CNY 试用 |
| /api/payment/link | GET/POST | ✅ 200 · USD 10→120K tokens · CNY 100→165K tokens · iframe_html 自动生成 |
| /api/payment/probe | POST | ✅ 200 · L1 直连 1815ms · L2 curl_cffi chrome124 1377ms · 修复循环引用 |
| /api/payment/webhook | POST | ✅ 异步回调 + HMAC 验签 + 自动到账 Token |
| /api/payment/orders | GET | ✅ 200 · 历史订单列表 · developer=自由的风 |

### 5 道密钥防线

1. `.gitignore` + `.dockerignore` 排除 `.env`
2. `scripts/build_exe.py` 显式过滤 PyInstaller datas
3. `GBT_Desktop.spec` datas 排除
4. `Dockerfile` 运行时挂载 .env（不入镜像）
5. **`gbt/payment_lock.py`** 启动 SHA256 hash + `gbt/pay_futurapay._lock_keys()` 模块导入即锁 + 失配 raise + 审计

### 验收清单

| 项 | 目标 | 实测 |
|----|------|------|
| S2 镜像预演 | 100% | **7/7 (100%)** |
| pytest T-010 | 100% | **22/22 (100%)** |
| pytest 全量 | ≥95% | **127 passed / 128 (99.2%)**，唯一 fail 是 strategy 模块旧问题与本任务无关 |
| healthcheck | L1+L2+L3 全绿 | ✅ dashboard/chart/recap 都在 + 数据校验通过 + rollback endpoint 暴露 |
| HTTP 5xx | 0 | **0** |
| 蓝图挂载 | 13 → 14 | **14 ✅** |

### 已知风险与缓解

- **R1 · CNY 不在 Futurapay 官方文档**：已通过 EXPERIMENTAL 标记 + WARNING 日志让用户知情；widget 拒收自动回退，不会污染账本
- **R2 · stage URL 在部分地区不可达**：三层探测自动选最快可达层；L1 失败自动试 L2 curl_cffi chrome124
- **R3 · circular reference bug（已修复）**：probe_widget() 的 r→all_layers→[r] 自循环 → 改为显式剥离 inner all_layers

---