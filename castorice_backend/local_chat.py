"""Ollama and compatible chat adapters; no implicit cloud fallback or hosted tools."""
import base64
import json
import mimetypes
from pathlib import Path

import httpx
from fastapi import HTTPException

def compatible_messages(messages):
    result = []
    for message in messages:
        parts = []
        for part in message.get('content', []):
            if 'text' in part:
                parts.append({'type': 'text', 'text': part['text']})
            elif 'image' in part:
                path = Path(part['image'].removeprefix('file://'))
                mime = mimetypes.guess_type(path.name)[0] or 'image/png'
                parts.append({'type': 'image_url', 'image_url': {'url': f'data:{mime};base64,' + base64.b64encode(path.read_bytes()).decode()}})
            elif 'video' in part:
                raise HTTPException(400, '此聊天连接尚未接入视频附件，请切换百炼或移除视频')
        result.append({'role': message['role'], 'content': parts})
    return result

async def chat_events(connection, messages, thinking, search):
    if search:
        raise HTTPException(400, '此连接尚未接入联网搜索，请关闭联网后发送；不会自动转云端')
    converted = compatible_messages(messages)
    base = connection['base_url']
    ollama = connection['provider'] == 'ollama'
    if ollama:
        try:
            async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
                info = await client.post(base + '/api/show', json={'model': connection['model']})
                info.raise_for_status()
                capabilities = info.json().get('capabilities', [])
        except (httpx.HTTPError, ValueError):
            raise HTTPException(502, '无法读取本地模型，请检查 Ollama 是否运行及模型是否已下载')
        if capabilities and 'completion' not in capabilities:
            raise HTTPException(400, '所选模型不是聊天模型，请勿将嵌入模型用于聊天')
        if any(p['type'] == 'image_url' for m in converted for p in m['content']) and capabilities and 'vision' not in capabilities:
            raise HTTPException(400, '所选本地模型不支持看图，请切换视觉模型或使用 OCR')
        if thinking and capabilities and 'thinking' not in capabilities:
            raise HTTPException(400, '所选本地模型不支持思考模式，请关闭思考后重试')
        native = []
        for message in converted:
            native.append({'role': message['role'], 'content': ''.join(p['text'] for p in message['content'] if p['type'] == 'text'),
                           'images': [p['image_url']['url'].split(',', 1)[1] for p in message['content'] if p['type'] == 'image_url']})
        payload = {'model': connection['model'], 'messages': native, 'stream': True}
        payload['think'] = thinking
        url = base + '/api/chat'
    else:
        payload = {'model': connection['model'], 'messages': converted, 'stream': True}
        url = base + '/chat/completions'
    headers = {'Authorization': 'Bearer ' + connection['api_key']} if connection['api_key'] else {}
    received = False
    async with httpx.AsyncClient(timeout=httpx.Timeout(180, connect=10), trust_env=False) as client:
        async with client.stream('POST', url, json=payload, headers=headers) as response:
            if response.status_code >= 400:
                raise HTTPException(502, f'聊天服务返回 HTTP {response.status_code}，请检查模型名称、输入能力和权限')
            async for line in response.aiter_lines():
                if not line or line.startswith(':'):
                    continue
                if not ollama and not line.startswith('data:'):
                    continue
                raw = line if ollama else line[5:].strip()
                if raw == '[DONE]':
                    break
                data = json.loads(raw)
                if data.get('error'):
                    raise HTTPException(502, '模型执行失败，请检查本地服务日志和模型能力')
                message = data.get('message', {}) if ollama else (data.get('choices') or [{}])[0].get('delta', {})
                text = message.get('content') or ''
                reasoning = (message.get('thinking') or message.get('reasoning_content') or '') if thinking else ''
                received = received or bool(text)
                if text or reasoning:
                    yield {'content': text, 'reasoning': reasoning}
    if not received:
        raise HTTPException(502, '模型未返回有效回答')
