#!/usr/bin/env node
/**
 * Download GitHub Release assets and verify SHA-256 + minisign signatures.
 *
 * Usage:
 *   node scripts/verify-release.mjs [version]
 *
 * Defaults to the version declared in app/package.json.
 */
import { mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const APP_DIR = join(ROOT, "app");

const VERSION = process.argv[2] || JSON.parse(await readFile(join(APP_DIR, "package.json"), "utf8")).version;
const TAG = VERSION.startsWith("v") ? VERSION : `v${VERSION}`;
const REPO = "paysssk-creator/GBTXIAOTUDOUAI";

const ASSETS = [
  `gbt-app_${VERSION}_x64-setup.exe`,
  `gbt-app_${VERSION}_x64-setup.exe.sig`,
  `gbt-app_${VERSION}_x64_en-US.msi`,
  `gbt-app_${VERSION}_x64_en-US.msi.sig`,
  "checksums.txt",
  "latest.json",
];

const WORK_DIR = join(ROOT, ".tmp-verify-release");

async function exec(cmd, args, opts = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, { stdio: "inherit", ...opts });
    child.on("close", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`${cmd} ${args.join(" ")} exited with ${code}`));
    });
  });
}

async function sha256(path) {
  const hash = createHash("sha256");
  hash.update(await readFile(path));
  return hash.digest("hex");
}

async function base64DecodeFile(inputPath, outputPath) {
  const b64 = await readFile(inputPath, "utf8");
  await writeFile(outputPath, Buffer.from(b64.trim(), "base64"));
}

async function getPublicKey() {
  const conf = JSON.parse(await readFile(join(APP_DIR, "src-tauri", "tauri.conf.json"), "utf8"));
  const pubB64 = conf.plugins.updater.pubkey;
  const pubFile = Buffer.from(pubB64, "base64").toString("utf8");
  return pubFile.trim().split("\n")[1];
}

async function main() {
  console.log(`Verifying release ${TAG} from ${REPO}`);

  await rm(WORK_DIR, { recursive: true, force: true });
  await mkdir(WORK_DIR, { recursive: true });

  console.log("\nDownloading assets...");
  await exec("gh", [
    "release", "download", TAG,
    "--repo", REPO,
    ...ASSETS.flatMap((a) => ["--pattern", a]),
    "-D", WORK_DIR,
  ]);

  console.log("\nVerifying checksums...");
  const checksums = new Map(
    (await readFile(join(WORK_DIR, "checksums.txt"), "utf8"))
      .trim()
      .split("\n")
      .filter(Boolean)
      .map((line) => {
        const [hash, ...nameParts] = line.trim().split(/\s+/);
        return [nameParts.join(" "), hash];
      })
  );

  for (const [name, expected] of checksums) {
    const actual = await sha256(join(WORK_DIR, name));
    if (actual !== expected) {
      throw new Error(`Checksum mismatch for ${name}: expected ${expected}, got ${actual}`);
    }
    console.log(`  ${name}: OK`);
  }

  console.log("\nVerifying latest.json signature...");
  const latest = JSON.parse(await readFile(join(WORK_DIR, "latest.json"), "utf8"));
  const setupSig = await readFile(join(WORK_DIR, `gbt-app_${VERSION}_x64-setup.exe.sig`), "utf8");
  if (latest.platforms["windows-x86_64"].signature !== setupSig) {
    throw new Error("latest.json windows-x86_64 signature does not match setup.exe.sig");
  }
  console.log("  latest.json signature: OK");

  console.log("\nBuilding minisign verifier...");
  await exec("cargo", ["build", "--release", "--manifest-path", join(ROOT, "scripts", "minisign-verify", "Cargo.toml")]);

  const pubKey = await getPublicKey();
  const verifier = join(ROOT, "scripts", "minisign-verify", "target", "release", process.platform === "win32" ? "minisign-verify-cli.exe" : "minisign-verify-cli");

  console.log("\nVerifying minisign signatures...");
  for (const name of ["gbt-app_1.5.3_x64-setup.exe", "gbt-app_1.5.3_x64_en-US.msi"]) {
    const rawSig = join(WORK_DIR, `${name}.sig.raw`);
    await base64DecodeFile(join(WORK_DIR, `${name}.sig`), rawSig);
    await exec(verifier, [pubKey, rawSig, join(WORK_DIR, name)]);
    console.log(`  ${name}: OK`);
  }

  console.log("\nAll verification checks passed.");
}

main().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
