#!/usr/bin/env node
/**
 * Deep scan for production-readiness issues in app/src.
 * Run with: node scripts/deep-scan.mjs  (or bun scripts/deep-scan.mjs)
 */
import { readdir, readFile, stat } from "node:fs/promises";
import { join, extname } from "node:path";

const ROOT = new URL("../app/src", import.meta.url).pathname.replace(/^\/([A-Za-z]:\/)/, "$1");

const SCANNED_EXTS = new Set([".ts", ".tsx", ".js", ".jsx", ".css"]);

const RULES = [
  {
    id: "debug-console-log",
    severity: "error",
    pattern: /console\.log\s*\(/,
    message: "Unexpected console.log (keep only console.error for error handlers)",
  },
  {
    id: "debugger-statement",
    severity: "error",
    pattern: /debugger\s*;/,
    message: "Debugger statement left in source",
  },
  {
    id: "eval-usage",
    severity: "error",
    pattern: /\beval\s*\(/,
    message: "eval() usage is dangerous in production",
  },
  {
    id: "secret-like-string",
    severity: "warning",
    pattern: /\b(api[_-]?key|secret|token|password|private[_-]?key)\s*[:=]\s*["'`][^"'`\s]{12,}["'`]/i,
    message: "Possible hardcoded secret-like value",
  },
  {
    id: "sk-pattern",
    severity: "warning",
    pattern: /\b(sk-[a-zA-Z0-9]{24,}|ghp_[a-zA-Z0-9]{20,}|AKIA[0-9A-Z]{16})\b/,
    message: "Possible API key/token pattern",
  },
  {
    id: "todo-fixme",
    severity: "warning",
    pattern: /\b(TODO|FIXME|HACK|XXX)\b/,
    message: "Outstanding TODO/FIXME/HACK marker",
  },
  {
    id: "non-localhost-url",
    severity: "info",
    pattern: /https?:\/\/[^\s"'`]+\.[a-z]{2,}\b/,
    message: "Non-localhost URL (review if intentional)",
  },
];

async function* walk(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  for (const entry of entries) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) {
      yield* walk(path);
    } else if (entry.isFile() && SCANNED_EXTS.has(extname(entry.name))) {
      yield path;
    }
  }
}

const findings = [];
for await (const path of walk(ROOT)) {
  const text = await readFile(path, "utf8");
  const lines = text.split("\n");
  const relative = path.replace(ROOT, "").replace(/^\\/, "");

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    for (const rule of RULES) {
      if (rule.pattern.test(line)) {
        // Allowlist: alert() in ErrorBoundary is intentional UX feedback
        if (rule.id === "non-localhost-url" && line.includes("127.0.0.1")) continue;
        findings.push({
          file: relative,
          line: i + 1,
          severity: rule.severity,
          rule: rule.id,
          message: rule.message,
          snippet: line.trim().slice(0, 120),
        });
      }
    }
  }
}

const errors = findings.filter((f) => f.severity === "error");
const warnings = findings.filter((f) => f.severity === "warning");
const infos = findings.filter((f) => f.severity === "info");

for (const f of findings) {
  console.log(`${f.severity.toUpperCase()} [${f.rule}] ${f.file}:${f.line} ${f.message}`);
  console.log(`  ${f.snippet}`);
}

console.log(`\nScanned ${ROOT}`);
console.log(`Errors: ${errors.length}, Warnings: ${warnings.length}, Info: ${infos.length}`);

if (errors.length > 0) {
  process.exit(1);
}
