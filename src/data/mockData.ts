export const systemStatus = {
  llm: "DeepSeek v3",
  provider: "deepseek",
  model: "deepseek-chat",
  mcpCount: 18,
  keysAvailable: 5,
  keysTotal: 13,
  uptime: "7h 23m",
  version: "v2.1.0619",
};

export const agents = [
  { id: "brain", name: "Brain Agent", role: "主脑决策引擎", status: "online" as const, tasks: 142, lastActive: "0s", memory: "2.3 MB", model: "DeepSeek v3" },
  { id: "watcher", name: "Night Watcher", role: "7×24 守夜人监控", status: "online" as const, tasks: 89, lastActive: "1s", memory: "1.1 MB", model: "GLM-5.1" },
  { id: "trader", name: "AShare Trader", role: "A股自动操盘手", status: "online" as const, tasks: 34, lastActive: "3s", memory: "3.7 MB", model: "DeepSeek v3" },
  { id: "desktop", name: "Desktop Controller", role: "桌面GUI自动化", status: "online" as const, tasks: 17, lastActive: "12s", memory: "0.8 MB", model: "GPT-4o" },
  { id: "ocr", name: "OCR Engine", role: "图像文字识别", status: "online" as const, tasks: 56, lastActive: "8s", memory: "4.2 MB", model: "Tesseract" },
  { id: "scraper", name: "Market Scraper", role: "行情数据采集", status: "online" as const, tasks: 210, lastActive: "0s", memory: "1.5 MB", model: "N/A" },
  { id: "reasoner", name: "Deep Reasoner", role: "8模式深度推理", status: "idle" as const, tasks: 8, lastActive: "2m", memory: "0.6 MB", model: "Claude 3.5" },
  { id: "guard", name: "Guard Scanner", role: "行动前安全守卫", status: "online" as const, tasks: 23, lastActive: "5s", memory: "0.4 MB", model: "N/A" },
];

export const marketIndices = [
  { code: "sh000001", name: "上证指数", price: 3312.48, change: 18.76, changePct: 0.57, volume: "2847亿", high: 3325.12, low: 3289.34 },
  { code: "sz399001", name: "深证成指", price: 10521.33, change: -42.15, changePct: -0.40, volume: "3621亿", high: 10598.44, low: 10489.22 },
  { code: "sz399006", name: "创业板指", price: 2098.77, change: 23.44, changePct: 1.13, volume: "1234亿", high: 2112.88, low: 2071.55 },
  { code: "sh000688", name: "科创50", price: 987.65, change: 5.32, changePct: 0.54, volume: "412亿", high: 992.10, low: 979.88 },
  { code: "sh000300", name: "沪深300", price: 3889.24, change: -12.33, changePct: -0.32, volume: "5213亿", high: 3912.45, low: 3874.12 },
  { code: "sz399005", name: "中小100", price: 6234.11, change: 87.23, changePct: 1.42, volume: "876亿", high: 6280.00, low: 6190.34 },
];

export const auditReport = {
  timestamp: "2026-06-19T22:09:33.370Z",
  summary: { passed: 7, warnings: 2, failed: 0 },
  passed: [
    "Git 仓库已初始化",
    "当前分支: main",
    "已配置远程仓库",
    ".clinerules 存在",
    ".gitignore 存在",
    ".env.example 存在 (或 .env 已在 gitignore)",
    "Python 依赖文件存在",
  ],
  warnings: [
    { name: "无未提交改动 (当前: 4)", detail: "有 4 个文件未提交，建议在上线前完成 commit" },
    { name: "测试套件覆盖率", detail: "项目无完整测试，修改后无法自动验证，建议补充单元测试" },
  ],
  failed: [] as string[],
  v12: {
    compile: { passed: 43, total: 43 },
    api: { passed: 9, total: 9 },
    router: { passed: 19, total: 19 },
    runtime: "brain/watcher/trader 全绿",
    threadSafety: "Logger模态级变量，非竞争",
    logic: "无永真/永假条件",
    typeSafety: "无 arithmetic-on-get 模式",
  },
};

export const systemResources = {
  cpu: 23,
  memory: 67,
  gpu: 15,
  network: 8,
  memoryUsedGB: 10.7,
  memoryTotalGB: 16,
  uptime: "7h 23m 14s",
};

export type ChatRole = "system" | "user" | "ai";
export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  timestamp: string;
}

export const initialChatMessages: ChatMessage[] = [
  { id: "s1", role: "system", content: "GBT Pro v2.1.0619 已启动 — AI 驱动 A 股自主交易终端", timestamp: "09:30:00" },
  { id: "s2", role: "system", content: "模型: DeepSeek v3 | MCP: 18 服务 | 守夜人: 运行中 | 风控: 激活", timestamp: "09:30:01" },
];

export const mockResponses = [
  `根据当前市场数据，上证指数收涨 0.57%，成交量 2847 亿，市场情绪偏乐观。

建议关注：创业板指涨幅 1.13%，成长板块活跃；中小100 领涨 1.42%。深证成指小幅回调，关注 10450 支撑位。

风控提醒：仓位不宜超过 60%，保留足够流动性应对波动。`,
  `MACD 指标日线级别底部背离，RSI 当前 42，中性偏低区域，有上行空间。

技术面：MA5 > MA10 > MA20 多头排列，近 3 日量能温和放大，布林带中轨上方运行。

操作建议：可分批建仓，止损设于前低位置。`,
  `当前 5 个 API 密钥可用，DeepSeek v3 延迟 187ms，系统运行正常。

守夜人状态：扫描频率每 30 秒，已发现 0 个异常，风控 120 分钟冷却机制激活。`,
];
