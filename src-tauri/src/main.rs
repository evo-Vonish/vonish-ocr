#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Command, Stdio};
use std::io::{BufRead, BufReader};
use std::path::Path;
use tokio::sync::RwLock;
use tauri::{Manager, State, WindowEvent};
use tauri_plugin_opener::OpenerExt;

#[cfg(windows)]
use std::os::windows::process::CommandExt;

/// 应用全局状态
struct AppState {
    python_port: RwLock<u16>,
    python_pid: RwLock<Option<u32>>,
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
        .post(format!("http://127.0.0.1:{}/v1/ocr/batch", port))
        .json(&body)
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

// ------------------------------------------------------------------
// Python Sidecar 管理
// ------------------------------------------------------------------

async fn find_available_port() -> Result<u16, std::io::Error> {
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await?;
    let addr = listener.local_addr()?;
    Ok(addr.port())
}

async fn start_python_sidecar() -> Result<(u16, u32), String> {
    // 找一个可用端口
    let port = find_available_port()
        .await
        .map_err(|e| format!("无法绑定端口: {}", e))?;

    // 开发模式 / 生产模式
    let is_dev = cfg!(debug_assertions);

    let (program, args): (String, Vec<String>) = if is_dev {
        let manifest_dir = std::env::var("CARGO_MANIFEST_DIR")
            .map_err(|e| e.to_string())?;
        let project_root = Path::new(&manifest_dir)
            .parent()
            .ok_or("无法定位项目根目录")?;
        let script = project_root.join("backend").join("main.py");
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
                return Ok((actual_port, pid));
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
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_opener::init())
        .manage(AppState {
            python_port: RwLock::new(0),
            python_pid: RwLock::new(None),
            client: reqwest::Client::new(),
        })
        .setup(|app| {
            let state: State<'_, AppState> = app.state();

            tauri::async_runtime::block_on(async move {
                match start_python_sidecar().await {
                    Ok((port, pid)) => {
                        *state.python_port.write().await = port;
                        *state.python_pid.write().await = Some(pid);
                        println!("Python sidecar ready on port {} (PID: {})", port, pid);
                    }
                    Err(e) => {
                        eprintln!("Failed to start Python sidecar: {}", e);
                        // 不阻塞启动，允许前端在 sidecar 不可用时提示用户
                    }
                }
            });

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            ocr_recognize,
            ocr_batch,
            get_batch_status,
            get_available_models,
            pull_model,
            get_config,
            save_config,
            open_model_dir,
        ])
        .on_window_event(|_window, event| {
            if let WindowEvent::CloseRequested { .. } = event {
                let state: State<'_, AppState> = _window.state();
                tauri::async_runtime::block_on(async {
                    if let Some(pid) = *state.python_pid.read().await {
                        kill_python_process(pid);
                    }
                });
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
