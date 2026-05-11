; installer.nsh — defensas críticas del installer/uninstaller de Ashley.
;
; Hace 4 cosas:
;   1. Mata procesos de Ashley en marcha antes de overwrite
;   2. (v0.19.10) NO mata python/node de OTROS apps del user — solo
;      los hijos de Ashley (filtrado por CommandLine via PowerShell)
;   3. (v0.19.10) Limpia carpetas huérfanas de installs interrumpidos
;   4. (v0.19.17) Defensas EXTENDIDAS contra residuos de installs malos:
;      - install dir sin Ashley.exe → orphan, borrar
;      - install dir SIN resources/app.asar → broken install, borrar
;      - install dir con Ashley.exe de 0 bytes → corrupt download, borrar
;      - %LOCALAPPDATA%\ashley-updater\pending\ → stale update, borrar
;
; NUNCA tocamos %APPDATA%\Ashley\data\ — ahí viven el chat history, facts,
; diary, achievements del user. Eso es SAGRADO. Solo borramos archivos del
; PROGRAMA, nunca datos del user.

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
;
; v0.19.13 — NSIS warning fix: $_ de PowerShell colisiona con la
; sintaxis de variables de NSIS ($VARNAME). En NSIS `$$` escapa a `$`
; literal, así que $$_.Name → $_.Name al ejecutarse.
; ─────────────────────────────────────────────────────────────────
!macro KillAshleyProcesses
  ; Kill TODAS las instancias de Ashley.exe (main + GPU + renderer +
  ; utility), pero SIN /T — ver nota CRITICAL arriba. Es seguro porque
  ; el nombre exacto "Ashley.exe" solo existe en NUESTRA app.
  nsExec::Exec 'taskkill /F /IM "Ashley.exe"'

  ; Kill SOLO los python/node/bun/reflex hijos de Ashley.
  nsExec::Exec 'powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { ($$_.Name -match \"^(python|node|bun|reflex)\") -and ($$_.CommandLine -like \"*ashley\\resources*\") } | ForEach-Object { try { Stop-Process -Id $$_.ProcessId -Force -ErrorAction Stop } catch {} }"'

  ; Wait 2s para que Windows libere los file handles.
  Sleep 2000
!macroend

; ─────────────────────────────────────────────────────────────────
; v0.19.17 — Cleanup extendido de instalaciones residuales/rotas.
;
; ESCENARIOS QUE LIMPIA:
;
; 1. Install ABANDONADO (orphan dir sin Ashley.exe):
;    Histórico bug — uninstall interrumpido dejaba uninstallerIcon.ico
;    huérfano y bloqueaba new install. Ya capturado en v0.19.10.
;
; 2. Install ROTO (sin resources/app.asar):
;    Si install se interrumpió a la mitad de extracción, puede haber
;    Ashley.exe pero sin recursos. Al arrancar daría errors "no asset
;    found". Detección: si Ashley.exe existe PERO resources/app.asar NO,
;    es install corrupto.
;
; 3. Install CORRUPTO (Ashley.exe = 0 bytes):
;    Download interrumpido (cierre de browser durante download, antivirus
;    truncando, etc) puede dejar Ashley.exe vacío. Detección: GetFileSize.
;
; 4. Auto-updater PENDING colgado:
;    Si una auto-update fue interrumpida (apagado del PC durante download),
;    queda %LOCALAPPDATA%\ashley-updater\pending\ con .exe parcial. Eso
;    bloquea futuras auto-updates. Limpiamos esa carpeta — nuevo download
;    arrancará limpio.
;
; SEGURIDAD: NO tocamos %APPDATA%\Ashley\data\ JAMÁS. Eso son los datos
; del user (chat, facts, diary). Solo borramos archivos del PROGRAMA en
; %LOCALAPPDATA%\Programs\ashley\ y %LOCALAPPDATA%\ashley-updater\.
; ─────────────────────────────────────────────────────────────────
!macro CleanupOrphanInstallDir
  ; Variable para tracking si necesitamos limpiar el install dir.
  Var /GLOBAL CleanupNeeded
  StrCpy $CleanupNeeded "0"

  ${If} ${FileExists} "$LOCALAPPDATA\Programs\ashley\*"
    ; Caso 1: dir existe pero falta Ashley.exe (orphan)
    ${IfNot} ${FileExists} "$LOCALAPPDATA\Programs\ashley\Ashley.exe"
      DetailPrint "Detectada instalacion huerfana sin Ashley.exe"
      StrCpy $CleanupNeeded "1"
    ${EndIf}

    ; Caso 2: Ashley.exe existe pero sin resources/app.asar (broken install)
    ${If} ${FileExists} "$LOCALAPPDATA\Programs\ashley\Ashley.exe"
    ${AndIfNot} ${FileExists} "$LOCALAPPDATA\Programs\ashley\resources\app.asar"
      DetailPrint "Detectada instalacion rota (sin resources/app.asar)"
      StrCpy $CleanupNeeded "1"
    ${EndIf}

    ; Caso 3: Ashley.exe es 0 bytes (download corrupto)
    ${If} ${FileExists} "$LOCALAPPDATA\Programs\ashley\Ashley.exe"
      ${GetSize} "$LOCALAPPDATA\Programs\ashley" "/M=Ashley.exe /S=0B" $0 $1 $2
      ${If} $0 == "0"
        DetailPrint "Detectado Ashley.exe corrupto (0 bytes)"
        StrCpy $CleanupNeeded "1"
      ${EndIf}
    ${EndIf}

    ; Si CUALQUIERA de los 3 casos pegó, limpiamos.
    ${If} $CleanupNeeded == "1"
      DetailPrint "Limpiando install dir corrupto antes de re-instalar"
      RMDir /r "$LOCALAPPDATA\Programs\ashley"
      Sleep 500  ; dejar que Windows libere los handles
    ${EndIf}
  ${EndIf}
!macroend

; ─────────────────────────────────────────────────────────────────
; v0.19.17 — Limpiar pending downloads del auto-updater.
;
; electron-updater descarga updates en %LOCALAPPDATA%\ashley-updater\pending\
; Si una update se interrumpe (cierre PC, falta de espacio, network drop),
; queda un .exe parcial ahí. Ese .exe bloquea futuros intentos del updater.
;
; Limpiamos al instalar para que el updater arranque desde estado fresco.
; ─────────────────────────────────────────────────────────────────
!macro CleanupStaleUpdaterState
  ${If} ${FileExists} "$LOCALAPPDATA\ashley-updater\pending\*"
    DetailPrint "Limpiando pending downloads viejos del auto-updater"
    RMDir /r "$LOCALAPPDATA\ashley-updater\pending"
  ${EndIf}
!macroend

; ─────────────────────────────────────────────────────────────────
; HOOKS de electron-builder (estos nombres son fixed por el template)
; ─────────────────────────────────────────────────────────────────

; Runs como parte de .onInit — MUY temprano, antes de la UI de NSIS.
!macro customInit
  !insertmacro KillAshleyProcesses
  !insertmacro CleanupOrphanInstallDir
  !insertmacro CleanupStaleUpdaterState
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
