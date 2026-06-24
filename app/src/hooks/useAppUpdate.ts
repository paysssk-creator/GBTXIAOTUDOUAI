import { useCallback, useEffect, useState } from "react";
import { check, Update, DownloadEvent } from "@tauri-apps/plugin-updater";
import { relaunch } from "@tauri-apps/plugin-process";

export type UpdatePhase =
  | "idle"
  | "checking"
  | "available"
  | "downloading"
  | "ready_to_install"
  | "installing"
  | "restarting"
  | "error";

interface UseAppUpdateOptions {
  autoCheck?: boolean;
  autoDownload?: boolean;
}

export function useAppUpdate(options: UseAppUpdateOptions = {}) {
  const { autoCheck = true, autoDownload = true } = options;
  const [phase, setPhase] = useState<UpdatePhase>("idle");
  const [info, setInfo] = useState<Update | null>(null);
  const [bytesDownloaded, setBytesDownloaded] = useState(0);
  const [totalBytes, setTotalBytes] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reset = useCallback(() => {
    setPhase("idle");
    setInfo(null);
    setBytesDownloaded(0);
    setTotalBytes(null);
    setError(null);
  }, []);

  const download = useCallback(async () => {
    if (!info) return;
    setPhase("downloading");
    setBytesDownloaded(0);
    setTotalBytes(null);
    setError(null);
    try {
      await info.downloadAndInstall((event: DownloadEvent) => {
        switch (event.event) {
          case "Started":
            setTotalBytes(event.data.contentLength ?? null);
            break;
          case "Progress":
            setBytesDownloaded((prev) => prev + event.data.chunkLength);
            break;
          case "Finished":
            setPhase("ready_to_install");
            break;
        }
      });
      setPhase("ready_to_install");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setPhase("error");
    }
  }, [info]);

  const checkForUpdate = useCallback(async () => {
    reset();
    setPhase("checking");
    try {
      const update = await check();
      if (update) {
        setInfo(update);
        setPhase("available");
        if (autoDownload) {
          await update.downloadAndInstall((event: DownloadEvent) => {
            switch (event.event) {
              case "Started":
                setTotalBytes(event.data.contentLength ?? null);
                break;
              case "Progress":
                setBytesDownloaded((prev) => prev + event.data.chunkLength);
                break;
              case "Finished":
                setPhase("ready_to_install");
                break;
            }
          });
          setPhase("ready_to_install");
        }
      } else {
        setPhase("idle");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setPhase("error");
    }
  }, [autoDownload, reset]);

  const install = useCallback(async () => {
    setPhase("installing");
    try {
      await info?.install();
      setPhase("restarting");
      await relaunch();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setPhase("error");
    }
  }, [info]);

  useEffect(() => {
    if (autoCheck) {
      // Delay slightly so the app doesn't thrash on boot.
      const t = setTimeout(checkForUpdate, 3000);
      return () => clearTimeout(t);
    }
  }, [autoCheck, checkForUpdate]);

  return {
    phase,
    info,
    bytesDownloaded,
    totalBytes,
    error,
    checkForUpdate,
    download,
    install,
    reset,
  };
}
