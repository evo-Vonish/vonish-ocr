#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Command, Stdio};
use std::io::{BufRead, BufReader};
use std::path::Path;
use tokio::sync::RwLock;
use tauri::{Manager, State, WindowEvent};
use tauri::menu::{MenuBuilder, MenuItemBuilder};
use tauri::tray::TrayIconBuilder;
use tauri_plugin_opener::OpenerExt;

#[cfg(windows)]
use std::os::windows::process::CommandExt;

/// 应用全局状态
struct AppState {
    python_port: RwLock<u16>,
    python_pid: RwLock<Option<u32>>,
    python_child: RwLock<Option<std::process::Child>>,
    client: reqwest::Client,
}

// ------------------------------------------------------------------
// IPC Commands（前端通过 @tauri-apps/api 调用）
// ------------------------------------------------------------------

#[tauri::command]
async fn ocr_recognize(
    state: State<'_, AppState>,
    image_base64: String,
    options: String,
) -> Result<String, String> {
    let port = *state.python_port.read().await;
    let body = serde_json::json!({
        "image": image_base64,
        "options": serde_json::from_str::<serde_json::Value>(&options)
            .unwrap_or(serde_json::Value::Null)
    });
    let res = state
        .client
        .post(format!("http://127.0.0.1:{}/v1/ocr", port))
        .json(&body)
        .send()
        .await
        .map_err(|e| e.to_string())?;
    let text = res.text().await.map_err(|e| e.to_string())?;
    Ok(text)
}

#[tauri::command]
async fn ocr_batch(
    state: State<'_, AppState>,
    images: Vec<String>,
    options: String,
) -> Result<String, String> {
    let port = *state.python_port.read().await;
    let body = serde_json::json!({
        "images": images,
        "options": serde_json::from_str::<serde_json::Value>(&options)
            .unwrap_or(serde_json::Value::Null)
    });
    let res = state
        .client
        .post(format!("http://127.0.0.1:{}/v1/ocr/batch/json", port))
        .json(&body)
        .send()
        .await
        .map_err(|e| e.to_string())?;
    let text = res.text().await.map_err(|e| e.to_string())?;
    Ok(text)
}

#[tauri::command]
async fn get_python_port(state: State<'_, AppState>) -> Result<u16, String> {
    let port = *state.python_port.read().await;
    Ok(port)
}

#[tauri::command]
async fn backend_service_status(state: State<'_, AppState>) -> Result<serde_json::Value, String> {
    // 这个状态来自 Tauri 进程本身；即使 Python sidecar 已停止，也能正常返回。
    let port = *state.python_port.read().await;
    let pid = *state.python_pid.read().await;
    Ok(serde_json::json!({
        "status": if pid.is_some() && port > 0 { "running" } else { "stopped" },
        "port": port,
        "pid": pid,
    }))
}

#[tauri::command]
async fn control_backend_service(
    state: State<'_, AppState>,
    action: String,
) -> Result<serde_json::Value, String> {
    // 服务启停必须在 Tauri 层做，不能走 HTTP；停止后 HTTP 已经不可用了。
    match action.as_str() {
        "stop" => {
            if let Some(pid) = *state.python_pid.read().await {
                kill_python_process(pid);
            }
            let _ = state.python_child.write().await.take();
            *state.python_pid.write().await = None;
            *state.python_port.write().await = 0;
            Ok(serde_json::json!({ "status": "stopped", "port": 0, "pid": null }))
        }
        "start" | "restart" => {
            if let Some(pid) = *state.python_pid.read().await {
                kill_python_process(pid);
            }
            let _ = state.python_child.write().await.take();
            *state.python_pid.write().await = None;
            *state.python_port.write().await = 0;

            let (port, pid, child) = start_python_sidecar().await?;
            *state.python_port.write().await = port;
            *state.python_pid.write().await = Some(pid);
            *state.python_child.write().await = Some(child);
            Ok(serde_json::json!({ "status": "running", "port": port, "pid": pid }))
        }
        other => Err(format!("未知后端服务动作: {}", other)),
    }
}

#[tauri::command]
async fn get_batch_results(
    state: State<'_, AppState>,
    task_id: String,
) -> Result<String, String> {
    let port = *state.python_port.read().await;
    let res = state
        .client
        .get(format!("http://127.0.0.1:{}/v1/ocr/batch/{}/results", port, task_id))
        .send()
        .await
        .map_err(|e| e.to_string())?;
    let text = res.text().await.map_err(|e| e.to_string())?;
    Ok(text)
}

#[tauri::command]
async fn get_batch_status(
    state: State<'_, AppState>,
    task_id: String,
) -> Result<String, String> {
    let port = *state.python_port.read().await;
    let res = state
        .client
        .get(format!("http://127.0.0.1:{}/v1/ocr/batch/{}", port, task_id))
        .send()
        .await
        .map_err(|e| e.to_string())?;
    let text = res.text().await.map_err(|e| e.to_string())?;
    Ok(text)
}

#[tauri::command]
async fn get_available_models(state: State<'_, AppState>) -> Result<String, String> {
    let port = *state.python_port.read().await;
    let res = state
        .client
        .get(format!("http://127.0.0.1:{}/v1/models", port))
        .send()
        .await
        .map_err(|e| e.to_string())?;
    let text = res.text().await.map_err(|e| e.to_string())?;
    Ok(text)
}

#[tauri::command]
async fn pull_model(
    state: State<'_, AppState>,
    model_id: String,
) -> Result<String, String> {
    let port = *state.python_port.read().await;
    let res = state
        .client
        .post(format!("http://127.0.0.1:{}/v1/models/{}/pull", port, model_id))
        .send()
        .await
        .map_err(|e| e.to_string())?;
    let text = res.text().await.map_err(|e| e.to_string())?;
    Ok(text)
}

#[tauri::command]
async fn get_config(state: State<'_, AppState>) -> Result<String, String> {
    let port = *state.python_port.read().await;
    let res = state
        .client
        .get(format!("http://127.0.0.1:{}/v1/config", port))
        .send()
        .await
        .map_err(|e| e.to_string())?;
    let text = res.text().await.map_err(|e| e.to_string())?;
    Ok(text)
}

#[tauri::command]
async fn save_config(
    state: State<'_, AppState>,
    config: String,
) -> Result<String, String> {
    let port = *state.python_port.read().await;
    let body: serde_json::Value =
        serde_json::from_str(&config).map_err(|e| e.to_string())?;
    let res = state
        .client
        .post(format!("http://127.0.0.1:{}/v1/config", port))
        .json(&body)
        .send()
        .await
        .map_err(|e| e.to_string())?;
    let text = res.text().await.map_err(|e| e.to_string())?;
    Ok(text)
}

#[tauri::command]
async fn open_model_dir(app_handle: tauri::AppHandle) -> Result<(), String> {
    let model_dir = std::env::current_dir()
        .unwrap_or_default()
        .join("models");
    app_handle
        .opener()
        .open_path(model_dir.to_string_lossy().as_ref(), None::<&str>)
        .map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
async fn open_backend_console(app_handle: tauri::AppHandle) -> Result<(), String> {
    let logs_dir = std::env::current_dir()
        .unwrap_or_default()
        .join("logs");
    app_handle
        .opener()
        .open_path(logs_dir.to_string_lossy().as_ref(), None::<&str>)
        .map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
async fn open_docs(app_handle: tauri::AppHandle) -> Result<(), String> {
    let readme = std::env::current_dir()
        .unwrap_or_default()
        .join("README.md");
    app_handle
        .opener()
        .open_path(readme.to_string_lossy().as_ref(), None::<&str>)
        .map_err(|e| e.to_string())?;
    Ok(())
}

// ------------------------------------------------------------------
// Python Sidecar 管理
// ------------------------------------------------------------------

async fn find_available_port() -> Result<u16, std::io::Error> {
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await?;
    let addr = listener.local_addr()?;
    Ok(addr.port())
}

async fn start_python_sidecar() -> Result<(u16, u32, std::process::Child), String> {
    // 找一个可用端口
    let port = find_available_port()
        .await
        .map_err(|e| format!("无法绑定端口: {}", e))?;

    // 开发模式 / 生产模式
    let is_dev = cfg!(debug_assertions);

    let (program, args): (String, Vec<String>) = if is_dev {
        let manifest_dir = match std::env::var("CARGO_MANIFEST_DIR") {
            Ok(value) => value,
            Err(_) => std::env::current_dir()
                .map_err(|e| e.to_string())?
                .join("src-tauri")
                .to_string_lossy()
                .to_string(),
        };
        let project_root = Path::new(&manifest_dir)
            .parent()
            .ok_or("无法定位项目根目录")?;
        let mut script = project_root.join("backend").join("main.py");
        if !script.exists() {
            if let Some(root) = std::env::current_exe()
                .ok()
                .and_then(|exe| exe.parent().and_then(|p| p.parent()).and_then(|p| p.parent()).and_then(|p| p.parent()).map(|p| p.to_path_buf()))
            {
                script = root.join("backend").join("main.py");
            }
        }
        (
            "python".to_string(),
            vec![script.to_string_lossy().to_string(), "--sidecar".to_string()],
        )
    } else {
        let exe = std::env::current_exe()
            .map_err(|e| e.to_string())?
            .parent()
            .ok_or("无法获取 exe 目录")?
            .join("backend_dist")
            .join("vonish_ocr_backend")
            .join("vonish_ocr_backend.exe");
        (exe.to_string_lossy().to_string(), vec!["--sidecar".to_string()])
    };

    let mut cmd = Command::new(&program);
    cmd.args(&args)
        .env("VONISH_PORT", port.to_string())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

    #[cfg(windows)]
    {
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }

    let mut child = cmd
        .spawn()
        .map_err(|e| format!("启动 Python 失败: {}", e))?;
    let pid = child.id();
    if pid == 0 {
        return Err("无法获取 PID".to_string());
    }

    // 读取 stdout 等待就绪信号
    let stdout = child.stdout.take().ok_or("无法捕获 stdout")?;
    let reader = BufReader::new(stdout);

    for line in reader.lines() {
        let line = line.map_err(|e| e.to_string())?;
        if let Ok(msg) = serde_json::from_str::<serde_json::Value>(&line) {
            if msg.get("status").and_then(|s| s.as_str()) == Some("ready") {
                let actual_port = msg
                    .get("port")
                    .and_then(|p| p.as_u64())
                    .unwrap_or(port as u64) as u16;
                return Ok((actual_port, pid, child));
            }
        }
    }

    Err("Python sidecar 未输出就绪信号".to_string())
}

fn kill_python_process(pid: u32) {
    #[cfg(windows)]
    {
        let _ = Command::new("taskkill")
            .args(&["/PID", &pid.to_string(), "/T", "/F"])
            .creation_flags(0x08000000)
            .spawn();
    }
    #[cfg(not(windows))]
    {
        let _ = Command::new("kill")
            .args(&["-TERM", &pid.to_string()])
            .spawn();
    }
}

// ------------------------------------------------------------------
// Main
// ------------------------------------------------------------------

fn main() {
    let builder = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_notification::init())
        .manage(AppState {
            python_port: RwLock::new(0),
            python_pid: RwLock::new(None),
            python_child: RwLock::new(None),
            client: reqwest::Client::new(),
        })
        .setup(|app| {
            let state: State<'_, AppState> = app.state();

            // 启动 Python sidecar
            tauri::async_runtime::block_on(async move {
                match start_python_sidecar().await {
                    Ok((port, pid, child)) => {
                        *state.python_port.write().await = port;
                        *state.python_pid.write().await = Some(pid);
                        *state.python_child.write().await = Some(child);
                        println!("Python sidecar ready on port {} (PID: {})", port, pid);
                    }
                    Err(e) => {
                        eprintln!("Failed to start Python sidecar: {}", e);
                    }
                }
            });

            // 服务化后主窗口默认定位到控制台入口。当前前端仍是单页状态机，
            // hash 先作为外部入口标记保留，App.vue 会默认展示 BackendConsole。
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.eval("window.location.hash = '#/console';");
            }

            // 创建系统托盘图标和菜单
            let show_i = MenuItemBuilder::new("显示主窗口")
                .id("show")
                .build(app)?;

            let logs_i = MenuItemBuilder::new("打开后端日志")
                .id("logs")
                .build(app)?;
            let models_i = MenuItemBuilder::new("打开模型目录")
                .id("models")
                .build(app)?;
            let docs_i = MenuItemBuilder::new("打开项目文档")
                .id("docs")
                .build(app)?;
            let quit_i = MenuItemBuilder::new("退出 VonishOCR")
                .id("quit")
                .build(app)?;
            let menu = MenuBuilder::new(app)
                .items(&[&show_i, &logs_i, &models_i, &docs_i, &quit_i])
                .build()?;

            // 安全设置托盘图标（开发模式下 default_window_icon 可能为 None）
            let icon = app.default_window_icon().cloned();
            let mut tray_builder = TrayIconBuilder::new()
                .menu(&menu)
                .tooltip("VonishOCR")
                .on_menu_event(|app, event| {
                    match event.id().as_ref() {
                        "show" => {
                            if let Some(window) = app.get_webview_window("main") {
                                let _ = window.show();
                                let _ = window.set_focus();
                            }
                        }

                        "logs" => {
                            let path = std::env::current_dir().unwrap_or_default().join("logs");
                            if let Err(e) = app.opener().open_path(path.to_string_lossy().as_ref(), None::<&str>) {
                                eprintln!("打开日志目录失败: {} (path: {:?})", e, path);
                            }
                        }
                        "models" => {
                            let path = std::env::current_dir().unwrap_or_default().join("models");
                            if !path.exists() {
                                let _ = std::fs::create_dir_all(&path);
                            }
                            if let Err(e) = app.opener().open_path(path.to_string_lossy().as_ref(), None::<&str>) {
                                eprintln!("打开模型目录失败: {} (path: {:?})", e, path);
                            }
                        }
                        "docs" => {
                            let path = std::env::current_dir().unwrap_or_default().join("README.md");
                            if !path.exists() {
                                eprintln!("README.md 不存在: {:?}", path);
                            } else if let Err(e) = app.opener().open_path(path.to_string_lossy().as_ref(), None::<&str>) {
                                eprintln!("打开 README.md 失败: {} (path: {:?})", e, path);
                            }
                        }
                        "quit" => {
                            let state: State<'_, AppState> = app.state();
                            tauri::async_runtime::block_on(async {
                                if let Some(pid) = *state.python_pid.read().await {
                                    kill_python_process(pid);
                                }
                            });
                            app.exit(0);
                        }
                        _ => {}
                    }
                })
                .on_tray_icon_event(|tray, event| {
                    if let tauri::tray::TrayIconEvent::Click { button, .. } = event {
                        // 仅左键单击显示窗口；右键单击交给默认菜单行为
                        if button == tauri::tray::MouseButton::Left {
                            let app = tray.app_handle();
                            if let Some(window) = app.get_webview_window("main") {
                                let _ = window.show();
                                let _ = window.set_focus();
                            }
                        }
                    }
                });
            if let Some(icon) = icon {
                tray_builder = tray_builder.icon(icon);
            }
            let _tray = tray_builder.build(app)?;

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            ocr_recognize,
            ocr_batch,
            get_batch_status,
            get_batch_results,
            get_available_models,
            pull_model,
            get_config,
            save_config,
            open_model_dir,
            open_backend_console,
            open_docs,
            get_python_port,
            backend_service_status,
            control_backend_service,
        ])
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                // 点击关闭按钮时隐藏窗口，而非退出
                let _ = window.hide();
                api.prevent_close();
            }
        });

    let app = builder
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    app.run(|_app_handle, event| {
        // 其他 RunEvent 处理（如系统托盘点击等已由 TrayIconBuilder 处理）
        // ExitRequested 在托盘"退出"时允许正常退出，不做阻止
        match event {
            tauri::RunEvent::Exit => {
                // 最终退出时确保 Python 进程已被清理
                let state: State<'_, AppState> = _app_handle.state();
                tauri::async_runtime::block_on(async {
                    if let Some(pid) = *state.python_pid.read().await {
                        kill_python_process(pid);
                    }
                    // 释放 Child 句柄，避免管道提前关闭导致 Python BrokenPipe
                    let _ = state.python_child.write().await.take();
                });
            }
            _ => {}
        }
    });
}
