# 真实券商灰度门禁报告

- 时间：2026-07-05 01:39:14
- 模式：AppOnlyPreview
- 候选包：release/GBT_Pro_v1.1.19_portable_download.zip
- SHA256：2605f2d5c4a0a5b016cb3fad49b1bbdbfa0bfc814c72c933c08bbe58690ca64f
- 运行时：c:\Users\ADMIN\Desktop\自主操盘\GBTXIAOTUDOUAI\dist_runtime_fresh5\GBT_Pro_v1.1.19_dir_parallel
- 结果：PRECHECK PASS

## 自动步骤

- [PASS] 01-候选包与哈希一致性 | zip_hash_ok=2605f2d5c4a0a5b016cb3fad49b1bbdbfa0bfc814c72c933c08bbe58690ca64f
- [PASS] 02-运行时指针检查 | runtime_exe=c:\Users\ADMIN\Desktop\自主操盘\GBTXIAOTUDOUAI\dist_runtime_fresh5\GBT_Pro_v1.1.19_dir_parallel\GBT_Pro_v1.1.19_dir_parallel.exe
- [PASS] 03-服务状态 | version=v1.1.19 role=desktop
- [PASS] 04-真实动作链冒烟 | chat_action_ok
- [PASS] 05-接管预检 | precheck=passed next=trade_form_fill
- [PASS] 06-唯一下一步预演 | planned=trade_form_fill
- [PASS] 07-闭环验证预演 | evidence_plan=audit_evidence/trade_validate_20260705_013914_同花顺_600519.json
- [PASS] 08-发布门禁状态检查 | gate_status=blocked_pending_real_broker_gray_acceptance

## 人工待办

- [ ] 真实券商窗口登录态检查
- [ ] 真实 trade_panel_probe 回读确认
- [ ] 最小风险单量灰度执行
- [ ] 回滚演练留档
- [ ] 签收人复核

## 归档

- JSON 报告：c:\Users\ADMIN\Desktop\自主操盘\GBTXIAOTUDOUAI\qa_uat\REAL_BROKER_GRAY_GATE_20260705_013911.json
- 清单：qa_uat\REAL_BROKER_GRAY_ACCEPTANCE_20260705.md
