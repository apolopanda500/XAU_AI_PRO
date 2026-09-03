const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

let mainWindow;
let backendProcess;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  // Carrega a URL de desenvolvimento ou o status do backend em produção.
  const startUrl = process.env.ELECTRON_START_URL || 'http://localhost:3001';
  mainWindow.loadURL(startUrl).catch((error) => {
    console.error('[electron] Falha ao carregar a interface:', error.message);
  });

  mainWindow.on('closed', async () => {
    if (backendProcess) {
      backendProcess.kill();
    }
    mainWindow = null;
  });
}

// Inicia backend Node.js junto com Electron
function startBackend() {
  const backendPath = path.join(__dirname, '../backend/server-desktop.cjs');
  backendProcess = spawn('node', [backendPath], {
    stdio: 'inherit'
  });

  backendProcess.on('error', (err) => {
    console.error('Erro ao iniciar backend:', err);
  });
}

app.whenReady().then(() => {
  startBackend();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    if (backendProcess) {
      backendProcess.kill();
    }
    app.quit();
  }
});
