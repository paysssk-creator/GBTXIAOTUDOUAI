import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

interface Shortcut {
  keys: string[];
  description: string;
}

const IS_MAC = typeof navigator !== "undefined" && navigator.platform.toLowerCase().includes("mac");
const MOD = IS_MAC ? "⌘" : "Ctrl";

const SHORTCUTS: Shortcut[] = [
  { keys: ["?"], description: "打开/关闭快捷键帮助" },
  { keys: [MOD, "1"], description: "切换到主页" },
  { keys: [MOD, "2"], description: "切换到对话" },
  { keys: [MOD, "3"], description: "切换到 Skills" },
  { keys: [MOD, "4"], description: "切换到设置" },
  { keys: ["←", "→"], description: "在底部导航间移动" },
  { keys: [MOD, "K"], description: "聚焦 Skills 搜索框" },
  { keys: [MOD, "Shift", "R"], description: "重新加载 Chat 页面" },
  { keys: [MOD, "Shift", "T"], description: "切换主题" },
  { keys: ["Esc"], description: "关闭弹窗、通知或返回上一页" },
];

function isTypingTarget(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false;
  const tag = el.tagName.toLowerCase();
  return (
    tag === "input" ||
    tag === "textarea" ||
    tag === "select" ||
    el.isContentEditable
  );
}

export function KeyboardShortcutsHelp() {
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "?" && !isTypingTarget(e.target)) {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
      if (e.key === "Escape") {
        setOpen(false);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  useEffect(() => {
    if (open) {
      closeButtonRef.current?.focus();
      const onClickOutside = (e: MouseEvent) => {
        if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
          setOpen(false);
        }
      };
      document.addEventListener("mousedown", onClickOutside);
      return () => document.removeEventListener("mousedown", onClickOutside);
    }
  }, [open]);

  if (!open) return null;

  return createPortal(
    <div className="shortcut-modal-overlay" role="dialog" aria-modal="true" aria-labelledby="shortcut-title">
      <div className="shortcut-modal" ref={panelRef}>
        <div className="shortcut-modal-header">
          <h2 id="shortcut-title" className="shortcut-modal-title">
            键盘快捷键
          </h2>
          <button
            ref={closeButtonRef}
            className="btn btn-ghost btn-sm"
            onClick={() => setOpen(false)}
            aria-label="关闭快捷键帮助"
          >
            ✕
          </button>
        </div>
        <div className="shortcut-list">
          {SHORTCUTS.map((shortcut, index) => (
            <div key={index} className="shortcut-row">
              <span className="shortcut-keys">
                {shortcut.keys.map((key, i) => (
                  <span key={i} className="shortcut-key">{key}</span>
                ))}
              </span>
              <span className="shortcut-desc">{shortcut.description}</span>
            </div>
          ))}
        </div>
        <div className="shortcut-modal-footer">
          <button className="btn btn-primary" onClick={() => setOpen(false)}>
            知道了
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}
