const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('weagentDesktopConfig', {
  get: () => ipcRenderer.invoke('weagent-config:get'),
  set: patch => ipcRenderer.invoke('weagent-config:set', patch),
})
