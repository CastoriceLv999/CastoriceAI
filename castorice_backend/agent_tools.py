"""Shared Responses API adapter for streaming and complete Agent replies."""
import base64
import json
import mimetypes

from fastapi import HTTPException
from openai import AsyncOpenAI


TOOL_MAP = {
    'search': ['web_search'],
    'web_extract': ['web_search', 'web_extractor'],
    'code': ['code_interpreter'],
    'search_image': ['web_search_image'],
    'image_search': ['image_search'],
    'auto': ['web_search', 'web_extractor', 'code_interpreter', 'web_search_image'],
}


def build_request(req, file_store):
    if req.tool not in TOOL_MAP:
        raise HTTPException(400, '不支持的工具类型')
    images = []
    for fid in req.files:
        meta = file_store.get(fid)
        if not meta or not meta['path'].is_file():
            raise HTTPException(404, '附件不存在，请重新上传')
        if meta['type'] != 'image':
            raise HTTPException(400, 'Agent 附件仅支持图片')
        mime = mimetypes.guess_type(str(meta['path']))[0] or 'image/png'
        images.append({'type': 'input_image', 'image_url':
                       f'data:{mime};base64,' + base64.b64encode(meta['path'].read_bytes()).decode()})
    if req.tool == 'image_search' and not images:
        raise HTTPException(400, '图搜图需要先上传参考图片')
    messages = [dict(m) for m in req.messages if m.get('role') in ('user', 'assistant') and isinstance(m.get('content'), str)]
    if not messages or messages[-1]['role'] != 'user':
        raise HTTPException(400, '请输入用户消息')
    if images:
        messages[-1]['content'] = [{'type': 'input_text', 'text': messages[-1]['content']}, *images]
    tools = list(TOOL_MAP[req.tool])
    if req.tool == 'auto' and images:
        tools.append('image_search')
    return messages, [{'type': tool} for tool in tools]


async def agent_events(req, messages, tools, *, api_key, base_url, model):
    """Yield application events, including upstream failure/empty-stream errors."""
    async with AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=120, max_retries=0) as client:
        received = False
        try:
            stream = await client.responses.create(
                model=model, input=messages, tools=tools, stream=True,
                instructions='你是遐蝶。根据用户需求使用工具，只有实际工具返回后才能声称已执行。使用用户的语言回答。',
                extra_body={'enable_thinking': req.thinking or any(t['type'] == 'code_interpreter' for t in tools)},
            )
            async with stream:
                async for event in stream:
                    data = event.model_dump()
                    kind = data.get('type', '')
                    if kind in ('error', 'response.failed', 'response.incomplete'):
                        response = data.get('response') or {}
                        error = data.get('error') or response.get('error') or response.get('incomplete_details') or data
                        message = error.get('message') or error.get('reason') or json.dumps(error, ensure_ascii=False)
                        yield {'error': message}
                        return
                    if kind == 'response.output_text.delta':
                        if data.get('delta'):
                            received = True
                            yield {'content': data['delta']}
                    elif kind in ('response.reasoning_text.delta', 'response.reasoning_summary_text.delta'):
                        if req.thinking and data.get('delta'):
                            yield {'reasoning': data['delta']}
                    elif kind in ('response.output_item.added', 'response.output_item.done'):
                        item = data.get('item') or {}
                        item_type = item.get('type', '')
                        if item_type.endswith('_call'):
                            yield {'tool_calling': kind.endswith('added'), 'tool_name': item_type.removesuffix('_call')}
                        if kind.endswith('done'):
                            if item.get('status') == 'failed':
                                yield {'error': f"工具 {item_type} 执行失败"}
                                return
                            if item_type in ('web_search_image_call', 'image_search_call') and item.get('output'):
                                output = item['output']
                                results = json.loads(output) if isinstance(output, str) else output
                                images = [{'title': x.get('title', ''), 'url': x['url']} for x in results if isinstance(x, dict) and x.get('url')]
                                if images:
                                    received = True
                                    yield {'images': images[:6]}
                            if item_type == 'code_interpreter_call':
                                yield {'tool_info': item.get('code') or '代码工具执行完成'}
                    elif kind == 'response.completed':
                        response = data.get('response') or {}
                        if response.get('error'):
                            yield {'error': str(response['error'])}
                            return
                        yield {'usage': response.get('usage') or {}}
            if not received:
                yield {'error': '模型未返回有效内容或图片，请检查模型权限和工具配置后重试。'}
        except Exception as exc:
            yield {'error': str(exc)}
