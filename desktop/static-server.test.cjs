const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const http=require('node:http');
const {createFrontendServer}=require('./static-server.cjs');
test('startup assets load before backend and support media byte ranges',async()=>{
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'castorice-static-'));
  fs.writeFileSync(path.join(directory,'index.html'),'<main>startup</main>');
  fs.writeFileSync(path.join(directory,'启动.mp4'),'0123456789');
  const server=createFrontendServer(directory,'http://127.0.0.1:1');
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const request=(url,headers={})=>new Promise((resolve,reject)=>{
    http.get({host:'127.0.0.1',port:server.address().port,path:url,headers},response=>{
      const chunks=[];response.on('data',chunk=>chunks.push(chunk));response.on('end',()=>resolve({status:response.statusCode,headers:response.headers,body:Buffer.concat(chunks).toString()}));
    }).on('error',reject);
  });
  try{
    assert.equal((await request('/')).status,200);
    const media=await request('/'+encodeURIComponent('启动.mp4'),{Range:'bytes=2-5'});
    assert.equal(media.status,206);assert.equal(media.body,'2345');assert.equal(media.headers['content-range'],'bytes 2-5/10');
    assert.equal((await request('/'+encodeURIComponent('启动.mp4'),{Range:'bytes=20-30'})).status,416);
    assert.equal((await request('/%2e%2e%2fprivate.txt')).status,403);
    assert.equal((await request('/api/settings')).status,503);
  }finally{
    await new Promise(resolve=>server.close(resolve));
    if(path.dirname(directory)===path.resolve(os.tmpdir())&&path.basename(directory).startsWith('castorice-static-'))fs.rmSync(directory,{recursive:true});
  }
});
