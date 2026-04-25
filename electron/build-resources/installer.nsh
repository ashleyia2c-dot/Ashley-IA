; installer.nsh — custom NSIS script that runs before the installer
; tries to write any file. Auto-kills Ashley and any leftover python/
; node processes to avoid the "cannot close Ashley, please close it
; manually" dialog during auto-update.
;
; Triggered by build.nsis.include in package.json.

!macro customInstall
  ; Already covered by customInit — leaving customInstall empty intentionally.
!macroend

; Runs BEFORE any installer screen — no UI interaction required for the user.
!macro customInit
  ; Kill the main Ashley executable if it's running.
  nsExec::Exec 'taskkill /F /IM "Ashley.exe" /T'

  ; Kill stray python.exe / node.exe processes spawned by Reflex.
  ; The /FI command-line filter is fragile on stock taskkill, so we
  ; use a PowerShell sweep that targets only processes whose path
  ; contains "ashley" (avoids killing the user's other Python apps).
  nsExec::Exec 'powershell -NoProfile -NonInteractive -Command "Get-CimInstance Win32_Process | Where-Object { ($_.Name -in @(''python.exe'',''node.exe'',''bun.exe'',''reflex.exe'')) -and ($_.CommandLine -like ''*ashley*'') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"'

  ; Tiny delay to let Windows release file handles before NSIS starts
  ; copying. Without this, the kill returns instantly but the exe
  ; lock can persist for ~500ms.
  Sleep 1500
!macroend

; Runs before the uninstaller too, to clean up before remove.
!macro customUnInit
  nsExec::Exec 'taskkill /F /IM "Ashley.exe" /T'
  nsExec::Exec 'powershell -NoProfile -NonInteractive -Command "Get-CimInstance Win32_Process | Where-Object { ($_.Name -in @(''python.exe'',''node.exe'',''bun.exe'',''reflex.exe'')) -and ($_.CommandLine -like ''*ashley*'') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"'
  Sleep 1000
!macroend
