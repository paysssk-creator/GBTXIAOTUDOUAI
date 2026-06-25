use anyhow::{Context, Result};
use directories::ProjectDirs;
use serde::Serialize;
use std::net::TcpStream;
use std::sync::atomic::{AtomicU8, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tauri::async_runtime::JoinHandle;
use tauri::{AppHandle, Emitter, Manager, RunEvent, State, WebviewWindow};
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::{Child, Command};
use tokio::sync::Mutex as TokioMutex;
use tokio::time::{interval, sleep};

const HEALTH_URL: &str = "http://127.0.0.1:8765/api/health";
const BACKEND_PORT: u16 = 8765;
const MAX_LOG_LINES: usize = 200;
const HEALTH_MAX_FAILS: u32 = 40;

#[derive(Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
enum BackendStatus {
    Idle = 0,
    Starting = 1,
    Healthy = 2,
    Failed = 3,
}

#[derive(Serialize, Clone)]
struct BackendInfo {
    port: u16,
    data_dir: String,
    status: String,
}

#[derive(Serialize, Clone)]
struct BackendStatusResp {
    status: String,
    logs: Vec<String>,
}

#[derive(Serialize, Clone)]
struct BackendStatusEvent {
    status: String,
    error: Option<String>,
}

/// Shared state that can be cheaply cloned into background tasks.
struct SharedState {
    status: AtomicU8,
    logs: Mutex<Vec<String>>,
}

impl SharedState {
    fn new() -> Self {
        Self {
            status: AtomicU8::new(BackendStatus::Idle as u8),
            logs: Mutex::new(Vec::new()),
        }
    }

    fn push_log(&self, line: String) {
        let mut logs = self.logs.lock().unwrap();
        logs.push(line);
        let len = logs.len();
        if len > MAX_LOG_LINES {
            logs.drain(0..len - MAX_LOG_LINES);
        }
    }

    fn get_logs(&self) -> Vec<String> {
        self.logs.lock().unwrap().clone()
    }

    fn set_status(&self, status: BackendStatus) {
        self.status.store(status as u8, Ordering::SeqCst);
    }

    fn get_status(&self) -> BackendStatus {
        match self.status.load(Ordering::SeqCst) {
            1 => BackendStatus::Starting,
            2 => BackendStatus::Healthy,
            3 => BackendStatus::Failed,
            _ => BackendStatus::Idle,
        }
    }
}

struct BackendHandle {
    shared: Arc<SharedState>,
    child: Arc<TokioMutex<Option<Child>>>,
    health_task: TokioMutex<Option<JoinHandle<()>>>,
    exit_watcher: TokioMutex<Option<JoinHandle<()>>>,
}

impl Default for BackendHandle {
    fn default() -> Self {
        Self {
            shared: Arc::new(SharedState::new()),
            child: Arc::new(TokioMutex::new(None)),
            health_task: TokioMutex::new(None),
            exit_watcher: TokioMutex::new(None),
        }
    }
}

impl BackendHandle {
    fn get_logs(&self) -> Vec<String> {
        self.shared.get_logs()
    }

    fn set_status(&self, status: BackendStatus) {
        self.shared.set_status(status);
    }

    fn get_status(&self) -> BackendStatus {
        self.shared.get_status()
    }
}

fn data_dir() -> Result<std::path::PathBuf> {
    ProjectDirs::from("com", "gbtxiaotudou", "GBT")
        .map(|d| d.data_dir().to_path_buf())
        .context("failed to resolve project data directory")
}

fn port_in_use(port: u16) -> bool {
    TcpStream::connect_timeout(
        &std::net::SocketAddr::from(([127, 0, 0, 1], port)),
        Duration::from_millis(300),
    )
    .is_ok()
}

fn sidecar_path(app: &AppHandle) -> Result<std::path::PathBuf> {
    let current = tauri::process::current_binary(&app.env())?;
    let parent = current
        .parent()
        .context("failed to resolve current binary directory")?;
    let name = if cfg!(windows) {
        "gbt-sidecar.exe"
    } else {
        "gbt-sidecar"
    };
    Ok(parent.join(name))
}

fn emit_log(app: &AppHandle, line: String) {
    let _ = app.emit("backend-log", line.clone());
}

fn emit_status(app: &AppHandle, status: BackendStatus, error: Option<String>) {
    let payload = BackendStatusEvent {
        status: match status {
            BackendStatus::Idle => "idle",
            BackendStatus::Starting => "starting",
            BackendStatus::Healthy => "healthy",
            BackendStatus::Failed => "failed",
        }
        .to_string(),
        error,
    };
    let _ = app.emit("backend-status", payload);
}

#[tauri::command]
async fn start_backend(app: AppHandle, state: State<'_, BackendHandle>) -> Result<BackendInfo, String> {
    if port_in_use(BACKEND_PORT) {
        return Err(format!("端口 {} 已被占用，请先关闭其他 GBT 实例", BACKEND_PORT));
    }

    let mut child_lock = state.child.lock().await;
    if child_lock.is_some() {
        return Err("后端已经启动".to_string());
    }

    state.set_status(BackendStatus::Starting);
    emit_status(&app, BackendStatus::Starting, None);

    let data_dir = data_dir().map_err(|e| e.to_string())?;
    std::fs::create_dir_all(&data_dir).map_err(|e| format!("无法创建数据目录: {}", e))?;

    let sidecar = sidecar_path(&app).map_err(|e| format!("无法定位 sidecar: {}", e))?;
    if !sidecar.exists() {
        return Err(format!("sidecar 二进制不存在: {}", sidecar.display()));
    }

    let mut cmd = Command::new(sidecar);
    cmd.env("GBT_TAURI", "1")
        .env("GBT_HOME", &data_dir)
        .env("PYTHONUTF8", "1")
        .env("PYTHONIOENCODING", "utf-8")
        .env("GBT_PORT", BACKEND_PORT.to_string())
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped());

    #[cfg(windows)]
    cmd.creation_flags(0x08000000); // CREATE_NO_WINDOW

    let mut child = cmd
        .kill_on_drop(true)
        .spawn()
        .map_err(|e| format!("启动 sidecar 失败: {}", e))?;

    let app_clone = app.clone();
    let shared = state.shared.clone();

    // Stream stdout logs.
    if let Some(stdout) = child.stdout.take() {
        let shared = shared.clone();
        let app = app_clone.clone();
        tokio::spawn(async move {
            let reader = BufReader::new(stdout);
            let mut lines = reader.lines();
            while let Ok(Some(line)) = lines.next_line().await {
                shared.push_log(line.clone());
                emit_log(&app, line);
            }
        });
    }

    // Stream stderr logs.
    if let Some(stderr) = child.stderr.take() {
        let shared = shared.clone();
        let app = app_clone.clone();
        tokio::spawn(async move {
            let reader = BufReader::new(stderr);
            let mut lines = reader.lines();
            while let Ok(Some(line)) = lines.next_line().await {
                shared.push_log(line.clone());
                emit_log(&app, line);
            }
        });
    }

    // Watch for unexpected child exit.
    let exit_shared = state.shared.clone();
    let exit_app = app_clone.clone();
    let child_for_exit = Arc::clone(&state.child);
    let exit_handle = tauri::async_runtime::spawn(async move {
        let mut ticker = interval(Duration::from_millis(500));
        loop {
            ticker.tick().await;
            let mut lock = child_for_exit.lock().await;
            match lock.as_mut() {
                Some(child) => match child.try_wait() {
                    Ok(Some(status)) => {
                        // Child exited. If we never reached Healthy, mark as failed.
                        if matches!(
                            exit_shared.get_status(),
                            BackendStatus::Starting | BackendStatus::Idle
                        ) {
                            let code = status.code().unwrap_or(-1);
                            let msg = format!("后端进程意外退出 (exit code: {})", code);
                            exit_shared.push_log(msg.clone());
                            emit_log(&exit_app, msg);
                            exit_shared.set_status(BackendStatus::Failed);
                            emit_status(&exit_app, BackendStatus::Failed, Some(format!("后端进程意外退出 (exit code: {})", code)));
                        }
                        *lock = None;
                        break;
                    }
                    Ok(None) => {
                        // Still running.
                    }
                    Err(e) => {
                        exit_shared.push_log(format!("[Error] sidecar try_wait error: {}", e));
                    }
                },
                None => break,
            }
        }
    });

    *child_lock = Some(child);
    drop(child_lock);

    let health_handle = tauri::async_runtime::spawn(poll_health(
        app_clone.clone(),
        state.shared.clone(),
    ));
    *state.health_task.lock().await = Some(health_handle);
    *state.exit_watcher.lock().await = Some(exit_handle);

    Ok(BackendInfo {
        port: BACKEND_PORT,
        data_dir: data_dir.to_string_lossy().to_string(),
        status: "starting".to_string(),
    })
}

async fn poll_health(app: AppHandle, shared: Arc<SharedState>) {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(2))
        .build()
        .unwrap();

    let mut failures = 0;
    let mut ticker = interval(Duration::from_millis(800));

    loop {
        ticker.tick().await;

        match client.get(HEALTH_URL).send().await {
            Ok(resp) if resp.status().is_success() => {
                shared.set_status(BackendStatus::Healthy);
                emit_status(&app, BackendStatus::Healthy, None);
                shared.push_log("[Health] backend ready".to_string());
                emit_log(&app, "[Health] backend ready".to_string());
                return;
            }
            _ => failures += 1,
        }

        if failures >= HEALTH_MAX_FAILS {
            shared.set_status(BackendStatus::Failed);
            emit_status(&app, BackendStatus::Failed, Some("后端健康检查超时".to_string()));
            let msg = "后端健康检查超时".to_string();
            shared.push_log(msg.clone());
            emit_log(&app, msg);
            return;
        }

        let msg = format!("等待后端就绪 ({}/{})...", failures, HEALTH_MAX_FAILS);
        shared.push_log(msg.clone());
        emit_log(&app, msg);
    }
}

async fn stop_backend_inner(state: &BackendHandle) -> Result<(), String> {
    if let Some(handle) = state.health_task.lock().await.take() {
        handle.abort();
    }
    if let Some(handle) = state.exit_watcher.lock().await.take() {
        handle.abort();
    }

    let mut child_lock = state.child.lock().await;
    if let Some(mut child) = child_lock.take() {
        let _ = child.start_kill();
        #[cfg(windows)]
        {
            // PyInstaller onefile spawns a child Python interpreter; killing the
            // bootloader leaves the worker alive. Ensure the entire sidecar tree
            // is terminated.
            let _ = std::process::Command::new("taskkill")
                .args(["/F", "/T", "/IM", "gbt-sidecar.exe"])
                .stdout(std::process::Stdio::null())
                .stderr(std::process::Stdio::null())
                .status();
        }
        let _ = child.wait().await;
    }

    state.set_status(BackendStatus::Idle);
    Ok(())
}

#[tauri::command]
async fn stop_backend(state: State<'_, BackendHandle>) -> Result<(), String> {
    stop_backend_inner(&state).await
}

#[tauri::command]
async fn restart_backend(app: AppHandle, state: State<'_, BackendHandle>) -> Result<BackendInfo, String> {
    stop_backend_inner(&state).await?;
    sleep(Duration::from_millis(500)).await;
    start_backend(app, state).await
}

#[tauri::command]
async fn backend_status(state: State<'_, BackendHandle>) -> Result<BackendStatusResp, String> {
    let status = match state.get_status() {
        BackendStatus::Idle => "idle",
        BackendStatus::Starting => "starting",
        BackendStatus::Healthy => "healthy",
        BackendStatus::Failed => "failed",
    };
    Ok(BackendStatusResp {
        status: status.to_string(),
        logs: state.get_logs(),
    })
}

#[tauri::command]
fn open_data_dir() -> Result<(), String> {
    let dir = data_dir().map_err(|e| e.to_string())?;
    std::fs::create_dir_all(&dir).map_err(|e| format!("无法创建数据目录: {}", e))?;
    opener::open(dir).map_err(|e| format!("无法打开数据目录: {}", e))?;
    Ok(())
}

#[tauri::command]
fn log_frontend_error(message: String, stack: Option<String>) {
    eprintln!("[frontend-error] {}", message);
    if let Some(s) = stack {
        eprintln!("[frontend-error-stack] {}", s);
    }
}

#[tauri::command]
async fn open_devtools(window: WebviewWindow) -> Result<(), String> {
    #[cfg(debug_assertions)]
    {
        window.open_devtools();
        Ok(())
    }
    #[cfg(not(debug_assertions))]
    {
        let _ = window;
        Err("开发者工具仅在开发模式下可用".to_string())
    }
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, argv, _cwd| {
            let _ = app.emit("single-instance", argv);
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.set_focus();
            }
        }))
        .plugin(tauri_plugin_deep_link::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .manage(BackendHandle::default())
        .invoke_handler(tauri::generate_handler![
            start_backend,
            stop_backend,
            restart_backend,
            backend_status,
            open_data_dir,
            log_frontend_error,
            open_devtools
        ])
        .setup(|_app| {
            #[cfg(any(windows, target_os = "linux"))]
            {
                use tauri_plugin_deep_link::DeepLinkExt;
                let _ = _app.deep_link().register("gbt");
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|_app_handle, event| match event {
            RunEvent::ExitRequested { .. } => {
                let state = _app_handle.state::<BackendHandle>();
                tauri::async_runtime::block_on(async move {
                    let _ = stop_backend_inner(&state).await;
                });
            }
            _ => {}
        });
}
