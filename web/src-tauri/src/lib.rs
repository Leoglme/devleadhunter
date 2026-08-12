// Prod → local DB sync is a local dev tool only: the module is compiled out of release
// builds (debug_assertions is false in `tauri build --release`).
#[cfg(debug_assertions)]
mod db_sync;

// The WebView2 permission plumbing only exists on Windows.
#[cfg(windows)]
mod media_permissions;

mod scraper_sidecar;

/// Sync the local dev database from prod (mysqldump → import). The command always exists
/// (so the frontend can `invoke` it), but only runs in debug builds; in a release build it
/// returns an error instead — the desktop app never syncs against a user's machine in prod.
#[tauri::command]
fn sync_dev_database_from_prod() -> Result<String, String> {
    #[cfg(debug_assertions)]
    {
        db_sync::sync_dev_database_from_prod_impl()
    }
    #[cfg(not(debug_assertions))]
    {
        Err("Prod → local DB sync is only available in debug builds (`tauri:dev`).".into())
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_shell::init())
        .manage(scraper_sidecar::SidecarState::default())
        .invoke_handler(tauri::generate_handler![
            sync_dev_database_from_prod,
            scraper_sidecar::scraper_sidecar_info,
            scraper_sidecar::prepare_scraper_for_update
        ])
        .setup(|_app| {
            // Sans ça, `getUserMedia` (enregistrement du clip de prospection)
            // ne peut pas ouvrir la caméra dans l'app desktop.
            #[cfg(windows)]
            {
                use tauri::Manager;
                if let Some(window) = _app.get_webview_window("main") {
                    media_permissions::grant_camera_and_microphone(&window);
                }
            }

            // Le scraping doit partir de l'IP résidentielle de l'utilisateur :
            // un échec ici ne doit pas empêcher le reste de l'app de démarrer.
            if let Err(error) = scraper_sidecar::start(&_app.handle().clone()) {
                log::error!("scraping sidecar unavailable: {error}");
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            // ExitRequested can be cancelled; Exit is the last chance before the
            // process dies. Kill on both so a Windows update never races a live sidecar.
            match event {
                tauri::RunEvent::ExitRequested { .. } | tauri::RunEvent::Exit => {
                    scraper_sidecar::stop(app_handle);
                }
                _ => {}
            }
        });
}
