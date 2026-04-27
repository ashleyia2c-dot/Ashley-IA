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
const fs = require('fs');
const path = require('path');

// ─── Configuracion ────────────────────────────────────────────────────────

// Descarga automatica en background — no preguntamos, solo bajamos.
// Ashley es un companion app, la gente quiere "just works" no micro-decisiones.
autoUpdater.autoDownload = true;

// Instalar automaticamente cuando el usuario cierre Ashley normalmente.
// Combinado con el pill "click para aplicar ahora" da la mejor experiencia:
//   - Quieren actualizar YA    → click en el pill → se reinicia y aplica
//   - Estan ocupados           → ignoran el pill → al cerrar Ashley, el
//                                 update se aplica solo en el proximo
//                                 arranque (sin preguntar nada).
// Asi nunca quedan atascados en una version vieja a menos que apaguen la PC
// bruscamente (en cuyo caso el update se aplica en el siguiente arranque).
autoUpdater.autoInstallOnAppQuit = true;

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

// ─── Helpers de disco / cleanup ───────────────────────────────────────────
//
// v0.13.10: añadidos para tapar gaps que vimos en el audit:
//   • Si el download se interrumpe (user mata el proceso, network drop,
//     disco lleno) electron-updater puede dejar archivos parciales que
//     ocupan disco y a veces confunden el siguiente intento.
//   • No teníamos visibilidad del disk space pre-download — si el disco
//     está al límite el update falla en silencio.

function _pendingDir() {
  // electron-updater descarga aquí: %LOCALAPPDATA%\ashley-updater\pending\
  const localAppData = process.env.LOCALAPPDATA || '';
  if (!localAppData) return null;
  return path.join(localAppData, 'ashley-updater', 'pending');
}

function _getFreeDiskSpaceMB(checkPath) {
  // Node 18+ tiene fs.statfsSync — Electron 33 viene con Node 20.
  try {
    const target = checkPath || process.env.LOCALAPPDATA || 'C:\\';
    const stats = fs.statfsSync(target);
    return Math.floor((Number(stats.bavail) * Number(stats.bsize)) / (1024 * 1024));
  } catch (e) {
    return null;
  }
}

function _cleanupPartialDownloads() {
  // Elimina archivos .tmp / .partial / .download que quedaron de un intento
  // anterior fallido. Idempotente — si no hay nada, no hace nada.
  try {
    const dir = _pendingDir();
    if (!dir || !fs.existsSync(dir)) return;
    const files = fs.readdirSync(dir);
    let cleaned = 0;
    for (const f of files) {
      const lower = f.toLowerCase();
      if (lower.endsWith('.tmp') || lower.endsWith('.partial') ||
          lower.endsWith('.download')) {
        try {
          fs.unlinkSync(path.join(dir, f));
          cleaned++;
        } catch (_) { /* file in use, dejarlo */ }
      }
    }
    if (cleaned > 0) {
      log(`cleaned ${cleaned} partial download file(s) in ${dir}`);
    }
  } catch (e) {
    log(`cleanup partial downloads failed: ${e.message}`);
  }
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
  // Disk space check (informativo). Un installer típico de Ashley pesa
  // ~180MB; con margen para el download + extracción pedimos >500MB libres.
  const freeMB = _getFreeDiskSpaceMB();
  if (freeMB !== null) {
    log(`disk free at update target: ${freeMB} MB`);
    if (freeMB < 500) {
      log(`WARNING: disk space low (<500MB), download may fail`);
      emit('disk-space-low', { freeMB });
    }
  }
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
  //   - Disco lleno mid-download (ENOSPC)
  //   - Permisos (EACCES) — raro en per-user install, posible si AV bloquea
  //   - Conexión cortada (ECONNRESET) — deja archivo parcial
  //   - Checksum/signature mismatch — corrupted download
  // Los logueamos pero NO crasheamos la app — el update es una feature, no
  // debe romper Ashley si falla.
  const msg = (err && err.message) || 'unknown';
  log(`error: ${msg}`);

  // v0.13.10: si el error sugiere descarga corrupta o interrumpida,
  // limpiamos los archivos parciales para que el siguiente intento empiece
  // limpio (sin esto, el .tmp de la sesión anterior puede confundir a
  // electron-updater o ocupar disco innecesario).
  const corruptionHints = ['ENOSPC', 'EACCES', 'ECONNRESET',
                            'corrupt', 'integrity', 'sha512', 'checksum'];
  const lower = msg.toLowerCase();
  if (corruptionHints.some(h => lower.includes(h.toLowerCase()))) {
    log(`error suggests partial/corrupt download — cleaning up`);
    _cleanupPartialDownloads();
  }

  emit('error', { message: msg });
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

ipcMain.handle('ashley-update:get-status', () => {
  // Status snapshot que la UI puede consultar para mostrar info del
  // updater (versión, último download, espacio disponible). Útil para
  // un eventual panel de "Actualización" en Settings.
  return {
    version: app.getVersion(),
    lastDownloadedVersion: lastDownloadedVersion,
    freeDiskMB: _getFreeDiskSpaceMB(),
  };
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

  // v0.13.10: cleanup preventivo de archivos parciales de un intento
  // anterior fallido. Si el user mató Ashley mid-download o se quedó sin
  // disco, electron-updater pudo dejar .tmp residuales que confunden el
  // siguiente intento. Empezar limpio.
  _cleanupPartialDownloads();

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
