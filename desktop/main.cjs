const { app, BrowserWindow, dialog, shell, ipcMain, screen } = require('electron');
const { spawn, spawnSync } = require('node:child_process');
const net = require('node:net');
const path = require('node:path');
const fs = require('node:fs');
let backend;
let win;
let quitting = false;
const smoke = process.argv.includes('--smoke-test');
app.setPath('userData', path.join(app.getPath('appData'), 'Castorice AI'));
if (smoke) app.setPath('userData', path.resolve(process.env.CASTORICE_SMOKE_DIR || path.join(__dirname, '../.dev-logs/desktop-smoke')));
function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => { const port = server.address().port; server.close(() => resolve(port)); });
  });
}
async function start() {
  const resources = app.isPackaged ? process.resourcesPath : path.resolve(__dirname, '../desktop-build');
  const web = app.isPackaged ? path.join(resources, 'web') : path.resolve(__dirname, '../castorice_vue/dist');
  const data = app.getPath('userData');
  fs.mkdirSync(data, { recursive: true });
  const log = fs.openSync(path.join(data, 'backend.log'), 'a');
  const port = await freePort();
  const root = path.resolve(__dirname, '..');
  const python = ['.venv', '.check-venv'].map(name => path.join(root, name, 'Scripts/python.exe')).find(file => fs.existsSync(file));
  if (!app.isPackaged && !python) throw new Error('开发模式需要 Python 虚拟环境');
  backend = spawn(app.isPackaged ? path.join(resources, 'backend/backend.exe') : python, app.isPackaged ? [String(port)] : [path.join(__dirname, 'backend_entry.py'), String(port)], {
    windowsHide: true, stdio: ['ignore', log, log],
    cwd: root,
    env: { ...process.env, PYTHONPATH: path.join(root, 'castorice_backend'), CASTORICE_DATA_DIR: data, CASTORICE_WEB_DIR: web }
  });
  fs.closeSync(log);
  let failed;
  backend.on('error', error => { failed = error; });
  backend.on('exit', code => { if (!quitting) { failed = new Error(`后台已退出 (${code})，请查看 ${path.join(data, 'backend.log')}`); if (win) { dialog.showErrorBox('后台服务已停止', failed.message); app.quit(); } } });
  const origin = `http://127.0.0.1:${port}`;
  const checkHealth = () => new Promise(resolve => {
    const request = require('node:http').get(origin + '/openapi.json', response => { response.resume(); resolve(response.statusCode === 200); });
    request.on('error', () => resolve(false));
    request.setTimeout(1000, () => { request.destroy(); resolve(false); });
  });
  // Stable UI origin preserves localStorage across launches despite the dynamic backend port.
  const { createFrontendServer } = require('./static-server.cjs');
  const proxy = createFrontendServer(web, origin);
  await new Promise((resolve, reject) => { proxy.once('error', reject); proxy.listen(18573, '127.0.0.1', resolve); });
  app.on('before-quit', () => proxy.close());
  const uiOrigin = 'http://127.0.0.1:18573';
  let bounds = { width: 1280, height: 900 };
  const windowStatePath = path.join(data, 'window.json');
  try {
    const stored = JSON.parse(fs.readFileSync(windowStatePath, 'utf8'));
    const candidate = stored.bounds;
    if (candidate && ['x','y','width','height'].every(k => Number.isFinite(candidate[k])) && candidate.width >= 700 && candidate.height >= 600 && screen.getAllDisplays().some(display => candidate.x < display.workArea.x + display.workArea.width && candidate.x + candidate.width > display.workArea.x && candidate.y < display.workArea.y + display.workArea.height && candidate.y + candidate.height > display.workArea.y)) bounds = candidate;
  } catch {}
  win = new BrowserWindow({ ...bounds, show: true, backgroundColor: '#130e20', minWidth: 700, minHeight: 600, title: 'Castorice AI', icon: path.join(__dirname, 'assets/icon.ico'), autoHideMenuBar: true, webPreferences: { preload: path.join(__dirname, 'preload.cjs'), nodeIntegration: false, contextIsolation: true, sandbox: true } });
  const allowedSender = event => { if (event.sender !== win?.webContents || new URL(event.senderFrame.url).origin !== uiOrigin) throw new Error('不允许的调用来源'); };
  ipcMain.handle('castorice:desktop', (event, action) => {
    allowedSender(event);
    if (action === 'info') return { version: app.getVersion(), dataDirectory: data };
    if (action === 'data') return shell.openPath(data);
    if (action === 'logs') { shell.showItemInFolder(path.join(data, 'backend.log')); return true; }
    if (action === 'restart') { app.relaunch(); app.quit(); return true; }
    if (action === 'reset-window') { win.setBounds({ width: 1280, height: 900 }); win.center(); return true; }
    throw new Error('不支持的桌面操作');
  });
  win.on('close', () => { try { fs.writeFileSync(windowStatePath, JSON.stringify({ bounds: win.getNormalBounds() })); } catch {} });
  win.webContents.setWindowOpenHandler(({ url }) => { if (/^https?:\/\//.test(url)) shell.openExternal(url); return { action: 'deny' }; });
  win.webContents.on('will-navigate', (event, url) => { if (new URL(url).origin !== uiOrigin) { event.preventDefault(); if (/^https?:\/\//.test(url)) shell.openExternal(url); } });
  await win.loadURL(uiOrigin);
  win.show();
  let ready = false;
  for (let attempt = 0; attempt < 120; attempt++) {
    if (failed) throw failed;
    if (await checkHealth()) { ready = true; break; }
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  if (!ready) throw new Error(`后台启动超时。请检查 ${path.join(data, 'backend.log')}。API 密钥可通过 DASHSCOPE_API_KEY 环境变量或该目录下的 .env 配置。`);
  if (smoke) {
    const result = await win.webContents.executeJavaScript(`({ title: document.title, appMounted: !!document.querySelector('#app')?.children.length, bodyLength: document.body.innerText.length })`);
    fs.writeFileSync(path.join(data, 'smoke.json'), JSON.stringify({ ...result, backendPort: port, passed: result.appMounted && result.bodyLength > 20 }, null, 2));
    const screenshot = await win.webContents.capturePage();
    fs.writeFileSync(path.join(data, 'preview.png'), screenshot.toPNG());
    app.quit();
  }
}
if (!app.requestSingleInstanceLock()) app.quit();
else {
  app.on('second-instance', () => { if (win) { if (win.isMinimized()) win.restore(); win.focus(); } });
  app.whenReady().then(start).catch(error => { quitting = true; if (smoke) { fs.mkdirSync(app.getPath('userData'), { recursive: true }); fs.writeFileSync(path.join(app.getPath('userData'), 'smoke.json'), JSON.stringify({ passed: false, error: error.message })); } else dialog.showErrorBox('Castorice 启动失败', error.message); app.quit(); });
  app.on('before-quit', () => {
    quitting = true;
    if (backend && backend.exitCode === null) {
      if (process.platform === 'win32') spawnSync('taskkill', ['/PID', String(backend.pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore', timeout: 5000 });
      else backend.kill();
    }
  });
  app.on('window-all-closed', () => app.quit());
}
