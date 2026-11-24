const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('castoriceDesktop', {
  info: () => ipcRenderer.invoke('castorice:desktop', 'info'),
  openData: () => ipcRenderer.invoke('castorice:desktop', 'data'),
  openLogs: () => ipcRenderer.invoke('castorice:desktop', 'logs'),
  restart: () => ipcRenderer.invoke('castorice:desktop', 'restart'),
  resetWindow: () => ipcRenderer.invoke('castorice:desktop', 'reset-window'),
});
