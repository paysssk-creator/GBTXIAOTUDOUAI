import { mkdir, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import type { ForgeConfig } from "../types.js";
import { LLMClient } from "../llm/client.js";

/**
 * 多维度思维导图能力(集成自 siweidaotu* 仓库的各引擎维度)：
 * 一个主题 → 一次产出 Markmap 交互脑图(HTML) + Mermaid 脑图 + Mermaid 流程图 + Markdown 大纲。
 */

export interface MindNode {
  title: string;
  children?: MindNode[];
}

export interface MindmapResult {
  dir: string;
  files: { outline: string; markmapHtml: string; mermaidMind: string; mermaidFlow: string; json: string };
}

const TREE_FORMAT = "只输出一个 JSON 对象, 形如 {\"title\":\"主题\",\"children\":[{\"title\":\"分支\",\"children\":[{\"title\":\"要点\"}]}]}。不要任何解释、不要markdown围栏。";

/** 让 LLM 产出层级树(JSON)。mode=understand 时是"对需求的理解"(供用户确认) */
async function genTree(topic: string, cfg: ForgeConfig, useStrong: boolean, mode: "topic" | "understand" = "topic"): Promise<MindNode> {
  const llm = new LLMClient(cfg, useStrong && cfg.cloudLlm ? cfg.cloudLlm : undefined);
  const sys =
    mode === "understand"
      ? `你是需求分析师。把用户的需求拆解成"你的理解"的思维导图, 一级分支固定为: 目标、功能模块、技术要点、边界与异常、验收标准。让用户一眼看懂你打算做什么、好确认或纠正。${TREE_FORMAT}`
      : `你是思维导图专家。层级清晰、覆盖全面(3-5 个一级分支, 每个再展开)。${TREE_FORMAT}`;
  const user = mode === "understand" ? `用户需求(请输出你理解后的拆解导图, 供确认): ${topic}` : `为主题生成多维度思维导图结构: ${topic}`;
  const raw = await llm.chat([
    { role: "system", content: sys },
    { role: "user", content: user },
  ]);
  const jsonStr = raw.replace(/```[a-z]*\n?/gi, "").trim();
  try {
    const start = jsonStr.indexOf("{");
    const end = jsonStr.lastIndexOf("}");
    return JSON.parse(jsonStr.slice(start, end + 1));
  } catch {
    return { title: topic, children: [{ title: "(模型未产出有效结构, 原文)" }, { title: jsonStr.slice(0, 200) }] };
  }
}

function toOutline(n: MindNode, depth = 0): string {
  const head = depth === 0 ? `# ${n.title}\n` : `${"  ".repeat(depth - 1)}- ${n.title}\n`;
  return head + (n.children || []).map((c) => toOutline(c, depth + 1)).join("");
}

function toMermaidMind(n: MindNode, depth = 1): string {
  if (depth === 1) {
    const root = `mindmap\n  root((${n.title}))\n`;
    return root + (n.children || []).map((c) => toMermaidMind(c, depth + 1)).join("");
  }
  const indent = "  ".repeat(depth);
  return `${indent}${n.title.replace(/[()]/g, "")}\n` + (n.children || []).map((c) => toMermaidMind(c, depth + 1)).join("");
}

function toMermaidFlow(n: MindNode): string {
  const lines: string[] = ["flowchart TD"];
  let id = 0;
  const ids = new Map<MindNode, string>();
  const ider = (node: MindNode) => {
    if (!ids.has(node)) ids.set(node, "N" + id++);
    return ids.get(node)!;
  };
  const walk = (node: MindNode) => {
    const pid = ider(node);
    lines.push(`  ${pid}["${node.title.replace(/"/g, "'")}"]`);
    for (const c of node.children || []) {
      lines.push(`  ${pid} --> ${ider(c)}`);
      walk(c);
    }
  };
  walk(n);
  return lines.join("\n");
}

/** HTML实体转义 — 防XSS */
function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function markmapHtml(title: string, markdown: string): string {
  return `<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><title>${escapeHtml(title)} · 思维导图</title>
<style>html,body{margin:0;height:100%}.markmap{height:100vh}</style></head><body>
<div class="markmap"><script type="text/template">
${escapeHtml(markdown)}
</script></div>
<script src="https://cdn.jsdelivr.net/npm/markmap-autoloader@0.18"></script>
</body></html>`;
}

export async function generateMindmap(topic: string, cfg: ForgeConfig, useStrong = false, mode: "topic" | "understand" = "topic"): Promise<MindmapResult> {
  const tree = await genTree(topic, cfg, useStrong, mode);
  const outline = toOutline(tree);
  const mind = toMermaidMind(tree);
  const flow = toMermaidFlow(tree);

  const safe = topic.replace(/[^\w一-龥]+/g, "_").slice(0, 30) || "mindmap";
  const dir = path.join(os.homedir(), ".gbt", "mindmaps", `${safe}-${Date.now()}`);
  await mkdir(dir, { recursive: true });
  const files = {
    outline: path.join(dir, "outline.md"),
    markmapHtml: path.join(dir, "mindmap.html"),
    mermaidMind: path.join(dir, "mindmap.mmd"),
    mermaidFlow: path.join(dir, "flowchart.mmd"),
    json: path.join(dir, "tree.json"),
  };
  await writeFile(files.outline, outline, "utf8");
  await writeFile(files.markmapHtml, markmapHtml(topic, outline), "utf8");
  await writeFile(files.mermaidMind, mind, "utf8");
  await writeFile(files.mermaidFlow, flow, "utf8");
  await writeFile(files.json, JSON.stringify(tree, null, 2), "utf8");
  return { dir, files };
}
