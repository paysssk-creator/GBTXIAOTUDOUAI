# GBT Pro v1.1.19 真实券商登录态灰度验收清单

## 当前发布状态

- 当前候选包：`release/GBT_Pro_v1.1.19_portable_download.zip`
- 当前 SHA256：`2605f2d5c4a0a5b016cb3fad49b1bbdbfa0bfc814c72c933c08bbe58690ca64f`
- 当前运行时指针：`release/current_runtime.ini -> dist_runtime_fresh5/GBT_Pro_v1.1.19_dir_parallel`
- 当前结论：已完成 `APP 内闭环 + 真实便携包执行链` 验证，但尚未完成真实券商登录态灰度签收
- 发布门禁：本清单未全部通过前，禁止进入正式发布或对外宣称“已完成真实实盘验收”

## 自动执行入口

- 本地预检命令：`pwsh -NoProfile -ExecutionPolicy Bypass -File qa_uat/run_real_broker_gray_gate.ps1 -AppOnlyPreview`
- 真实灰度命令：`pwsh -NoProfile -ExecutionPolicy Bypass -File qa_uat/run_real_broker_gray_gate.ps1`
- 脚本输出：会在 `qa_uat/` 生成 `REAL_BROKER_GRAY_GATE_*.json` 和 `REAL_BROKER_GRAY_GATE_*.md`

## 强制准入规则

### 1. 环境一致性

- 灰度机必须使用与候选发布物完全相同的 ZIP 和 SHA256，禁止临时改文件、禁止手工热修
- 灰度机必须与目标生产机保持同构：Windows 版本、分辨率、缩放比例、券商客户端版本、网络出口、输入法、权限级别一致
- 启动方式必须走不可变目录切换：新包解压到独立目录，验证通过后再一次性切换桌面入口，禁止覆盖式原地更新
- 所有配置只能来自本地配置文件或变量，禁止把券商账号、密钥、验证码规则写进脚本和文档
- 灰度演练前必须保留上一版可回退包和快捷方式，回退资产缺失则禁止开始

### 2. 数据一致性

- 不允许对券商客户端、数据库、配置目录做手工直接修改
- 灰度前必须备份以下内容：
  - 当前便携运行时目录
  - 当前桌面快捷方式或启动入口
  - 本次灰度使用的券商客户端版本信息与登录态截图
- 所有真实交易验证必须先跑一次 `dry_run` 或预演链，确认契约一致后才能进入最小灰度单
- 新包产生的截图、日志、验证报告必须能被旧包读取和留档，禁止引入回退后不可读的新格式

### 3. 验证与观测

- 必须先在生产同构沙盒完成一次正向演练和一次回滚演练，未演练禁止上灰度机
- 灰度执行时必须同时开启日志、截图归档、接口回包留档
- 任一关键指标超阈值必须立即回滚，不允许“先放着观察”
- 灰度完成后必须校验：
  - 核心业务结果
  - 关键页面状态
  - 证据文件完整性
  - 回滚路径可用性

## 原子替换要求

- 接口契约稳定：灰度期间 `trade_takeover_precheck`、`trade_execute_next`、`trade_live_validate` 的输入输出字段不得变化
- 数据层隔离：新旧包都只能写各自运行目录，不得覆盖对方证据和日志
- 渐进发布：只允许一台机器、一个券商、一个低风险账户先灰度，禁止一上来全量替换
- 真正原子切换：只允许通过新目录 + 新快捷方式一次性切换，禁止在旧目录里增量替换文件

## 灰度执行顺序

### 阶段 A：预演门禁

- [ ] 校验 ZIP 与 SHA256 完全一致
- [ ] 校验 `release/current_runtime.ini` 指向本次候选运行时
- [ ] 启动新包，确认 `/api/status` 正常
- [ ] 执行 `/api/chat` 真实动作链冒烟
- [ ] 执行 `trade_takeover_precheck`
- [ ] 执行 `trade_execute_next` 预演链
- [ ] 执行 `trade_live_validate` 预演链并确认能生成证据计划
- [ ] 完成一次完整回滚演练并记录恢复时间

### 阶段 B：登录态灰度

- [ ] 券商窗口已登录且保持前台可见
- [ ] `trade_takeover_precheck` 返回 `precheck_passed=true`
- [ ] `trade_panel_probe` 能识别锚点、委托区、持仓区
- [ ] `trade_form_fill` 在真实登录态下先完成一次预演
- [ ] 已勾选高风险确认，且人工确认人已到位
- [ ] 使用最小风险单量执行一次灰度单
- [ ] `trade_submit_confirm` 返回成功
- [ ] `trade_result_watch` 返回成功并能回读结果
- [ ] 所有证据文件已归档到 `screenshots/` 和 `audit_evidence/`

### 阶段 C：收口与回滚验证

- [ ] 核心指标全部达标
- [ ] 业务结果与券商界面一致
- [ ] 重新启动应用后状态正常
- [ ] 按回滚脚本或回滚目录完成一次退回验证
- [ ] 旧版入口恢复后，`/api/status`、`/api/chat`、桌面基础能力验证正常

## 通过标准

- 错误率：`0%`
- `trade_takeover_precheck` 单次响应：`<= 5s`
- `trade_execute_next` 单次响应：`<= 8s`
- `trade_result_watch` 完成判定：`<= 15s`
- 灰度期间 CPU 峰值：`< 80%`
- 灰度期间内存峰值：`< 1.5 GB`
- 关键业务指标：
  - 实际提交结果与界面显示一致
  - 委托代码、持仓代码回读一致
  - 证据截图与 JSON 报告时间戳一致

## 立即回滚触发器

- `trade_submit_confirm` 返回失败
- `trade_result_watch` 超时或返回失败
- 回读代码与目标代码不一致
- 界面锚点错位、识别窗口错误、账户错位
- 关键日志缺失、证据归档失败、截图为空白
- 错误率非零或关键延迟超过阈值

## 回滚步骤

1. 停止当前 `fresh5` 运行进程
2. 恢复上一版已签收运行时目录和桌面入口
3. 验证 `/api/status`、`/api/chat`、`browser_open`、`trade_takeover_precheck`
4. 记录回滚耗时、回滚原因、恢复后版本号
5. 将本次灰度日志、截图、报告归档到 `qa_uat/` 并标记失败

## 归档要求

- 必须归档：
  - 灰度机环境截图
  - 券商登录态截图
  - `trade_live_validate` 返回 JSON
  - `screenshots/trade_validate_*.png`
  - `audit_evidence/trade_validate_*.json`
  - 回滚演练日志
  - 本次候选 ZIP 的 SHA256 文件
- 归档不完整视为未通过

## 签收记录

- 发布候选：`v1.1.19`
- 验收日期：`待填写`
- 灰度机器：`待填写`
- 券商客户端：`待填写`
- 操作账户：`待填写`
- 执行人：`待填写`
- 复核人：`待填写`
- 回滚演练通过：`否`
- 灰度结论：`待签收`