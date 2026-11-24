const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const types = { '.html':'text/html; charset=utf-8', '.js':'text/javascript; charset=utf-8', '.css':'text/css; charset=utf-8', '.json':'application/json', '.png':'image/png', '.jpg':'image/jpeg', '.jpeg':'image/jpeg', '.gif':'image/gif', '.webp':'image/webp', '.ico':'image/x-icon', '.svg':'image/svg+xml', '.mp4':'video/mp4', '.webm':'video/webm', '.mp3':'audio/mpeg', '.woff2':'font/woff2', '.woff':'font/woff' };
function createFrontendServer(directory, backendOrigin) {
  const root = path.resolve(directory);
  return http.createServer((req, res) => {
    let pathname;
    try { pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname); } catch { res.writeHead(400); res.end(); return; }
    if (['/api/', '/uploads/', '/settings-assets/'].some(prefix => pathname.startsWith(prefix))) {
      const upstream = http.request(backendOrigin + req.url, { method: req.method, headers: req.headers }, response => { res.writeHead(response.statusCode, response.headers); response.pipe(res); });
      upstream.on('error', () => { if (!res.headersSent) res.writeHead(503, { 'Content-Type':'application/json' }); res.end(JSON.stringify({detail:'本地后台正在启动，请稍候'})); });
      req.pipe(upstream);res.on('close',()=>upstream.destroy());return;
    }
    if (!['GET','HEAD'].includes(req.method)) { res.writeHead(405);res.end();return; }
    const file = path.resolve(root, '.' + (pathname === '/' ? '/index.html' : pathname));
    if (!file.startsWith(root + path.sep) || pathname.includes('\0')) { res.writeHead(403);res.end();return; }
    fs.stat(file,(error,stat)=>{
      if(error || !stat.isFile()){res.writeHead(404);res.end();return;}
      let start=0,end=stat.size-1,status=200;
      if(req.headers.range){
        const match=/^bytes=(\d*)-(\d*)$/.exec(req.headers.range);
        if(!match || (!match[1]&&!match[2])){res.writeHead(416,{'Content-Range':`bytes */${stat.size}`});res.end();return;}
        if(!match[1])start=Math.max(0,stat.size-Number(match[2]));
        else {start=Number(match[1]);if(match[2])end=Math.min(end,Number(match[2]));}
        if(start>end || start>=stat.size){res.writeHead(416,{'Content-Range':`bytes */${stat.size}`});res.end();return;}
        status=206;
      }
      const headers={'Content-Type':types[path.extname(file).toLowerCase()]||'application/octet-stream','Content-Length':Math.max(0,end-start+1),'Accept-Ranges':'bytes','Cache-Control':'no-cache'};
      if(status===206)headers['Content-Range']=`bytes ${start}-${end}/${stat.size}`;
      res.writeHead(status,headers);
      if(req.method==='HEAD'||stat.size===0){res.end();return;}
      const stream=fs.createReadStream(file,{start,end});stream.on('error',()=>res.destroy());res.on('close',()=>stream.destroy());stream.pipe(res);
    });
  });
}
module.exports = { createFrontendServer };
