// Ashley — auto-update handler usando electron-updater
//
// Flujo:
//   1. Al arrancar (30s despues de que la UI este lista), consultamos GitHub
//      Releases buscando tags > version actual.
//   2. Si hay update disponible, se descarga en background SIN molestar.
//   3. Cuando termina la descarga, notificamos a la UI via IPC.
//   4. La UI muestra un pill "v1.x disponible - Reiniciar".
//   5. Click del usuario -> quitAndInstall() aplica el update en el proximo
//      arranque.
//
// En --dev mode el updater queda desactivado (electron-updater se niega a
// correr en un proceso de Electron no-empaquetado, asi que igual no haria nada,
// pero lo loggeamos claro).

const { autoUpdater } = require('electron-updater');
const { app, ipcMain } = require('electron');

// ─── Configuracion ────────────────────────────────────────────────────────

// NO descargar automaticamente — queremos notificar primero a la UI por si
// el usuario esta en medio de algo importante. En un futuro podriamos
// hacerlo automatico con un toggle en Settings.
autoUpdater.autoDownload = true;

// Tampoco aplicar automaticamente al quit — respetamos la eleccion del user.
autoUpdater.autoInstallOnAppQuit = false;

// Intervalo de re-chequeo: cada 4h mientras la app este abierta.
// Suficiente para que salgan hotfixes el mismo dia, no tan seguido como para
// saturar la API de GitHub (el rate limit sin token es 60 req/h).
const CHECK_INTERVAL_MS = 4 * 60 * 60 * 1000;  // 4h

// Delay inicial: esperamos 30s despues del arranque para no competir con
// el carga de Reflex / frontend / Whisper warmup.
const INITIAL_DELAY_MS = 30 * 1000;

// ─── Logger con prefijo ───────────────────────────────────────────────────

function log(msg) {
  const ts = new Date().toISOString();
  console.log(`[${ts}] [updater] ${msg}`);
}

// ─── Estado que exponemos al renderer ─────────────────────────────────────
//
// mainWindow.webContents.send('ashley-update:<evento>', payload) es como
// avisamos al frontend. Los nombres de evento son estables — la UI se
// suscribe a ellos via preload.js.

let mainWindowRef = null;
let checkTimer = null;
let lastDownloadedVersion = null;

function emit(event, payload) {
  if (!mainWindowRef || mainWindowRef.isDestroyed()) return;
  try {
    mainWindowRef.webContents.send(`ashley-update:${event}`, payload || {});
  } catch (e) {
    log(`emit failed for ${event}: ${e.message}`);
  }
}

// ─── Handlers de eventos del autoUpdater ──────────────────────────────────

autoUpdater.on('checking-for-update', () => {
  log('checking for updates...');
  emit('checking');
});

autoUpdater.on('update-available', (info) => {
  log(`update available: ${info.version} (current: ${app.getVersion()})`);
  emit('available', {
    version: info.version,
    releaseDate: info.releaseDate,
    releaseNotes: info.releaseNotes,
  });
});

autoUpdater.on('update-not-available', (info) => {
  log(`up to date: ${info && info.version}`);
  emit('up-to-date', { version: info && info.version });
});

autoUpdater.on('download-progress', (progress) => {
  // progress: { percent, bytesPerSecond, transferred, total }
  emit('download-progress', {
    percent: Math.round(progress.percent || 0),
    bytesPerSecond: progress.bytesPerSecond,
    transferred: progress.transferred,
    total: progress.total,
  });
});

autoUpdater.on('update-downloaded', (info) => {
  log(`update downloaded: ${info.version} — ready to install`);
  lastDownloadedVersion = info.version;
  emit('downloaded', {
    version: info.version,
    releaseNotes: info.releaseNotes,
  });
});

autoUpdater.on('error', (err) => {
  // Errores comunes:
  //   - No internet
  //   - GitHub rate limit
  //   - Repo privado sin token
  //   - Latest.yml mal formado
  // Los logueamos pero NO crasheamos la app — el update es una feature, no
  // debe romper Ashley si falla.
  log(`error: ${err && err.message}`);
  emit('error', { message: err && err.message });
});

// ─── IPC: permite a la UI disparar acciones manuales ──────────────────────

ipcMain.handle('ashley-update:check-now', async () => {
  log('manual check requested from UI');
  try {
    const result = await autoUpdater.checkForUpdates();
    return { ok: true, version: result && result.updateInfo && result.updateInfo.version };
  } catch (e) {
    return { ok: false, error: e.message };
  }
});

ipcMain.handle('ashley-update:install-now', async () => {
  log('install requested from UI');
  if (!lastDownloadedVersion) {
    return { ok: false, error: 'No update downloaded yet' };
  }
  // quitAndInstall cierra Ashley, corre el instalador del update, y relanza.
  // El segundo parametro (isForceRunAfter) garantiza que Ashley reabra
  // sola tras el update.
  setImmediate(() => autoUpdater.quitAndInstall(false, true));
  return { ok: true };
});

ipcMain.handle('ashley-update:get-version', () => {
  return app.getVersion();
});

// ─── Setup publico ────────────────────────────────────────────────────────

/**
 * Inicializa el sistema de auto-updates. Llamar UNA VEZ despues de que la
 * ventana principal este creada y lista.
 *
 * @param {BrowserWindow} mainWindow — ventana principal a la que notificar
 * @param {Object} opts
 * @param {boolean} opts.isDev — si true, el updater se desactiva completo
 */
function setupAutoUpdater(mainWindow, opts = {}) {
  mainWindowRef = mainWindow;

  if (opts.isDev) {
    log('DEV mode — auto-updater disabled');
    return;
  }

  // electron-updater necesita que el proceso este empaquetado (despues
  // de un electron-builder). En un run "electron ." normal, app.isPackaged
  // es false y esto falla silencioso.
  if (!app.isPackaged) {
    log('app not packaged — auto-updater disabled (this is normal in dev)');
    return;
  }

  log(`current version: ${app.getVersion()}`);
  log(`check interval: ${CHECK_INTERVAL_MS / 1000 / 60} min`);

  // Primera verificacion tras INITIAL_DELAY_MS (no bloquea el arranque)
  setTimeout(() => {
    autoUpdater.checkForUpdates().catch((e) => {
      log(`initial check failed (expected on first run if offline): ${e.message}`);
    });
  }, INITIAL_DELAY_MS);

  // Re-chequeos periodicos
  checkTimer = setInterval(() => {
    autoUpdater.checkForUpdates().catch((e) => {
      log(`periodic check failed: ${e.message}`);
    });
  }, CHECK_INTERVAL_MS);
}

function stopAutoUpdater() {
  if (checkTimer) {
    clearInterval(checkTimer);
    checkTimer = null;
  }
}

module.exports = { setupAutoUpdater, stopAutoUpdater };
