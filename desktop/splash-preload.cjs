const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('startup', {
  onStatus: callback => ipcRenderer.on('castorice:startup-status', (_event, value) => callback(value)),
});
