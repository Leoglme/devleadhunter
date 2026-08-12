//! Spawns the local scraping sidecar that ships inside the app.
//!
//! Google blocks datacenter IPs, so browser-driven scraping has to run on the
//! user's own machine with their residential IP. The sidecar is a packaged
//! Python binary; this module starts it on a free loopback port, guards it with
//! a one-shot token, and hands both to the web layer.

use std::net::TcpListener;
use std::sync::Mutex;
use std::time::Duration;

use tauri::{AppHandle, Manager, State};
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

/// Process image name of the bundled scraping sidecar on Windows.
#[cfg(windows)]
const WINDOWS_SIDECAR_IMAGE: &str = "devleadhunter-scraper.exe";

/// Where the web layer should send scraping calls, and how to authenticate them.
#[derive(Clone, serde::Serialize)]
pub struct SidecarInfo {
    pub port: u16,
    pub token: String,
}

/// Running sidecar, kept so it can be killed when the app closes.
#[derive(Default)]
pub struct SidecarState {
    pub info: Mutex<Option<SidecarInfo>>,
    pub child: Mutex<Option<CommandChild>>,
}

/// Ask the OS for a port nobody is using.
///
/// Binding port 0 and reading back the assignment avoids the classic collision
/// of a hardcoded port when a second instance — or another app — already holds it.
fn free_loopback_port() -> Result<u16, String> {
    let listener = TcpListener::bind("127.0.0.1:0").map_err(|e| format!("no free port: {e}"))?;
    listener
        .local_addr()
        .map(|addr| addr.port())
        .map_err(|e| format!("no local addr: {e}"))
}

/// Build a random token so only this app can drive the scraper.
///
/// Loopback alone would leave the sidecar open to any local process, including
/// a web page the user has open in a browser. The bytes come from the OS CSPRNG:
/// a token derived from the clock or the PID would be reconstructible by exactly
/// the local process it is meant to keep out.
fn generate_token() -> Result<String, String> {
    let mut bytes = [0u8; 32];
    getrandom::fill(&mut bytes).map_err(|e| format!("no secure randomness: {e}"))?;
    Ok(bytes.iter().map(|b| format!("{b:02x}")).collect())
}

/// Start the sidecar and remember how to reach it.
pub fn start(app: &AppHandle) -> Result<(), String> {
    let port = free_loopback_port()?;
    let token = generate_token()?;

    let command = app
        .shell()
        .sidecar("devleadhunter-scraper")
        .map_err(|e| format!("sidecar not bundled: {e}"))?
        .args(["--port", &port.to_string()])
        .env("SIDECAR_TOKEN", token.clone())
        .env("SIDECAR_PORT", port.to_string());

    let (_rx, child) = command
        .spawn()
        .map_err(|e| format!("sidecar failed to start: {e}"))?;

    let state = app.state::<SidecarState>();
    *state.info.lock().map_err(|_| "state poisoned")? = Some(SidecarInfo {
        port,
        token: token.clone(),
    });
    *state.child.lock().map_err(|_| "state poisoned")? = Some(child);

    log::info!("scraping sidecar started on 127.0.0.1:{port}");
    Ok(())
}

/// Stop the managed sidecar child process when present.
fn kill_managed_child(app: &AppHandle) {
    if let Some(state) = app.try_state::<SidecarState>() {
        if let Ok(mut guard) = state.child.lock() {
            if let Some(child) = guard.take() {
                let _ = child.kill();
            }
        }
        if let Ok(mut info) = state.info.lock() {
            *info = None;
        }
    }
}

/// Force-kill every scraper image on Windows, including PyInstaller orphans.
///
/// `CommandChild::kill` only hits the process we spawned. PyInstaller onefile
/// and previous crashed sessions can leave extra `devleadhunter-scraper.exe`
/// processes that still lock the binary — NSIS then fails with
/// "Error opening file for writing".
#[cfg(windows)]
fn kill_windows_sidecar_images() {
    use std::os::windows::process::CommandExt;
    use std::process::{Command, Stdio};

    // CREATE_NO_WINDOW — avoid a flashing console during update shutdown.
    const CREATE_NO_WINDOW: u32 = 0x0800_0000;
    let _ = Command::new("taskkill")
        .args(["/F", "/T", "/IM", WINDOWS_SIDECAR_IMAGE])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .creation_flags(CREATE_NO_WINDOW)
        .status();
}

#[cfg(not(windows))]
fn kill_windows_sidecar_images() {}

/// Stop the sidecar; called when the app exits so no orphan process survives.
pub fn stop(app: &AppHandle) {
    kill_managed_child(app);
    kill_windows_sidecar_images();
}

/// Stop every scraper process and wait until Windows releases the exe handle.
///
/// Must run before the NSIS updater copies `devleadhunter-scraper.exe`. The
/// plain `RunEvent::Exit` kill races the installer and is not enough on its own.
#[tauri::command]
pub fn prepare_scraper_for_update(app: AppHandle) -> Result<(), String> {
    stop(&app);
    // Give the kernel a moment to drop file locks after taskkill returns.
    std::thread::sleep(Duration::from_millis(1200));
    Ok(())
}

/// Expose the sidecar's port and token to the web layer.
#[tauri::command]
pub fn scraper_sidecar_info(state: State<'_, SidecarState>) -> Result<SidecarInfo, String> {
    state
        .info
        .lock()
        .map_err(|_| "state poisoned".to_string())?
        .clone()
        .ok_or_else(|| "sidecar not started".to_string())
}
