"""Local application configuration. Credentials never appear in public responses."""
import base64
import copy
import ctypes
import json
import os
import threading
import re
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import HTTPException

MODULES = ('chat', 'vision', 'document', 'embedding', 'agent', 'search_image', 'image_search', 'image', 'video')
DEFAULT_MODELS = dict(zip(MODULES, ('qwen3.8-max', 'qwen3.8-max', 'qwen3.8-max', 'text-embedding-v3', 'qwen3.8-max', 'qwen3.8-max', 'qwen3.8-max', 'qwen-image-3.0', 'wan3.0-video-prime')))

def protect(value, decrypt=False):
    if not value:
        return ''
    if os.name != 'nt':
        if decrypt:
            return base64.b64decode(value).decode()
        return base64.b64encode(value.encode()).decode()
    from ctypes import wintypes
    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]
    raw = base64.b64decode(value) if decrypt else value.encode()
    buffer = ctypes.create_string_buffer(raw)
    source = Blob(len(raw), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output = Blob()
    function = ctypes.windll.crypt32.CryptUnprotectData if decrypt else ctypes.windll.crypt32.CryptProtectData
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise RuntimeError('无法处理当前 Windows 用户的密钥，请重新填写 API Key')
    try:
        result = ctypes.string_at(output.data, output.size)
        return result.decode() if decrypt else base64.b64encode(result).decode()
    finally:
        ctypes.windll.kernel32.LocalFree(output.data)

def validate_url(value):
    parsed = urlsplit(value)
    if parsed.username or parsed.password or parsed.query or parsed.fragment or not parsed.hostname:
        raise HTTPException(400, '服务地址不能包含密钥、查询参数或登录信息')
    if parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname in ('127.0.0.1', 'localhost', '::1')):
        raise HTTPException(400, '云端地址必须使用 HTTPS；HTTP 仅用于本机服务')
    return value.rstrip('/')

class Configuration:
    def __init__(self, directory):
        self.path = Path(directory) / 'settings.json'
        self.lock = threading.RLock()
        self.value = {'revision': 0, 'connections': [
            {'id': 'bailian', 'name': '阿里云百炼', 'provider': 'dashscope', 'base_url': os.getenv('RESPONSES_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1'), 'secret': '', 'use_environment_key': True},
            {'id': 'ollama', 'name': '本机 Ollama', 'provider': 'ollama', 'base_url': 'http://127.0.0.1:11434', 'secret': ''}],
            'modules': {name: {'connection': 'bailian', 'model': os.getenv({'chat': 'CHAT_MODEL', 'agent': 'AGENT_MODEL', 'image': 'IMAGE_MODEL', 'video': 'VIDEO_MODEL'}.get(name, ''), model)} for name, model in DEFAULT_MODELS.items()},
            'appearance': {'user_name': '你', 'assistant_name': 'Castorice', 'user_avatar': '', 'assistant_avatar': '', 'avatar_shape': 'circle',
                           'background_mode': 'default', 'background_asset': '', 'background_color': '#100b25', 'background_fit': 'cover', 'background_dim': 0, 'background_blur': 0,
                           'pause_hidden': True, 'reduce_motion': False, 'font_size': 16, 'music_enabled': True, 'music_volume': 0.45,
                           'send_key': 'enter', 'system_prompt': ''}}
        if self.path.exists():
            try:
                loaded = json.loads(self.path.read_text(encoding='utf-8'))
                self.value.update({key: loaded[key] for key in ('revision', 'connections', 'modules') if key in loaded})
                self.value['appearance'].update(loaded.get('appearance', {}))
            except (ValueError, OSError):
                raise RuntimeError('设置文件无法读取，请先备份并检查 settings.json')

    def public(self):
        with self.lock:
            result = copy.deepcopy(self.value)
        for connection in result['connections']:
            connection.setdefault('use_environment_key', connection['id'] == 'bailian')
            connection['has_key'] = bool(connection.pop('secret', '') or connection['id'] == 'bailian' and connection.get('use_environment_key', True) and os.getenv('DASHSCOPE_API_KEY'))
        result['credential_storage'] = 'Windows 用户加密' if os.name == 'nt' else '本地文件（仅当前用户权限）'
        return result

    def connection(self, identity):
        with self.lock:
            item = next((copy.deepcopy(c) for c in self.value['connections'] if c['id'] == identity), None)
        if not item:
            raise HTTPException(400, '连接不存在，请重新选择')
        item['api_key'] = protect(item.pop('secret', ''), True) or (os.getenv('DASHSCOPE_API_KEY', '') if identity == 'bailian' and item.get('use_environment_key', True) else '')
        return item

    def runtime(self, module):
        with self.lock:
            route = dict(self.value['modules'][module])
        return {**self.connection(route['connection']), 'model': route['model']}

    def save(self, incoming):
        with self.lock:
            if incoming.get('revision') != self.value['revision']:
                raise HTTPException(409, '设置已在其他窗口更新，请重新载入后编辑')
            old = {c['id']: c for c in self.value['connections']}
            connections = []
            seen = set()
            for item in incoming.get('connections', []):
                identity = str(item.get('id', ''))
                if not identity or len(identity) > 80 or identity in seen:
                    raise HTTPException(400, '连接标识无效或重复')
                seen.add(identity)
                provider = item.get('provider')
                if provider not in ('dashscope', 'ollama', 'compatible'):
                    raise HTTPException(400, '不支持的连接类型')
                if provider == 'dashscope' and item.get('base_url', '').rstrip('/') != 'https://dashscope.aliyuncs.com/compatible-mode/v1':
                    raise HTTPException(400, '当前百炼原生功能仅适配中国站；其他地址请使用兼容连接进行聊天')
                secret = old.get(identity, {}).get('secret', '')
                use_environment_key = bool(item.get('use_environment_key', old.get(identity, {}).get('use_environment_key', identity == 'bailian')))
                if item.get('clear_key'):
                    secret = ''
                    use_environment_key = False
                elif item.get('api_key'):
                    if len(item['api_key']) > 4096:
                        raise HTTPException(400, '密钥过长')
                    secret = protect(item['api_key'].strip())
                connections.append({'id': identity, 'name': str(item.get('name', '')).strip()[:80] or identity,
                                    'provider': provider, 'base_url': validate_url(str(item.get('base_url', ''))), 'secret': secret, 'use_environment_key': use_environment_key})
            modules = incoming.get('modules', {})
            for name in MODULES:
                route = modules.get(name, {})
                if route.get('connection') not in seen or not isinstance(route.get('model'), str) or not route['model'].strip() or len(route['model']) > 160:
                    raise HTTPException(400, f'{name} 的连接或模型无效')
                provider = next(c['provider'] for c in connections if c['id'] == route['connection'])
                if name in ('agent', 'search_image', 'image_search', 'image', 'video') and provider != 'dashscope':
                    raise HTTPException(400, f'{name} 当前仅接入百炼工具或生成服务；不能仅改模型名称代替接入')
            appearance = dict(self.value['appearance'])
            appearance.update({k: v for k, v in incoming.get('appearance', {}).items() if k in appearance})
            for key, minimum, maximum in [('background_dim', 0, .85), ('background_blur', 0, 20), ('font_size', 12, 24), ('music_volume', 0, 1)]:
                if type(appearance[key]) not in (int, float) or not minimum <= appearance[key] <= maximum:
                    raise HTTPException(400, '外观参数超出范围')
            for key in ('pause_hidden', 'reduce_motion', 'music_enabled'):
                if type(appearance[key]) is not bool:
                    raise HTTPException(400, '外观开关值无效')
            for key, choices in {'background_mode': ('default', 'video', 'image', 'color', 'gradient'), 'background_fit': ('cover', 'contain'), 'avatar_shape': ('circle', 'rounded'), 'send_key': ('enter', 'ctrl-enter')}.items():
                if appearance[key] not in choices:
                    raise HTTPException(400, '不支持的显示选项')
            for key in ('user_avatar', 'assistant_avatar', 'background_asset'):
                value = appearance[key]
                if not isinstance(value, str) or value and (not value.startswith('/settings-assets/') or '..' in value or '/' in value[len('/settings-assets/'):]):
                    raise HTTPException(400, '媒体文件路径无效')
            for key in ('user_name', 'assistant_name', 'system_prompt', 'background_color'):
                if not isinstance(appearance[key], str) or len(appearance[key]) > (8000 if key == 'system_prompt' else 100):
                    raise HTTPException(400, '名称或角色设定过长')
            if not re.fullmatch(r'#[0-9a-fA-F]{6}', appearance['background_color']):
                raise HTTPException(400, '背景颜色格式无效')
            candidate = {'revision': self.value['revision'] + 1, 'connections': connections, 'modules': {k: {'connection': modules[k]['connection'], 'model': modules[k]['model'].strip()} for k in MODULES}, 'appearance': appearance}
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix('.tmp')
            temporary.write_text(json.dumps(candidate, ensure_ascii=False, indent=2), encoding='utf-8')
            if os.name != 'nt':
                temporary.chmod(0o600)
            temporary.replace(self.path)
            self.value = candidate
        return self.public()
