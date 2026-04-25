; installer.nsh — kills any process holding Ashley files BEFORE
; NSIS tries to overwrite them. Without this, the user gets the
; "Cannot close Ashley" dialog during auto-update.
;
; Strategy: simple taskkill on the EXACT image names Ashley spawns.
; No filters, no PowerShell — just brute force. The trade-off is
; that if the user has another Python/Node app running, it'll get
; killed too — but during an Ashley update that's an acceptable
; compromise versus a broken installer.
;
; We hook into MULTIPLE NSIS macros (customInit + customInstall) so
; the kill fires in both early init and right before file copy.
; Belt and braces — if one hook timing is wrong, the other catches it.

; ─────────────────────────────────────────────────────────────────
; Reusable macro that does the actual killing.
; Order matters: kill the parent (Ashley.exe) WITH its tree first,
; then any leftover orphans. Sleeps in between to let Windows
; release file handles.
; ─────────────────────────────────────────────────────────────────
!macro KillAshleyProcesses
  ; Kill main Electron process + its child tree (covers most cases).
  nsExec::Exec 'taskkill /F /IM "Ashley.exe" /T'

  ; Brute-force kill orphaned children. /F = force, no filter so
  ; this catches them whether the parent died first or not.
  nsExec::Exec 'taskkill /F /IM "python.exe"'
  nsExec::Exec 'taskkill /F /IM "node.exe"'
  nsExec::Exec 'taskkill /F /IM "bun.exe"'
  nsExec::Exec 'taskkill /F /IM "reflex.exe"'

  ; Conhost windows that may be hosting our spawned processes.
  nsExec::Exec 'taskkill /F /IM "conhost.exe" /FI "MEMUSAGE lt 5000"'

  ; Wait 2s for Windows to release file handles. Without this,
  ; the kill returns instantly but the .exe lock can persist.
  Sleep 2000
!macroend

; Runs as part of .onInit — VERY early, before any NSIS UI.
!macro customInit
  !insertmacro KillAshleyProcesses
!macroend

; Runs inside the install Section, right before file extraction.
; Backup in case customInit timing wasn't enough.
!macro customInstall
  !insertmacro KillAshleyProcesses
!macroend

; Same treatment for the uninstaller.
!macro customUnInit
  !insertmacro KillAshleyProcesses
!macroend
