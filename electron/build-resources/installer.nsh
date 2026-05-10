; installer.nsh — defensas críticas del installer/uninstaller de Ashley.
;
; Hace 3 cosas:
;   1. Mata procesos de Ashley en marcha antes de overwrite
;   2. (v0.19.10) NO mata python/node de OTROS apps del user — solo
;      los hijos de Ashley (filtrado por CommandLine via PowerShell)
;   3. (v0.19.10) Limpia carpetas huérfanas de installs interrumpidos
;      (caso real: orphan uninstallerIcon.ico bloqueaba install nuevo)

!include "FileFunc.nsh"
!include "LogicLib.nsh"

; ─────────────────────────────────────────────────────────────────
; Macro reutilizable: matar procesos de Ashley en marcha.
;
; CRITICAL: NO usar `/T` sobre Ashley.exe. Cuando auto-update corre,
; electron-updater spawna ESTE installer como CHILD del Ashley.exe en
; ejecución. `taskkill /T` walka el process tree, así que matar
; Ashley.exe con /T desde customInit suicidaría el installer mismo
; (bug histórico v0.13.6 → 0.13.7).
;
; v0.19.10 — el original mataba `python.exe` y `node.exe` sin filtrar.
; Eso ASESINABA cualquier IDE Python/Node del user (VS Code, IntelliJ
; con Python interpreter, scripts Node en background, etc). Cambio:
; filtrar por CommandLine via PowerShell. Solo matamos procesos cuyo
; CommandLine contiene "ashley\resources" (= hijo de NUESTRA app).
; ─────────────────────────────────────────────────────────────────
!macro KillAshleyProcesses
  ; Kill TODAS las instancias de Ashley.exe (main + GPU + renderer +
  ; utility), pero SIN /T — ver nota CRITICAL arriba. Es seguro porque
  ; el nombre exacto "Ashley.exe" solo existe en NUESTRA app.
  nsExec::Exec 'taskkill /F /IM "Ashley.exe"'

  ; v0.19.10 — kill SOLO los python/node/bun/reflex hijos de Ashley.
  ; PowerShell filtra por CommandLine — si VS Code tiene un Python
  ; interpreter abierto, NO lo matamos (su CommandLine no contiene
  ; "ashley\resources").
  ;
  ; v0.19.13 — NSIS warning fix: $_ de PowerShell colisiona con la
  ; sintaxis de variables de NSIS ($VARNAME). En NSIS `$$` escapa a `$`
  ; literal, así que $$_.Name → $_.Name al ejecutarse. Sin esto, NSIS
  ; daba warning 6000 ("unknown variable/constant _.Name") y CI lo
  ; trataba como error → build fallaba (v0.19.10 / v0.19.11 / v0.19.12).
  nsExec::Exec 'powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { ($$_.Name -match \"^(python|node|bun|reflex)\") -and ($$_.CommandLine -like \"*ashley\\resources*\") } | ForEach-Object { try { Stop-Process -Id $$_.ProcessId -Force -ErrorAction Stop } catch {} }"'

  ; Esperar 2s para que Windows libere los file handles. Sin esto, el
  ; kill devuelve al instante pero el lock del .exe puede persistir.
  Sleep 2000
!macroend

; ─────────────────────────────────────────────────────────────────
; v0.19.10 — Cleanup defensivo de instalación huérfana.
;
; Bug observado en el dev PC: si una instalación previa se interrumpió
; (Ctrl+C en uninstaller, crash de Windows, antivirus matando el process,
; user cierra el wizard a la mitad), queda una carpeta
; `$LOCALAPPDATA\Programs\ashley\` con UN SOLO archivo
; (`uninstallerIcon.ico`) y SIN Ashley.exe.
;
; El nuevo installer detecta esa carpeta como "instalación previa",
; intenta upgrade, se confunde y se cierra silenciosamente sin instalar
; nada — el wizard se abre, pides "solo para mí", y se cierra sin error.
;
; Fix: si la carpeta target existe PERO no tiene Ashley.exe, la borramos
; antes de empezar el install. Es seguro: si tuviera una instalación
; legítima, Ashley.exe estaría ahí y NO entramos en la rama de delete.
; ─────────────────────────────────────────────────────────────────
!macro CleanupOrphanInstallDir
  ; $LOCALAPPDATA\Programs\ashley\ es el target perUser por defecto.
  ${If} ${FileExists} "$LOCALAPPDATA\Programs\ashley\*"
    ${IfNot} ${FileExists} "$LOCALAPPDATA\Programs\ashley\Ashley.exe"
      ; Carpeta existe pero falta el binario principal → orphan.
      DetailPrint "Detectada instalacion huerfana sin Ashley.exe — limpiando"
      RMDir /r "$LOCALAPPDATA\Programs\ashley"
      Sleep 500  ; dejar que Windows libere los handles
    ${EndIf}
  ${EndIf}
!macroend

; ─────────────────────────────────────────────────────────────────
; HOOKS de electron-builder (estos nombres son fixed por el template)
; ─────────────────────────────────────────────────────────────────

; Runs como parte de .onInit — MUY temprano, antes de la UI de NSIS.
!macro customInit
  !insertmacro KillAshleyProcesses
  !insertmacro CleanupOrphanInstallDir
!macroend

; Runs dentro de la install Section, justo antes de file extraction.
; Backup en caso de que el timing del customInit no fuera suficiente.
!macro customInstall
  !insertmacro KillAshleyProcesses
!macroend

; Mismo trato para el uninstaller.
!macro customUnInit
  !insertmacro KillAshleyProcesses
!macroend
