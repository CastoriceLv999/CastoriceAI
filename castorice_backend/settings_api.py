import asyncio
import io
import json
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from PIL import Image

def settings_router(config, assets, invalidate):
    router = APIRouter(prefix='/api/settings')

    def guard(request):
        origin = request.headers.get('origin')
        if origin and urlsplit(origin).hostname not in ('localhost', '127.0.0.1', '::1'):
            raise HTTPException(403, '设置仅允许从本机应用操作')

    @router.get('')
    async def read(request: Request):
        guard(request)
        return config.public()

    @router.put('')
    async def save(request: Request):
        guard(request)
        before = config.runtime('embedding')
        result = await asyncio.to_thread(config.save, await request.json())
        if before != config.runtime('embedding'):
            invalidate()
        return result

    @router.post('/models')
    async def models(request: Request):
        guard(request)
        connection = config.connection((await request.json()).get('connection'))
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
                if connection['provider'] == 'ollama':
                    result = await client.get(connection['base_url'] + '/api/tags')
                    result.raise_for_status()
                    entries = [{'id': item['name']} for item in result.json().get('models', [])]
                else:
                    if not connection['api_key']:
                        raise HTTPException(400, '请先保存 API Key')
                    result = await client.get(connection['base_url'] + '/models', headers={'Authorization': 'Bearer ' + connection['api_key']})
                    result.raise_for_status()
                    entries = [{'id': item['id']} for item in result.json().get('data', [])]
            return {'models': entries, 'latency_ms': round((time.monotonic() - start) * 1000), 'note': '仅验证连接和列表读取，未生成内容；模型实际能力仍需任务验证。'}
        except httpx.HTTPStatusError as exc:
            raise HTTPException(502, f'服务返回 HTTP {exc.response.status_code}，请检查地址、密钥或账号权限')
        except httpx.HTTPError:
            raise HTTPException(502, '连接失败或超时，请检查服务地址与服务运行状态')

    @router.post('/capabilities')
    async def capabilities(request: Request):
        guard(request)
        body = await request.json()
        connection = config.connection(body.get('connection'))
        if connection['provider'] != 'ollama':
            return {'capabilities': [], 'note': '此服务未提供统一能力检测接口，请以模型说明和实测结果为准'}
        try:
            async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
                response = await client.post(connection['base_url'] + '/api/show', json={'model': body.get('model')})
                response.raise_for_status()
                return {'capabilities': response.json().get('capabilities', []), 'note': '来自本地模型声明，尚不代表任务实测通过'}
        except httpx.HTTPError:
            raise HTTPException(502, '无法读取模型能力，请确认模型已下载')

    @router.post('/asset')
    async def asset(request: Request, file: UploadFile = File(...)):
        guard(request)
        kind = request.query_params.get('kind', 'avatar')
        limit = (10 if kind == 'avatar' else 200) * 1024 * 1024
        ext = Path(file.filename or '').suffix.lower()
        if kind not in ('avatar', 'background'):
            raise HTTPException(400, '媒体用途无效')
        allowed = {'.png', '.jpg', '.jpeg', '.webp', '.gif'} | ({'.mp4', '.webm'} if kind == 'background' else set())
        if ext not in allowed:
            raise HTTPException(400, '不支持此文件格式')
        content = bytearray()
        while chunk := await file.read(1024 * 1024):
            content.extend(chunk)
            if len(content) > limit:
                raise HTTPException(413, f'文件超过 {limit // 1048576} MB 限制')
        if ext in ('.mp4', '.webm'):
            if not ((ext == '.mp4' and content[4:8] == b'ftyp') or (ext == '.webm' and content[:4] == b'\x1aE\xdf\xa3')):
                raise HTTPException(400, '视频文件头与格式不一致')
        else:
            try:
                with Image.open(io.BytesIO(content)) as image:
                    if image.format not in ('PNG', 'JPEG', 'WEBP', 'GIF') or image.width * image.height > 40_000_000:
                        raise ValueError()
                    image.verify()
            except Exception:
                raise HTTPException(400, '图片无效或分辨率过大')
        name = uuid.uuid4().hex + ext
        await asyncio.to_thread((assets / name).write_bytes, content)
        return {'url': '/settings-assets/' + name, 'size': len(content), 'type': 'video' if ext in ('.mp4', '.webm') else 'image'}

    @router.get('/diagnostics')
    async def diagnostics(request: Request):
        guard(request)
        return {'status': 'running', 'data_directory': str(config.path.parent),
                'files': sum(1 for p in config.path.parent.rglob('*') if p.is_file()),
                'bytes': sum(p.stat().st_size for p in config.path.parent.rglob('*') if p.is_file()),
                'agent_engine': 'DashScope 云端工具，Codex 未接入', 'cloud_fallback': False}

    @router.post('/clear-index')
    async def clear_index(request: Request):
        guard(request)
        invalidate()
        return {'message': '内存检索索引已清空，下次文档问答自动重建；原文件未删除'}
    return router
