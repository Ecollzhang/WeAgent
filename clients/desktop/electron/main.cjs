const { app, BrowserWindow, ipcMain } = require('electron')
const path = require('path')
const fs = require('fs')

const CONFIG_FILE = 'config.json'
const APP_NAME = 'WeAgent'
const APP_ICON = fs.existsSync(path.join(__dirname, '..', 'logo.ico'))
  ? path.join(__dirname, '..', 'logo.ico')
  : path.join(__dirname, '..', 'logo.png')

app.setName(APP_NAME)

function configPath() {
  return path.join(app.getPath('userData'), CONFIG_FILE)
}

function readConfig() {
  try {
    return JSON.parse(fs.readFileSync(configPath(), 'utf8'))
  } catch (error) {
    return {}
  }
}

function writeConfig(config) {
  fs.mkdirSync(app.getPath('userData'), { recursive: true })
  fs.writeFileSync(configPath(), JSON.stringify(config || {}, null, 2), 'utf8')
  return config
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1180,
    height: 760,
    minWidth: 920,
    minHeight: 620,
    title: APP_NAME,
    icon: APP_ICON,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, 'preload.cjs'),
    },
  })

  const devUrl = process.env.VITE_DEV_SERVER_URL
  if (devUrl) {
    win.loadURL(devUrl)
  } else {
    win.loadFile(path.join(__dirname, '..', 'dist', 'index.html'))
  }
}

ipcMain.handle('weagent-config:get', () => readConfig())
ipcMain.handle('weagent-config:set', (event, patch) => {
  const next = { ...readConfig(), ...(patch || {}) }
  return writeConfig(next)
})

app.whenReady().then(() => {
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
