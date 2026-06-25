import { useCallback, useEffect, useState } from "react";
import { fetchData, postData } from "../lib/api";

export interface Skill {
  name: string;
  description: string;
  category?: string;
  icon?: string;
}

export interface SkillResult {
  ok: boolean;
  data?: unknown;
  message?: string;
  error?: string;
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
        { name: "screen_ocr", description: "屏幕 OCR 识别", category: "desktop" },
        { name: "browser_open", description: "打开浏览器", category: "desktop" },
        { name: "web_search", description: "网络搜索", category: "hacker" },
        { name: "maximize", description: "窗口最大化", category: "desktop" },
        { name: "screenshot", description: "截屏", category: "desktop" },
        { name: "stock_lookup", description: "股票查询", category: "trading" },
        { name: "scan_market", description: "市场扫描", category: "trading" },
        { name: "trade", description: "执行交易", category: "trading" },
        { name: "watchlist", description: "自选股监控", category: "trading" },
        { name: "system_status", description: "系统状态", category: "system" },
        { name: "watcher_check", description: "Watcher 检查", category: "system" },
        { name: "account_query", description: "账户查询", category: "system" },
        { name: "auto_pipeline", description: "自动流水线", category: "trading" },
        { name: "code_exec", description: "代码执行", category: "hacker" },
        { name: "file_operation", description: "文件操作", category: "hacker" },
        { name: "login_detect", description: "登录检测", category: "desktop" },
        { name: "notify", description: "发送通知", category: "notification" },
        { name: "precision_scrape", description: "精准抓取", category: "hacker" },
        { name: "voice_speak", description: "语音播报", category: "notification" },
        { name: "cradle_task", description: "Cradle 任务", category: "desktop" },
        { name: "screenpipe_monitor", description: "ScreenPipe 监控", category: "desktop" },
      ]);
    } finally {
      setLoading(false);
    }
  }, []);

  const invokeSkill = useCallback(async (name: string, text = "", params?: Record<string, unknown>): Promise<SkillResult> => {
    try {
      return await postData<SkillResult>(`/api/skill/${name}`, { text, params: params ?? {} });
    } catch (err) {
      return { ok: false, error: err instanceof Error ? err.message : String(err) };
    }
  }, []);

  useEffect(() => {
    fetchSkills();
  }, [fetchSkills]);

  return { skills, loading, refresh: fetchSkills, invokeSkill };
}
