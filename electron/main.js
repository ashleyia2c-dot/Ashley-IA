// Ashley — Electron wrapper (hardened)
// Contenedor nativo alrededor del backend Reflex. Protecciones incluidas:
//  - API key del usuario cifrada con DPAPI (electron safeStorage)
//  - Bloqueo de DevTools / View Source / menu contextual en produccion
//  - Datos del usuario aislados en %APPDATA%\Ashley
//  - Disclosure de permisos en primera ejecucion

const { app, BrowserWindow, Menu, shell, ipcMain, safeStorage, dialog, session } = require('electron');
const { spawn, exec } = require('child_process');
const path = require('path');
const http = require('http');
const net = require('net');
const fs = require('fs');
const { setupAutoUpdater, stopAutoUpdater } = require('./updater');

// Command-line switches (deben ejecutarse ANTES de app.whenReady)
// Ayudan con compatibilidad de MediaRecorder en algunos Windows
app.commandLine.appendSwitch('enable-features', 'SharedArrayBuffer');

// ─── Configuración general ────────────────────────────────────────────────
function resolveProjectRoot() {
  const candidates = [
    path.resolve(__dirname, '..'),
    path.join(process.env.USERPROFILE || '', 'Desktop', 'reflex-companion'),
    path.join(process.env.USERPROFILE || '', 'reflex-companion'),
    'C:\\reflex-companion',
  ];
  for (const p of candidates) {
    if (p && fs.existsSync(path.join(p, 'venv', 'Scripts', 'reflex.exe'))) {
      return p;
    }
  }
  return candidates[0];
}

const PROJECT_ROOT = resolveProjectRoot();
const VENV_REFLEX = path.join(PROJECT_ROOT, 'venv', 'Scripts', 'reflex.exe');
const REFLEX_HOST = '127.0.0.1';
// Puertos base. Si están ocupados (procesos zombis de sesiones previas,
// Hyper-V reservando rangos, etc.) buscamos el siguiente libre.
const FRONTEND_PORT_BASE = 17300;
const BACKEND_PORT_BASE  = 17800;
// Estos se resuelven en runtime al arrancar
let REFLEX_FRONTEND_PORT = FRONTEND_PORT_BASE;
let REFLEX_BACKEND_PORT  = BACKEND_PORT_BASE;
let REFLEX_URL = `http://${REFLEX_HOST}:${REFLEX_FRONTEND_PORT}`;
const STARTUP_TIMEOUT_MS = 120000;
const DEV_MODE = process.argv.includes('--dev');

// ─── Storage seguro del usuario ───────────────────────────────────────────
// app.getPath('userData') → %APPDATA%\Ashley en Windows (carpeta privada por usuario)
const USER_DATA = app.getPath('userData');
const ASHLEY_DATA_DIR = path.join(USER_DATA, 'data');        // para JSONs de memoria
const API_KEY_FILE = path.join(USER_DATA, 'key.bin');        // cifrada con DPAPI
const DISCLOSURE_FLAG = path.join(USER_DATA, 'disclosure.ok');
const LANGUAGE_FILE = path.join(ASHLEY_DATA_DIR, 'language.json'); // compartido con Python i18n

// Asegurar que existen
try { fs.mkdirSync(ASHLEY_DATA_DIR, { recursive: true }); } catch {}

// ─── Estado ───────────────────────────────────────────────────────────────
let reflexProcess = null;
let mainWindow = null;
let splashWindow = null;
let onboardingWindow = null;
let reflexApiKey = null;            // guardada para reusar en auto-restart
let isShuttingDown = false;         // true cuando el usuario cierra la app
let reflexRestartCount = 0;
const MAX_REFLEX_RESTARTS = 5;

// ─── Logging ──────────────────────────────────────────────────────────────
function log(msg) {
  const ts = new Date().toISOString().slice(11, 19);
  console.log(`[${ts}] ${msg}`);
}

// ─── Detección REAL de puerto en uso ──────────────────────────────────────
// Testea por TCP connect (no por bind): si podemos conectar, alguien escucha,
// aunque esté en 0.0.0.0 y nosotros intentemos bind en 127.0.0.1.
function isPortInUse(port) {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    let settled = false;
    const finish = (used) => { if (!settled) { settled = true; resolve(used); } };
    socket.setTimeout(400);
    socket.once('connect', () => { socket.destroy(); finish(true); });
    socket.once('timeout', () => { socket.destroy(); finish(false); });
    socket.once('error',  () => { socket.destroy(); finish(false); });
    try { socket.connect(port, '127.0.0.1'); }
    catch { finish(false); }
  });
}

async function findFreePort(startPort, maxTries = 30) {
  for (let i = 0; i < maxTries; i++) {
    const port = startPort + i;
    const used = await isPortInUse(port);
    if (!used) return port;
  }
  throw new Error(`No free port in [${startPort}, ${startPort + maxTries})`);
}

// ─── Kill de procesos que tienen un puerto en LISTENING ───────────────────
// Si hay un zombie de una sesión previa, lo exterminamos antes de arrancar.
function killProcessesOnPort(port) {
  return new Promise((resolve) => {
    exec(`netstat -ano -p tcp | findstr :${port}`, (err, stdout) => {
      if (err || !stdout) return resolve(0);
      const pids = new Set();
      for (const line of stdout.split('\n')) {
        if (!line.includes('LISTENING')) continue;
        const parts = line.trim().split(/\s+/);
        const pid = parts[parts.length - 1];
        // filtra PID 0 (System Idle) y cosas raras
        if (pid && /^\d+$/.test(pid) && pid !== '0') pids.add(pid);
      }
      if (!pids.size) return resolve(0);
      const pidList = [...pids];
      log(`Port ${port} ocupado por PID(s): ${pidList.join(',')} → matando`);
      const killArgs = pidList.flatMap(p => ['/PID', p]);
      const cmd = `taskkill /F ${killArgs.join(' ')}`;
      exec(cmd, { windowsHide: true }, () => resolve(pidList.length));
    });
  });
}

async function pickReflexPorts() {
  // Primero intenta limpiar cualquier zombie en los puertos base
  await killProcessesOnPort(FRONTEND_PORT_BASE);
  await killProcessesOnPort(BACKEND_PORT_BASE);
  // Pequeña espera para que Windows libere los sockets
  await new Promise(r => setTimeout(r, 500));

  // Ahora sí, busca puerto libre (por TCP connect, robusto contra 0.0.0.0)
  REFLEX_FRONTEND_PORT = await findFreePort(FRONTEND_PORT_BASE);
  REFLEX_BACKEND_PORT  = await findFreePort(BACKEND_PORT_BASE);
  REFLEX_URL = `http://${REFLEX_HOST}:${REFLEX_FRONTEND_PORT}`;
  log(`Puertos asignados: frontend=${REFLEX_FRONTEND_PORT}, backend=${REFLEX_BACKEND_PORT}`);
}

// ─── API key: obtener / guardar ───────────────────────────────────────────
function loadStoredApiKey() {
  if (!fs.existsSync(API_KEY_FILE)) return null;
  if (!safeStorage.isEncryptionAvailable()) {
    log('safeStorage no disponible en este sistema');
    return null;
  }
  try {
    const encrypted = fs.readFileSync(API_KEY_FILE);
    return safeStorage.decryptString(encrypted);
  } catch (err) {
    log(`Error descifrando API key: ${err.message}`);
    return null;
  }
}

function saveApiKey(key) {
  if (!safeStorage.isEncryptionAvailable()) {
    throw new Error('Cifrado no disponible en este sistema');
  }
  const encrypted = safeStorage.encryptString(key);
  fs.writeFileSync(API_KEY_FILE, encrypted, { mode: 0o600 });
}

function loadApiKeyFromEnvFile() {
  // Fallback para modo dev: leer .env del proyecto
  const envFile = path.join(PROJECT_ROOT, '.env');
  if (!fs.existsSync(envFile)) return null;
  try {
    const content = fs.readFileSync(envFile, 'utf8');
    const match = content.match(/^\s*XAI_API_KEY\s*=\s*["']?([^"'\s\r\n]+)/m);
    return match ? match[1] : null;
  } catch {
    return null;
  }
}

// ─── Disclosure (primera ejecución) ───────────────────────────────────────
function disclosureAccepted() {
  return fs.existsSync(DISCLOSURE_FLAG);
}

function markDisclosureAccepted() {
  fs.writeFileSync(DISCLOSURE_FLAG, new Date().toISOString());
}

function saveLanguage(lang) {
  const normalized = (lang === 'es') ? 'es' : 'en';
  try {
    fs.writeFileSync(LANGUAGE_FILE, JSON.stringify({ language: normalized }));
  } catch (err) {
    log(`No pude guardar language.json: ${err.message}`);
  }
}

// ─── Hardening: bloquear DevTools, View Source, context menu en produccion
function hardenWindow(win) {
  if (DEV_MODE) return;

  // Bloquear atajos de DevTools / View Source
  win.webContents.on('before-input-event', (event, input) => {
    const key = (input.key || '').toLowerCase();
    const ctrl = input.control || input.meta;
    const shift = input.shift;

    // F12, Ctrl+Shift+I, Ctrl+Shift+J, Ctrl+Shift+C (elem inspector), Ctrl+U (view source)
    if (key === 'f12') return event.preventDefault();
    if (ctrl && shift && (key === 'i' || key === 'j' || key === 'c')) return event.preventDefault();
    if (ctrl && key === 'u') return event.preventDefault();
  });

  // Bloquear menu contextual (clic derecho)
  win.webContents.on('context-menu', (e) => e.preventDefault());

  // Bloquear aperturas programaticas de DevTools
  win.webContents.on('devtools-opened', () => win.webContents.closeDevTools());

  // Cualquier navegacion a URLs no localhost → abrir externo, NO dentro de la app
  win.webContents.on('will-navigate', (e, url) => {
    if (!url.startsWith(REFLEX_URL)) {
      e.preventDefault();
      shell.openExternal(url);
    }
  });
}

// ─── Splash ───────────────────────────────────────────────────────────────
function createSplash() {
  const iconPath = path.join(__dirname, 'build-resources', 'icon.ico');
  splashWindow = new BrowserWindow({
    width: 400, height: 280,
    frame: false, transparent: false, alwaysOnTop: true,
    resizable: false, movable: true,
    backgroundColor: '#0a0a0a',
    icon: fs.existsSync(iconPath) ? iconPath : undefined,
    center: true, skipTaskbar: false,
    webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true },
  });
  const splashHTML = `<!DOCTYPE html><html><head><style>
    body{margin:0;padding:0;background:#0a0a0a;color:#ff9aee;font-family:'Segoe UI',sans-serif;
      display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;user-select:none}
    h1{margin:0 0 12px;font-size:42px;font-weight:300;letter-spacing:4px}
    .sub{color:#bbb;font-size:13px;margin-bottom:28px}
    .spinner{width:32px;height:32px;border:3px solid #333;border-top-color:#ff9aee;
      border-radius:50%;animation:spin 0.9s linear infinite}
    @keyframes spin{to{transform:rotate(360deg)}}
    .status{margin-top:20px;font-size:11px;color:#666}
  </style></head><body>
    <h1>Ashley</h1><div class="sub">iniciando...</div>
    <div class="spinner"></div><div class="status">arrancando backend</div>
  </body></html>`;
  splashWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(splashHTML));
  splashWindow.on('closed', () => { splashWindow = null; });
  hardenWindow(splashWindow);
}

// ─── Onboarding (primera ejecucion: disclosure + API key) ─────────────────
function runOnboarding() {
  return new Promise((resolve, reject) => {
    const iconPath = path.join(__dirname, 'build-resources', 'icon.ico');
    onboardingWindow = new BrowserWindow({
      width: 620, height: 720,
      resizable: false, minimizable: false, maximizable: false,
      title: 'Ashley — Configuración inicial',
      backgroundColor: '#0a0a0a',
      icon: fs.existsSync(iconPath) ? iconPath : undefined,
      autoHideMenuBar: true,
      webPreferences: {
        preload: path.join(__dirname, 'preload.js'),
        contextIsolation: true,
        nodeIntegration: false,
        sandbox: false, // preload necesita acceso a ipcRenderer
      },
    });
    onboardingWindow.setMenuBarVisibility(false);
    onboardingWindow.loadFile(path.join(__dirname, 'onboarding.html'));
    hardenWindow(onboardingWindow);

    let completed = false;

    const onSubmit = (_event, data) => {
      if (!data || !data.apiKey) return;
      try {
        saveApiKey(data.apiKey);
        markDisclosureAccepted();
        if (data.language) saveLanguage(data.language);
        completed = true;
        if (onboardingWindow) onboardingWindow.close();
        resolve(data.apiKey);
      } catch (err) {
        reject(err);
      }
    };

    const onCancel = () => {
      if (onboardingWindow) onboardingWindow.close();
    };

    ipcMain.once('onboarding-submit', onSubmit);
    ipcMain.once('onboarding-cancel', onCancel);

    onboardingWindow.on('closed', () => {
      onboardingWindow = null;
      ipcMain.removeListener('onboarding-submit', onSubmit);
      ipcMain.removeListener('onboarding-cancel', onCancel);
      if (!completed) reject(new Error('Onboarding cancelado por el usuario'));
    });
  });
}

// ─── Resolver API key: storage → .env → onboarding ────────────────────────
async function resolveApiKey() {
  const stored = loadStoredApiKey();
  if (stored) {
    log('API key cargada de storage cifrado');
    return stored;
  }
  const fromEnv = loadApiKeyFromEnvFile();
  if (fromEnv) {
    log('API key cargada de .env (modo dev)');
    return fromEnv;
  }
  log('No hay API key guardada — lanzando onboarding');
  return await runOnboarding();
}

// ─── Line-buffered logger ─────────────────────────────────────────────────
function makeLineLogger(prefix, isErr) {
  let buf = '';
  return (chunk) => {
    buf += chunk.toString('utf8');
    const parts = buf.split(/\r?\n|\r/);
    buf = parts.pop();
    const out = isErr ? process.stderr : process.stdout;
    for (const line of parts) {
      const t = line.trim();
      if (t) out.write(`[${prefix}] ${t}\n`);
    }
  };
}

// ─── Arrancar Reflex con env vars de seguridad ────────────────────────────
function startReflex(apiKey) {
  if (!fs.existsSync(VENV_REFLEX)) {
    throw new Error(`No encuentro reflex.exe en ${VENV_REFLEX}`);
  }

  reflexApiKey = apiKey;
  log(`Arrancando Reflex (intento ${reflexRestartCount + 1}) desde ${PROJECT_ROOT}`);
  log(`Datos en: ${ASHLEY_DATA_DIR}`);

  reflexProcess = spawn(VENV_REFLEX, [
    'run',
    '--frontend-port', String(REFLEX_FRONTEND_PORT),
    '--backend-port',  String(REFLEX_BACKEND_PORT),
    '--loglevel', 'warning',
  ], {
    cwd: PROJECT_ROOT,
    env: {
      ...process.env,
      XAI_API_KEY: apiKey,
      ASHLEY_DATA_DIR: ASHLEY_DATA_DIR,
      // Para que el frontend sepa dónde está el backend (custom /api/* routes)
      ASHLEY_BACKEND_PORT: String(REFLEX_BACKEND_PORT),
    },
    shell: false,
    windowsHide: true,
  });

  reflexProcess.stdout.on('data', makeLineLogger('reflex', false));
  reflexProcess.stderr.on('data', makeLineLogger('reflex', true));

  reflexProcess.on('exit', (code, signal) => {
    log(`Reflex process exited (code=${code}, signal=${signal})`);
    reflexProcess = null;
    if (isShuttingDown) return;

    // Exit inesperado → auto-restart hasta MAX intentos
    if (code !== 0) {
      reflexRestartCount++;
      if (reflexRestartCount <= MAX_REFLEX_RESTARTS) {
        log(`Restarting Reflex in 2s... (${reflexRestartCount}/${MAX_REFLEX_RESTARTS})`);
        setTimeout(async () => {
          if (isShuttingDown || reflexProcess) return;
          try {
            // Re-picking ports en cada restart — por si el port anterior quedó atascado
            await pickReflexPorts();
            startReflex(reflexApiKey);
          } catch (err) {
            log(`Restart failed: ${err.message}`);
          }
        }, 2000);
      } else {
        log(`Max restarts exceeded. Giving up.`);
        dialog.showErrorBox(
          'Ashley — backend crashed',
          'The Reflex backend keeps crashing and has been restarted ' + MAX_REFLEX_RESTARTS +
          ' times. Please close Ashley and check the console logs for errors.'
        );
      }
    }
  });
  reflexProcess.on('error', (err) => log(`Reflex spawn error: ${err.message}`));
}

// ─── Esperar a que Reflex responda ────────────────────────────────────────
function waitForReflex(timeoutMs) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    let done = false;
    const finish = (err) => { if (done) return; done = true; err ? reject(err) : resolve(); };
    const scheduleRetry = () => {
      if (done) return;
      if (Date.now() - start > timeoutMs) finish(new Error(`Reflex no arrancó en ${timeoutMs}ms`));
      else setTimeout(check, 600);
    };
    const check = () => {
      if (done) return;
      let settled = false;
      const fail = () => { if (settled) return; settled = true; scheduleRetry(); };
      const req = http.get(REFLEX_URL, { timeout: 2000 }, (res) => {
        res.resume();
        if (settled) return;
        settled = true;
        if (res.statusCode && res.statusCode < 500) {
          log(`Reflex está respondiendo (${Date.now() - start}ms)`);
          finish();
        } else scheduleRetry();
      });
      req.on('error', fail);
      req.on('timeout', () => { req.destroy(); fail(); });
    };
    check();
  });
}

// ─── Ventana principal ────────────────────────────────────────────────────
function createMainWindow() {
  const iconPath = path.join(__dirname, 'build-resources', 'icon.ico');
  mainWindow = new BrowserWindow({
    width: 1280, height: 820,
    minWidth: 900, minHeight: 650,
    title: 'Ashley',
    icon: fs.existsSync(iconPath) ? iconPath : undefined,
    backgroundColor: '#0a0a0a',
    autoHideMenuBar: !DEV_MODE,
    show: false,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      // sandbox:true bloquea require() en preload.js → necesitamos false aquí
      // porque preload.js usa ipcRenderer. contextIsolation sigue activo así
      // que el preload NO filtra todo Node al renderer — solo expone lo
      // explícitamente pasado por contextBridge.exposeInMainWorld().
      sandbox: false,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  mainWindow.loadURL(REFLEX_URL);

  // Links externos → navegador del sistema
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith(REFLEX_URL)) return { action: 'allow' };
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.once('ready-to-show', () => {
    if (splashWindow) splashWindow.close();
    mainWindow.show();
  });

  mainWindow.on('closed', () => { mainWindow = null; });

  hardenWindow(mainWindow);

  if (DEV_MODE) {
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  }
}

// ─── Matar Reflex y arbol de procesos ─────────────────────────────────────
function killReflex() {
  if (!reflexProcess || reflexProcess.killed) return;
  const pid = reflexProcess.pid;
  log(`Matando Reflex (pid=${pid}) y su árbol de procesos`);
  if (process.platform === 'win32') {
    exec(`taskkill /pid ${pid} /T /F`, (err) => {
      if (err) log(`taskkill err: ${err.message}`);
    });
  } else {
    try { reflexProcess.kill('SIGTERM'); } catch {}
  }
}

// ─── Lifecycle ────────────────────────────────────────────────────────────
app.whenReady().then(async () => {
  Menu.setApplicationMenu(null);

  // Conceder permiso de micrófono al renderer (sin esto getUserMedia falla silencioso)
  const ALLOWED_PERMS = new Set([
    'media', 'microphone', 'audioCapture',
    'videoCapture',  // a veces Chromium pide este aunque solo quieras audio
    'clipboard-read', 'clipboard-sanitized-write',
  ]);

  // Permisos que se deniegan silenciosamente (Chromium/Reflex los chequea en
  // bucle y llenaban el log con spam inútil cada 60s). Los denegamos igual,
  // sólo no lo registramos.
  const SILENT_DENY = new Set([
    'background-sync',    // service worker de Next.js: no lo usamos
    'notifications',       // no queremos notifs del sistema
    'periodic-background-sync',
  ]);

  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback, details) => {
    const allowed = ALLOWED_PERMS.has(permission);
    if (!SILENT_DENY.has(permission)) {
      log(`Permission REQUEST: "${permission}" → ${allowed ? 'GRANTED' : 'DENIED'} (mediaTypes=${(details && details.mediaTypes) || 'n/a'})`);
    }
    callback(allowed);
  });
  session.defaultSession.setPermissionCheckHandler((webContents, permission, origin) => {
    const allowed = ALLOWED_PERMS.has(permission);
    if (!SILENT_DENY.has(permission)) {
      log(`Permission CHECK:   "${permission}" for "${origin}" → ${allowed}`);
    }
    return allowed;
  });

  try {
    // 1. Resolver API key (puede disparar onboarding)
    const apiKey = await resolveApiKey();
    if (!apiKey) throw new Error('No hay API key disponible');

    // 2. Splash mientras Reflex arranca
    createSplash();

    // 3. Encontrar puertos libres (evita conflictos con zombies de sesiones previas)
    await pickReflexPorts();

    // 4. Arrancar Reflex con la key + data dir + puertos libres
    startReflex(apiKey);
    await waitForReflex(STARTUP_TIMEOUT_MS);

    // 4. Ventana principal
    createMainWindow();

    // 5. Auto-updater: chequea GitHub Releases, descarga en background, notifica a la UI.
    // Se desactiva automaticamente en dev/no-empaquetado (ver updater.js).
    setupAutoUpdater(mainWindow, { isDev: DEV_MODE });
  } catch (err) {
    log(`Error arrancando: ${err.message}`);
    if (splashWindow) splashWindow.close();
    if (onboardingWindow) onboardingWindow.close();
    dialog.showErrorBox('Ashley no pudo arrancar', `${err.message}`);
    killReflex();
    app.quit();
  }
});

app.on('window-all-closed', () => {
  isShuttingDown = true;
  stopAutoUpdater();
  killReflex();
  app.quit();
});

app.on('before-quit', () => {
  isShuttingDown = true;
  stopAutoUpdater();
  killReflex();
});

process.on('SIGINT',  () => { isShuttingDown = true; killReflex(); process.exit(0); });
process.on('SIGTERM', () => { isShuttingDown = true; killReflex(); process.exit(0); });
