const { app, BrowserWindow, Tray, Menu, ipcMain, nativeImage, dialog } = require('electron');
const path = require('path');
const cp = require('child_process');
let tray = null;
let win = null;

function createWindow() {
    win = new BrowserWindow({
        width: 440,
        height: 640,
        icon: path.join(__dirname, 'media', 'jemai_chip_icon.png'),
        webPreferences: { nodeIntegration: true, contextIsolation: false }
    });
    win.loadFile('index.html');
}

app.whenReady().then(() => {
    createWindow();

    // Tray Icon
    const trayIcon = nativeImage.createFromPath(path.join(__dirname, 'media', 'jemai_chip_icon.png'));
    tray = new Tray(trayIcon.resize({ width: 20, height: 20 }));
    const trayMenu = Menu.buildFromTemplate([
        { label: 'Show JEMAI', click: () => { win.show(); } },
        { label: 'View Logs', click: () => { win.webContents.send('show-logs'); win.show(); } },
        { label: 'Toggle Voice', click: () => { win.webContents.send('toggle-voice'); } },
        { type: 'separator' },
        { label: 'Quit', click: () => { app.quit(); } }
    ]);
    tray.setToolTip('JEMAI AGI OS');
    tray.setContextMenu(trayMenu);

    // Start backend Python service (always-on, restarts on crash)
    function startJemaiBackend() {
        const pythonPath = process.platform === 'win32' ? 'python' : 'python3';
        const backend = cp.spawn(pythonPath, [path.join(__dirname, 'jemai_core.py')], { detached: true });
        backend.on('exit', (code) => { setTimeout(startJemaiBackend, 1000); }); // restart if crash
    }
    startJemaiBackend();
});

ipcMain.handle('pick-log', async () => {
    const res = await dialog.showOpenDialog({ filters: [{ name: 'Logs', extensions: ['log', 'txt'] }], properties: ['openFile'] });
    return res.filePaths[0];
});
