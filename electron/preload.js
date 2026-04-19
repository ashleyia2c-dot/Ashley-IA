// Preload script para onboarding.html Y la ventana principal de Ashley.
// Expone un API limitado al renderer via contextBridge (no expone todo el Node).

const { contextBridge, ipcRenderer } = require('electron');

// ─── API de onboarding (sólo usado por onboarding.html) ───────────────────
contextBridge.exposeInMainWorld('ashleyAPI', {
  submit: (data) => ipcRenderer.send('onboarding-submit', data),
  cancel: () => ipcRenderer.send('onboarding-cancel'),
});

// ─── API del auto-updater (usado por la ventana principal) ────────────────
//
// La ventana principal es un HTML servido por Reflex desde 127.0.0.1:17300.
// Como lo cargamos en Electron, tiene acceso a este preload y por tanto a
// `window.ashleyUpdate`. El frontend (assets/ashley_fx.js) se suscribe a
// los eventos y muestra el pill "Update disponible".
//
// Eventos que emite el main process:
//   - ashley-update:checking           → empezó a buscar updates
//   - ashley-update:available          → encontró uno nuevo
//   - ashley-update:up-to-date         → no hay nada nuevo
//   - ashley-update:download-progress  → {percent, bytesPerSecond, ...}
//   - ashley-update:downloaded         → update listo para instalar
//   - ashley-update:error              → algo falló (no crashea la app)

const UPDATE_EVENTS = [
  'checking', 'available', 'up-to-date',
  'download-progress', 'downloaded', 'error',
];

// ─── API de notificaciones (usado por ashley_fx.js) ───────────────────────
// ashley_fx.js dispara notificaciones Windows nativas cuando Ashley escribe
// y la ventana no está focuseada. Al hacer click en la notif, llama a
// focusWindow() para traer Ashley al frente. Lo hace el main process porque
// el renderer no tiene permisos para restaurar la propia ventana.
contextBridge.exposeInMainWorld('ashleyNotif', {
  focusWindow: () => ipcRenderer.send('notif-focus-window'),
});

contextBridge.exposeInMainWorld('ashleyUpdate', {
  // Suscribir un callback a un evento del updater.
  // Devuelve una función para cancelar la suscripción.
  on: (event, callback) => {
    if (!UPDATE_EVENTS.includes(event)) {
      console.warn(`[ashleyUpdate] evento desconocido: ${event}`);
      return () => {};
    }
    const channel = `ashley-update:${event}`;
    const handler = (_e, payload) => {
      try { callback(payload); } catch (err) { console.error('[ashleyUpdate] handler error:', err); }
    };
    ipcRenderer.on(channel, handler);
    return () => ipcRenderer.removeListener(channel, handler);
  },

  // Forzar un chequeo manual (ej. botón "Buscar actualizaciones" en Settings).
  checkNow: () => ipcRenderer.invoke('ashley-update:check-now'),

  // Instalar el update descargado y relanzar Ashley.
  installNow: () => ipcRenderer.invoke('ashley-update:install-now'),

  // Versión actual de Ashley (del package.json).
  getVersion: () => ipcRenderer.invoke('ashley-update:get-version'),
});
