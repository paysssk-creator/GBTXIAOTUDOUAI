-- ============================================================
-- v001: Initial Schema Rollback (DOWN)
-- 删除 v001 创建的所有表和索引
-- 幂等: 全部使用 IF EXISTS
-- ============================================================

DROP INDEX IF EXISTS idx_kline_cache_day;
DROP INDEX IF EXISTS idx_kline_cache_code_scale;
DROP INDEX IF EXISTS idx_sessions_status;
DROP INDEX IF EXISTS idx_sessions_code;
DROP INDEX IF EXISTS idx_signals_action;
DROP INDEX IF EXISTS idx_signals_time;
DROP INDEX IF EXISTS idx_signals_code;
DROP INDEX IF EXISTS idx_trades_action;
DROP INDEX IF EXISTS idx_trades_time;
DROP INDEX IF EXISTS idx_trades_code;

DROP TABLE IF EXISTS blacklist;
DROP TABLE IF EXISTS kline_cache;
DROP TABLE IF EXISTS risk_config;
DROP TABLE IF EXISTS strategy_config;
DROP TABLE IF EXISTS daily_stats;
DROP TABLE IF EXISTS sessions;
DROP TABLE IF EXISTS signals;
DROP TABLE IF EXISTS trades;
DROP TABLE IF EXISTS positions;
DROP TABLE IF EXISTS accounts;
