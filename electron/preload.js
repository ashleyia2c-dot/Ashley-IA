// Preload script para onboarding.html
// Expone un API limitado al renderer via contextBridge (no expone todo el Node).

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('ashleyAPI', {
  submit: (data) => ipcRenderer.send('onboarding-submit', data),
  cancel: () => ipcRenderer.send('onboarding-cancel'),
});
