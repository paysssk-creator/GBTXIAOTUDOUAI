import { useCallback, useEffect, useState } from "react";
import { fetchData, postData } from "../lib/api";

export interface Skill {
  name: string;
  description: string;
  icon?: string;
}

export function useSkills() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchSkills = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchData<{ skills: Skill[] }>("/api/skills");
      setSkills(result.skills || []);
    } catch {
      // Fallback skill list if endpoint doesn't exist yet
      setSkills([
        { name: "screen_ocr", description: "屏幕 OCR 识别" },
        { name: "browser_open", description: "打开浏览器" },
        { name: "web_search", description: "网络搜索" },
        { name: "maximize", description: "窗口最大化" },
        { name: "screenshot", description: "截屏" },
        { name: "stock_lookup", description: "股票查询" },
        { name: "scan_market", description: "市场扫描" },
        { name: "trade", description: "执行交易" },
        { name: "watchlist", description: "自选股监控" },
        { name: "system_status", description: "系统状态" },
        { name: "watcher_check", description: "Watcher 检查" },
        { name: "account_query", description: "账户查询" },
        { name: "auto_pipeline", description: "自动流水线" },
        { name: "code_exec", description: "代码执行" },
        { name: "file_operation", description: "文件操作" },
        { name: "login_detect", description: "登录检测" },
        { name: "notify", description: "发送通知" },
        { name: "precision_scrape", description: "精准抓取" },
        { name: "voice_speak", description: "语音播报" },
        { name: "cradle_task", description: "Cradle 任务" },
        { name: "screenpipe_monitor", description: "ScreenPipe 监控" },
      ]);
    } finally {
      setLoading(false);
    }
  }, []);

  const invokeSkill = useCallback(async (name: string, params?: unknown) => {
    try {
      const result = await postData<Record<string, unknown>>(`/api/skill/${name}`, params ?? {});
      return { ok: true, result };
    } catch (err) {
      return { ok: false, error: err instanceof Error ? err.message : String(err) };
    }
  }, []);

  useEffect(() => {
    fetchSkills();
  }, [fetchSkills]);

  return { skills, loading, refresh: fetchSkills, invokeSkill };
}
