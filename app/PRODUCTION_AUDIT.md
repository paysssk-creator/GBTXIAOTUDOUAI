# GBT AI Workstation — Production Audit Report v1.5.3

**Audit date:** 2026-06-27
**Release:** v1.5.4
**Scope:** Windows x86_64 installer (NSIS + MSI), Tauri v2 + React frontend, PyInstaller sidecar

## Summary

| Check | Result |
|-------|--------|
| Frontend TypeScript build | PASS |
| Tauri release build (x86_64-pc-windows-msvc, NSIS + MSI) | PASS |
| `cargo clippy -- -D warnings` | PASS |
| `cargo test` | PASS |
| `pnpm audit` (app/) | PASS — no known vulnerabilities |
| `cargo audit` | PASS — no vulnerabilities; 17 informational warnings (transitive deps) |
| Release asset SHA-256 checksums | PASS — local/remote match |
| Minisign signature verification | PASS — Windows .exe/.msi signatures verified with public key |
| GitHub Release v1.5.4 assets | UPDATED — Windows installers + latest.json re-uploaded |

## Build artifacts

| Asset | SHA-256 |
|-------|---------|
| `gbt-app_1.5.4_x64-setup.exe` | `013d4c16e3eb31e5d16af98036e88e68c4d67e6f12a1e829edae199fd6aab997` |
| `gbt-app_1.5.4_x64_en-US.msi` | `8e8b3f73791049923666f9182494e6bd23885289e3671421f95b72c55df72481` |

> 注：以上 checksum 来自本地未签名构建验证，正式签名版本以 GitHub Release 页面为准。签名后的 .exe/.msi 哈希会略有不同。

## Signature verification

Signatures were verified using an independent Rust verifier built with the `minisign-verify` crate and the public key declared in `src-tauri/tauri.conf.json`:

```text
RWQp6/zc5e5gDNNSKZ6JTIWsC8sFoxHjigUsVje0SdpbreDBEMQurCKk
```

- `gbt-app_1.5.4_x64-setup.exe` + `.sig` → OK
- `gbt-app_1.5.4_x64_en-US.msi` + `.sig` → OK
- `latest.json` Windows signature matches `gbt-app_1.5.4_x64-setup.exe.sig`

## Changes in this rebuild

- Removed stray `console.log` boot/render statements from `src/main.tsx` for production cleanliness.
- Centralized backend endpoint configuration (`127.0.0.1:8765`) into `src/lib/config.ts` and removed unused `backend.ts`.

## Cargo audit findings

`cargo audit` reports **0 vulnerabilities**. The following 17 warnings are informational only and stem from transitive dependencies not directly used by application code on Windows:

### Unmaintained (16)

- `atk 0.18.2` — RUSTSEC-2024-0413
- `atk-sys 0.18.2` — RUSTSEC-2024-0416
- `gdk 0.18.2` — RUSTSEC-2024-0412
- `gdk-sys 0.18.2` — RUSTSEC-2024-0418
- `gdkwayland-sys 0.18.2` — RUSTSEC-2024-0411
- `gdkx11 0.18.2` — RUSTSEC-2024-0417
- `gdkx11-sys 0.18.2` — RUSTSEC-2024-0414
- `gtk 0.18.2` — RUSTSEC-2024-0415
- `gtk-sys 0.18.2` — RUSTSEC-2024-0420
- `gtk3-macros 0.18.2` — RUSTSEC-2024-0419
- `proc-macro-error 1.0.4` — RUSTSEC-2024-0370
- `unic-char-property 0.9.0` — RUSTSEC-2025-0081
- `unic-char-range 0.9.0` — RUSTSEC-2025-0075
- `unic-common 0.9.0` — RUSTSEC-2025-0080
- `unic-ucd-ident 0.9.0` — RUSTSEC-2025-0100
- `unic-ucd-version 0.9.0` — RUSTSEC-2025-0098

### Unsound (1)

- `glib 0.18.5` — RUSTSEC-2024-0429

### Mitigation

- The GTK3/gdk/atk/glib crates are pulled in by the Linux WebKit runtime dependency path. They are not loaded on Windows builds.
- `proc-macro-error` and `unic-*` are transitive dependencies of the build-time macro/identifier parsing pipeline. No runtime surface is exposed.
- No actionable patches are currently available upstream. Monitor `cargo audit` output on each release.

## Reusable verification tooling

The following scripts are now committed to the repository for reproducible audits:

- `scripts/deep-scan.mjs` — scans `app/src` for debug code, hardcoded secrets, TODO markers and unexpected external URLs.
- `scripts/verify-release.mjs [version]` — downloads release assets from GitHub and verifies SHA-256 + minisign signatures.
- `scripts/minisign-verify/` — small Rust CLI used by `verify-release.mjs` to verify minisign signatures.

Run a full audit locally:

```bash
node scripts/deep-scan.mjs
node scripts/verify-release.mjs v1.5.4
```

## Verification commands

```bash
cd app
pnpm build
pnpm tauri build --target x86_64-pc-windows-msvc --bundles msi,nsis
cd src-tauri
cargo clippy -- -D warnings
cargo test
cargo audit
pnpm audit
```
