# GBT Pro Web Dashboard — Implementation Plan

## Context
Build a professional dark-theme Web Dashboard UI for the GBT Pro AI trading terminal (https://github.com/paysssk-creator/GBTXIAOTUDOUAI). This is a **frontend-only** React app that:
- Displays mock data mirroring GBT Pro's real API structure (at `localhost:8765`)
- Can be connected to the live GBT Pro Python backend if available

## Pages & Features

| Page | Route | Content |
|------|-------|---------|
| Overview | `/` | Status cards, market ticker bar, audit summary widget, system resource gauges |
| Agent Monitor | `/agents` | Agent cards grid with live pulse indicators |
| Market Data | `/market` | A-share index table (up=green, down=red) |
| Audit Report | `/audit` | KPI row (passed/warnings/failed), event timeline |
| AI Chat | `/chat` | Dark terminal-style LLM chat interface |

## Design System Changes

**`src/index.css`** — Full dark theme rewrite:
- Page bg: `#0D1117`, Cards: `#161B27`, Overlay: `#1E2538`
- Primary (gold): `#F59E0B`, Gain: `#22C55E`, Loss: `#EF4444`
- Add CSS vars: `--color-gain`, `--color-loss`, `--color-terminal-bg`, `--color-sidebar-bg`, `--shadow-card-brand`, etc.
- Add `@font-face` for JetBrains Mono (via Google Fonts import)
- Add keyframe animations: `pulse`, `blink`, `marquee`, `flash-gain`, `flash-loss`

**`tailwind.config.ts`** — Extend with `gain`, `loss`, `terminal`, `sidebar` color tokens and font stacks.

## File Structure (new files)

```
src/
  data/
    mockData.ts              ← All mock data (agents, market, audit, chat, system)
  components/
    layout/
      Sidebar.tsx            ← Fixed sidebar with nav items + logo
      DashboardLayout.tsx    ← Sidebar + main content wrapper
    dashboard/
      StatusCard.tsx         ← KPI card with icon, value, delta, status dot
      MarketTickerBar.tsx    ← Scrolling marquee of index prices
      SystemGauge.tsx        ← SVG arc gauge (CPU, RAM, GPU, Network)
      AgentCard.tsx          ← Agent status card with pulse indicator
      AuditTimeline.tsx      ← Scrollable audit event list
      ChatMessage.tsx        ← Single terminal-style chat message
  pages/
    Overview.tsx             ← Dashboard home
    AgentMonitor.tsx         ← Agent grid
    MarketData.tsx           ← Index table
    AuditReport.tsx          ← Audit KPIs + timeline
    AIChat.tsx               ← Terminal chat
```

## Files to Modify

- `src/index.css` — full rewrite with dark theme tokens
- `tailwind.config.ts` — extend colors & fonts
- `src/router.tsx` — add 4 new routes (agents, market, audit, chat)
- `src/pages/Index.tsx` — replace with Overview page
- `src/App.tsx` — wrap with DashboardLayout

## Mock Data (mockData.ts)

```ts
// Status cards: LLM=DeepSeek v3, MCP=18 servers, Keys=5 available/13 total
// Agents: Brain, WatcherAgent, AShareTrader, DesktopCtl, OCR, Scraper (all ONLINE)
// Market: SSE+SZSE+CSI300+ChiNext+STAR50+CSI100 with realistic prices/changes
// Audit: 7 passed, 2 warnings, 0 failed (from real AUDIT_REPORT.json)
// Chat: system welcome message
// System: CPU 23%, RAM 67%, GPU 15%, Network 8%
```

## Key Component Details

### StatusCard
- Icon + title (uppercase small) + live dot
- Large mono value + color-coded delta
- Gold glow border variant

### SystemGauge
- SVG arc ring (circumference calc)
- Color switches: <70%=green, 70-89%=amber, ≥90%=red
- Animated stroke-dashoffset on mount

### MarketTickerBar
- CSS marquee animation (horizontal scroll)
- Each ticker: code + price + colored change %

### AI Chat
- Terminal bg `#080C12`
- Messages: `[SYSTEM]`, `›` USER, `[GBT]` AI
- Mock streaming effect (typewriter on page load)
- Send button dispatches to mock response

## Routing
Use existing React Router (already in `src/router.tsx`). Wrap all routes in `DashboardLayout`.

## Verification
- All 5 pages render without errors
- Dark theme consistent across all pages
- Numbers use monospace font
- Green/red color coding works on market table
- Gauges animate on mount
- Chat send button shows mock AI response
