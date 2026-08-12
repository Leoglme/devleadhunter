; Kill orphaned scraping sidecars before NSIS replaces their binary.
; Tauri's CheckIfAppIsRunning only closes the main exe — externalBin sidecars
; keep a file lock and surface "Error opening file for writing".

!macro NSIS_HOOK_PREINSTALL
  DetailPrint "Stopping DevLeadHunter scraping sidecar..."
  nsExec::ExecToLog 'taskkill /F /T /IM devleadhunter-scraper.exe'
  Pop $0
  Sleep 1500
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  DetailPrint "Stopping DevLeadHunter scraping sidecar..."
  nsExec::ExecToLog 'taskkill /F /T /IM devleadhunter-scraper.exe'
  Pop $0
  Sleep 1000
!macroend
