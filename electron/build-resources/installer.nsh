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
;
; CRITICAL: do NOT use `/T` on Ashley.exe. When auto-update runs,
; electron-updater spawns THIS installer as a CHILD of the running
; Ashley.exe. `taskkill /T` walks the whole process tree, so if we
; kill Ashley.exe with /T from inside customInit we suicide the
; installer itself — splash flashes for a moment then everything
; vanishes (the v0.13.6 → 0.13.7 bug).
;
; Workaround: kill each Electron renderer/helper by image name
; (multiple Ashley.exe instances all match `taskkill /F /IM`),
; then mop up the spawned children explicitly. None of those use
; /T, so the installer's own tree survives.
; ─────────────────────────────────────────────────────────────────
!macro KillAshleyProcesses
  ; Kill ALL Ashley.exe instances (main + GPU + renderer + utility),
  ; but withOUT /T — see the CRITICAL note above.
  nsExec::Exec 'taskkill /F /IM "Ashley.exe"'

  ; Mop up the spawned children Ashley would otherwise leak. These
  ; live as siblings in the process tree (re-parented to System once
  ; Ashley.exe dies), so we have to name them explicitly.
  nsExec::Exec 'taskkill /F /IM "python.exe"'
  nsExec::Exec 'taskkill /F /IM "node.exe"'
  nsExec::Exec 'taskkill /F /IM "bun.exe"'
  nsExec::Exec 'taskkill /F /IM "reflex.exe"'

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
