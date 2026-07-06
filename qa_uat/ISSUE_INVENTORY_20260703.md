# 2026-07-03 全量问题清单

## 审计原则

- 先记账，后修复；本文件只记录已复现问题、影响范围、模块归属和原子替换候选。
- 所有修复必须先在生产同构沙盒演练，通过后再做一次性模块替换。
- 发布前必须同时具备正向验证和回滚验证，不允许只测前进不测回退。

## 已确认问题

### P0-01 `mirror invoke` 在正式冻结运行时超时挂死

- 影响链路：`/api/mirror/invoke`，用户打开镜像空间或触发校验时会卡住并引发错误报警。
- 复现证据：
  - `POST /api/mirror/invoke {"skill":"validate","params":{}}` 在 95 秒内未返回。
  - `POST /api/mirror/invoke {"skill":"validate","extra":{},"dry_run":true}` 同样在 95 秒内未返回。
  - 直接在源码环境执行 `python .\gbt\mirror_space\sandbox-orchestrator.py --project . --validate` 会立即返回。
- 根因归属：
  - `gbt/mirror_space/bridge.py` 的 `_py()` 返回 `sys.executable`。
  - 当前正式运行线是冻结包，`release/current_runtime.ini` 指向 `dist_rebuild_parallel\GBT_Pro_v1.1.17_dir_parallel\GBT_Pro_v1.1.17_dir_parallel.exe`。
  - 冻结态下 `sys.executable` 是桌面 EXE，不是 Python 解释器；`invoke_skill()` 实际会尝试用 EXE 去执行 `mirror_skill.py`，这是错误子进程入口。
- 模块归属：
  - `gbt/mirror_space/bridge.py`
  - `gbt/api/mirror.py`
  - 运行时冻结环境
- 原子替换候选单元：
  - `Mirror Transport Unit`

### P0-02 `mirror` 返回契约直接泄露绝对路径和原始审计日志

- 影响链路：`/api/mirror/status`、`/api/mirror/skills`，前端直接展示后会把 `C:\...` 暴露到用户界面。
- 复现证据：
  - `GET /api/mirror/skills` 返回：
    - `latest_report.file = C:\Users\ADMIN\.gbt\sandbox\reports\sandbox-latest-review.json`
    - `latest_report.report.audit.output` 中包含 `C:\Users\ADMIN\.gbt\sandbox\mirror\sandbox`
    - `modules.command` 中包含多个 `C:\Users\ADMIN\.cline\...`
  - `GET /api/mirror/status` 设计上返回 `sandbox_dir` 和 `project_dir` 绝对路径。
- 根因归属：
  - `gbt/mirror_space/bridge.py` 的 `status()`、`latest_report()`、`Result.to_dict()`
  - `gbt/api/mirror.py` 直接透传上述结构
- 模块归属：
  - `gbt/mirror_space/bridge.py`
  - `gbt/api/mirror.py`
  - 前端镜像空间展示层
- 原子替换候选单元：
  - `Mirror Transport Unit`

### P1-03 截图接口响应体仍携带绝对路径

- 影响链路：`/api/hacker/exec` 的 `screenshot` 能力；虽然文案已改成相对友好提示，但 JSON 里仍有 `path` 绝对路径。
- 复现证据：
  - `POST /api/hacker/exec {"id":"screenshot","action":"运行"}` 返回：
    - `data = 截图已保存到 screenshots 目录：screenshot_20260703_011041.png`
    - `path = C:\Users\ADMIN\Desktop\自主操盘\GBTXIAOTUDOUAI\dist_rebuild_parallel\GBT_Pro_v1.1.17_dir_parallel\screenshots\...`
- 根因归属：
  - `gbt/api/audit.py` 的 `_exec_desktop("screenshot")` 返回体包含 `"path": path`
  - `gbt/api/hacker.py` 原样透传结果
- 模块归属：
  - `gbt/api/audit.py`
  - `gbt/api/hacker.py`
- 原子替换候选单元：
  - `Desktop Output Contract Unit`

### P1-04 全量审计脚本对 `hacker exec` 存在假阳性

- 影响链路：`qa_uat/audit_full.ps1`，会把失败接口记成通过，导致审计结果失真。
- 复现证据：
  - 脚本发送 `{"cmd":"echo","args":["hello from audit"]}` 到 `/api/hacker/exec`。
  - 实际接口要求的是 `id`，真实返回是 `{"ok":false,"error":"缺少能力ID"}`。
  - 但脚本只按 HTTP 200 计为通过，没有校验 `ok`。
- 根因归属：
  - `qa_uat/audit_full.ps1` 的 A8 组用例与真实接口契约不一致。
  - `gbt/api/hacker.py` 在错误场景仍返回 HTTP 200，放大了假阳性。
- 模块归属：
  - `qa_uat/audit_full.ps1`
  - `gbt/api/hacker.py`
- 原子替换候选单元：
  - `Audit Contract Unit`

### P1-05 沙盒模块发现器对当前仓库识别为 0 个模块

- 影响链路：镜像空间的校验、演练、部署闭环形同空跑，无法覆盖当前桌面应用真实模块。
- 复现证据：
  - `python .\gbt\mirror_space\sandbox-orchestrator.py --project . --discover`
  - 输出：`found 0 modules`
- 根因归属：
  - `gbt/mirror_space/sandbox-orchestrator.py` 的 `discover()` 只扫描项目根目录下一层子目录。
  - 当前仓库主应用在根目录本身，并不是子模块化布局。
- 模块归属：
  - `gbt/mirror_space/sandbox-orchestrator.py`
  - `gbt/mirror_space/module_registry.py`
- 原子替换候选单元：
  - `Mirror Discovery Unit`

### P2-06 前端日志区域会原样渲染后端 `data/error`

- 影响链路：任何后端一旦返回路径、命令输出或原始错误，都会直接出现在界面，放大用户感知报警。
- 复现证据：
  - `desktop/templates/layout.html`
  - `desktop/templates/partials/_scripts.html`
  - 都存在 `(d ? d.data || d.error || "" : "")` 原样写入日志区的逻辑。
- 根因归属：
  - 前端没有做 UI 安全投影，后端也没有统一脱敏层。
- 模块归属：
  - `desktop/templates/layout.html`
  - `desktop/templates/partials/_scripts.html`
- 原子替换候选单元：
  - `Desktop Output Contract Unit`

### P1-07 前端 `toast` 对非故障提示没有分流且缺少去重

- 影响链路：登录认证、OAuth、支付未配置、适配未完成等页面操作时，界面会连续弹出“警告/失败”提示，形成用户感知上的错误风暴。
- 复现证据：
  - `desktop/templates/partials/_scripts.html`
  - `desktop/templates/layout.html`
  - 原实现对所有消息统一 `toast(msg)`，没有区分故障与配置提示，也没有时间窗口去重。
  - 命中消息包括：
    - `授权尚未配置`
    - `已入入口矩阵，但桌面端适配器还没完成`
    - `读取 OAuth 配置失败`
    - `支付链路未配置`
- 根因归属：
  - 前端通知层未做“软提示/硬错误”分流。
  - 重复消息会在短时间内反复写入 toast 队列。
- 模块归属：
  - `desktop/templates/partials/_scripts.html`
  - `desktop/templates/layout.html`
- 原子替换候选单元：
  - `Desktop Notification Unit`

### P1-08 用户视角截图仍出现绝对项目路径文案

- 影响链路：正式 APP 用户体验验收阶段；桌面截图中前景 `GBT小土豆` 对话窗直接显示了 `当前项目：C:\Users\ADMIN\GBTXIAOTUDOUAI`。
- 复现证据：
  - [desktop_20260703_021553.png](file:///c:/Users/ADMIN/Desktop/%E8%87%AA%E4%B8%BB%E6%93%8D%E7%9B%98/GBTXIAOTUDOUAI/qa_uat/desktop_20260703_021553.png)
  - 当前截图里主窗口 `GBT Pro` 背后没有错误告警，但前景聊天窗存在用户可见路径泄露。
- 当前判断：
  - 泄露点不在主面板模板静态文案中，疑似来自 `GBT小土豆` 独立欢迎语或外部聊天窗初始化消息。
  - 需要继续确认该窗口是否属于当前正式包的一部分，还是桌面上另一个独立进程。
- 模块归属：
  - 待确认
- 原子替换候选单元：
  - `GBT Assistant Greeting Unit`

### P1-09 连接大模型成功但访客聊天被 0T 门禁拦截，用户感知为“能连不能用”

- 影响链路：`连接大模型 -> 智能对话`
- 真实现象：
  - 连接页显示“连接成功”
  - 聊天页在访客模式下直接返回“Token余额不足，请先充值”
  - 用户无法判断下一步该去登录、充值，还是重新连模型
- 根因：
  - 后端 `api_chat` 对 `_default` 访客余额为 `0` 的场景只返回通用充值错误，没有区分“访客未登录”和“已登录但余额不足”
  - 前端 `saveLLM()` 在连接成功后没有把用户引导到下一步动作
  - 前端 `sendChat()` 在访客 `0T` 场景下没有本地预检，导致用户先看到矛盾状态再被后端拦截
- 修复：
  - `gbt/api/llm.py`
    - `_default` 访客 `0T` 时返回明确文案：先登录领取新用户 `10000 tokens`，或前往充值激活
  - `desktop/templates/partials/_scripts.html`
  - `desktop/templates/layout.html`
    - 增加 `guideChatAccess()` 本地预检
    - 连接成功后主动读取余额并在访客 `0T` 时跳转到认证页
    - 聊天发送前本地拦截访客 `0T` 和已登录 `0T` 两种场景，分别引导到认证/充值
- 双重复检：
  - 第 1 轮：接口级复检
    - 访客 `POST /api/chat` 返回 `402`，但错误文案已明确为“先登录领取新用户10000 tokens，或前往充值激活”
    - 登录后 `POST /api/chat` 返回 `200`
  - 第 2 轮：浏览器级复检
    - 访客点击聊天发送后，页面直接切到 `auth` 页，不再出现“连接成功但不能聊”的矛盾报错
    - 登录态浏览器真实发送聊天后返回正常回答，`chat-auth-tip` 与剩余令牌同步更新
- 原子替换候选单元：
  - `LLM Connect + Chat Access Guard Unit`

## 原子替换候选单元

### Unit A `Mirror Transport Unit`

- 范围：
  - `gbt/mirror_space/bridge.py`
  - `gbt/api/mirror.py`
- 目标：
  - 修正冻结运行时子进程解释器入口。
  - 统一 `status/skills/invoke` 返回契约，只返回 UI 安全字段。
  - 去掉绝对路径、原始日志、宿主环境命令路径。
- 准入标准：
  - 正式冻结运行时下 `validate/status/skills` 都必须在超时阈值内返回。
  - 返回体不得含 `C:\`、`sandbox_dir`、`project_dir`、宿主机真实脚本路径。
  - 沙盒演练和回滚演练都要留档。

### Unit B `Desktop Output Contract Unit`

- 范围：
  - `gbt/api/audit.py`
  - `gbt/api/hacker.py`
  - 必要时连带桌面日志展示模板
- 目标：
  - 后端只返回相对路径或友好句柄，不再返回绝对路径。
  - 前端日志区只展示白名单字段，不直接吞原始报文。
- 准入标准：
  - 截图、桌面操控、黑客能力链路不再出现本机绝对路径。
  - 桌面 UI 连续实测不再弹出路径处理错误。

### Unit C `Audit Contract Unit`

- 范围：
  - `qa_uat/audit_full.ps1`
  - `qa_uat/deep_verify.ps1`
  - `tests/test_api_mirror.py`
  - `tests/test_api_hacker.py`
- 目标：
  - 测试脚本和真实接口契约对齐。
  - 把“HTTP 200 但业务失败”的假阳性剔除。
  - 增加“不得泄露绝对路径”和“冻结运行时 invoke 必须返回”的回归校验。
- 准入标准：
  - 审计脚本必须校验 `ok`、关键字段和超时。
  - 报告自动归档，未达标禁止进入发布步骤。

## 沙盒修复顺序

1. 先替换 `Unit A`，因为它同时覆盖超时挂死和路径泄露两类 P0。
2. 再替换 `Unit B`，消除桌面端剩余路径报警。
3. 最后替换 `Unit C`，把审计脚本改成能真正拦截问题的发布准入门。

## 发布合规要求

- 环境一致性：
  - 生产、演练、正式包必须使用同一运行时目录结构和锁定依赖。
  - 禁止用源码直跑结果代替冻结包结论。
- 数据一致性：
  - 任何涉及迁移、审计报告、镜像缓存的改动必须有前进脚本和回退方案。
  - 发布前先做快照，回滚演练通过后才允许切换。
- 验证与观测：
  - 必须在生产同构沙盒完成正向演练、回滚演练、日志归档、性能记录。
  - 通过标准至少包含错误率、超时率、关键业务链路成功率和用户界面无路径报警。
