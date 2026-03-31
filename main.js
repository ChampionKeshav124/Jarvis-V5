// ═══════════════════════════════════════════════════════════════
//  JARVIS V5 — Electron Main Process
//  BYTEFORGE SYSTEM
//  Manages window lifecycle, Python IPC bridge, and system stats
// ═══════════════════════════════════════════════════════════════

const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn, execSync } = require('child_process');
const os = require('os');

// Show Warning if not elevated (runs once on app ready)
app.whenReady().then(() => {
  if (!isElevated) {
    dialog.showMessageBox({
      type: 'warning',
      title: 'JARVIS: High-Level Elevation Required',
      message: 'Administrative Access is Limited.',
      detail: 'To physically control applications like Steam, JARVIS needs full Administrative Authority. \n\nTACTICAL CHECKLIST:\n1. Close JARVIS and VS Code/Terminal.\n2. Search Start Menu for "PowerShell" or "VS Code".\n3. Right-click it & select "Run as Administrator".\n4. Type "npm run dev" to reboot with full power.',
      buttons: ['I Understand (Continue User-Mode)', 'Exit to restart correctly'],
      defaultId: 0
    }).then(result => {
      if (result.response === 1) app.quit();
    });
  }
});

let mainWindow;

// ── Window Creation ─────────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1000,
    height: 720,
    minWidth: 820,
    minHeight: 620,
    frame: false,
    transparent: false,
    backgroundColor: '#06060a',
    title: 'JARVIS V5',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      devTools: true // Enable for troubleshooting
    },
    // Frameless + rounded corners usually need some margin or specific CSS
  });

  // Handle Permissions for Microphone
  const { session, globalShortcut } = require('electron');

  // Register Global Hotkey
  const ret = globalShortcut.register('Alt+Space', () => {
    console.log('Alt+Space is pressed');
    mainWindow.webContents.send('wake-jarvis');
    mainWindow.show();
    mainWindow.focus();
  });

  if (!ret) { console.log('shortcut registration failed'); }

  // Spawn Native Windows Speech Listener (V4.3)
  const { spawn } = require('child_process');
  const ps = spawn('powershell.exe', ['-ExecutionPolicy', 'Bypass', '-File', path.join(__dirname, 'speech_listener.ps1')]);

  ps.stdout.on('data', (data) => {
    const output = data.toString();
    console.log(`PS-STDOUT: ${output}`);
    if (output.includes('WAKE_DETECTED')) {
      mainWindow.webContents.send('wake-jarvis');
      mainWindow.show();
      mainWindow.focus();
    }
  });

  ps.stderr.on('data', (data) => console.log(`PS-STDERR: ${data}`));

  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    if (permission === 'media') {
      callback(true); // Always allow microphone for JARVIS
    } else {
      callback(false);
    }
  });

  // Bypass autoplay restrictions
  app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');

  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));
  mainWindow.on('closed', () => { mainWindow = null; });
}

// ── Python Bridge ───────────────────────────────────────────
// Spawns python/jarvis.py per command and returns JSON response
ipcMain.handle('send-command', async (_event, payload) => {
  return new Promise((resolve) => {
    const scriptPath = path.join(__dirname, 'python', 'jarvis.py');
    const { text, voice } = payload;
    
    let args = [scriptPath, text];
    if (voice) args.push('--voice');

    const proc = spawn('python', args, {
      cwd: path.join(__dirname, 'python'),
    });

    let stdout = '';
    let stderr = '';

    proc.stdout.on('data', (d) => { stdout += d.toString(); });
    proc.stderr.on('data', (d) => { stderr += d.toString(); });

    proc.on('close', (code) => {
      if (stderr) console.error('[Python stderr]', stderr);
      try {
        resolve(JSON.parse(stdout.trim()));
      } catch {
        resolve({
          response: stdout.trim() || 'I encountered an internal processing error.',
          action: null,
        });
      }
    });

    proc.on('error', (err) => {
      console.error('[Spawn Error]', err.message);
      resolve({
        response: 'Failed to reach AI core. Ensure Python is installed and accessible.',
        action: null,
      });
    });

    // 60-second timeout (V5.4.1)
    // Provides enough buffer for Gemini 2.5 Reflection and ElevenLabs High-Quality audio.
    setTimeout(() => {
      proc.kill();
      resolve({ response: 'Request timed out. AI core unresponsive.', action: null });
    }, 60000);
  });
});

// ── Real System Stats ───────────────────────────────────────
// Returns actual CPU and RAM usage from the OS
ipcMain.handle('get-system-stats', async () => {
  const totalMem = os.totalmem();
  const freeMem = os.freemem();
  const ramPercent = Math.round(((totalMem - freeMem) / totalMem) * 100);

  // CPU usage: compare idle vs total over a 500ms sample
  const cpuPercent = await new Promise((resolve) => {
    const cpus1 = os.cpus();
    setTimeout(() => {
      const cpus2 = os.cpus();
      let idleDiff = 0, totalDiff = 0;
      for (let i = 0; i < cpus2.length; i++) {
        const t1 = cpus1[i].times, t2 = cpus2[i].times;
        const total1 = t1.user + t1.nice + t1.sys + t1.idle + t1.irq;
        const total2 = t2.user + t2.nice + t2.sys + t2.idle + t2.irq;
        idleDiff += t2.idle - t1.idle;
        totalDiff += total2 - total1;
      }
      resolve(totalDiff === 0 ? 0 : Math.round(100 - (idleDiff / totalDiff) * 100));
    }, 500);
  });

  return { cpu: cpuPercent, ram: ramPercent };
});

// ── Config Provider ─────────────────────────────────────────
ipcMain.handle('get-config', async () => {
  try {
    const configPath = path.join(__dirname, 'config.py');
    const fs = require('fs');
    const content = fs.readFileSync(configPath, 'utf8');
    
    // Simple regex to extract WAKE_WORDS list
    const wakeMatch = content.match(/WAKE_WORDS\s*=\s*\[(.*?)\]/s);
    let wakeWords = ["jarvis wake up", "jarvis uth jao", "wake up daddy's home"];
    if (wakeMatch) {
      wakeWords = wakeMatch[1].split(',').map(s => s.trim().replace(/['"]/g, ''));
    }
    
    return { wakeWords };
  } catch (err) {
    return { wakeWords: ["jarvis wake up", "jarvis uth jao", "wake up daddy's home"] };
  }
});

// ── Window Controls (frameless) ─────────────────────────────
ipcMain.on('win-minimize', () => mainWindow?.minimize());
ipcMain.on('win-maximize', () => {
  if (mainWindow) mainWindow.isMaximized() ? mainWindow.unmaximize() : mainWindow.maximize();
});
ipcMain.on('win-close', () => mainWindow?.close());
ipcMain.on('open-mic-settings', () => {
    require('child_process').exec('start ms-settings:privacy-microphone');
});

// ── App Lifecycle ───────────────────────────────────────────
app.whenReady().then(createWindow);
app.on('window-all-closed', () => app.quit());
app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
