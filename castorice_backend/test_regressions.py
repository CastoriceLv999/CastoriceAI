"""Offline regression tests. All model calls are mocked; no video requests are sent."""
import asyncio
import json
import tempfile
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
import main
from configuration import Configuration
from agent_tools import build_request, agent_events


class Regressions(unittest.TestCase):
    def setUp(self):
        self.settings_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.settings_directory.cleanup)
        self.environment = patch.dict(os.environ, {'DASHSCOPE_API_KEY': 'offline-test-key'})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.settings_patch = patch.object(main, 'configuration', Configuration(Path(self.settings_directory.name)))
        self.settings_patch.start()
        self.addCleanup(self.settings_patch.stop)

    def test_stream_error_is_valid_sse(self):
        async def collect():
            return [x async for x in main.dashscope_stream_adapter(iter([
                {'status_code': 429, 'message': 'quota "exhausted"\nretry'}]))]
        events = asyncio.run(collect())
        self.assertTrue(events[0].startswith('data: '))
        self.assertIn('quota', json.loads(events[0][6:])['error'])

    def test_stream_empty_content_is_not_brackets(self):
        item = SimpleNamespace(status_code=200, output=SimpleNamespace(choices=[{'message': {'content': []}}]))
        async def collect():
            return [x async for x in main.dashscope_stream_adapter(iter([item]))]
        self.assertEqual(asyncio.run(collect()), ['data: [DONE]\n\n'])

    def test_upload_survives_store_reload(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            root = Path(folder)
            with patch.object(main, 'UPLOAD_DIR', root), patch.object(main, 'FILE_INDEX', root / 'index.json'), patch.object(main, 'file_store', {}):
                response = TestClient(main.app).post('/api/upload', files={'file': ('test.txt', b'sample')})
                self.assertEqual(response.status_code, 200)
                meta = main.load_file_store()[response.json()['file_id']]
                self.assertEqual(meta['filename'], 'test.txt')
                self.assertEqual(meta['path'].read_text(), 'sample')

    def test_ocr_mode_uses_text_not_image(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            path = Path(folder) / 'test.png'
            path.touch()
            with patch.object(main, 'file_store', {'img': {'path': path, 'type': 'image'}}), patch.object(main, 'ocr_image', return_value='CASTORICE 742'):
                req = main.ChatRequest(messages=[{'role': 'user', 'content': 'Read this'}], files=['img'], image_mode='ocr')
                messages = asyncio.run(main.build_messages(req))
                self.assertIn('CASTORICE 742', messages[0]['content'][0]['text'])
                self.assertFalse(any('image' in item for msg in messages for item in msg['content']))

    def test_missing_attachment_is_reported(self):
        with patch.object(main, 'file_store', {}):
            response = TestClient(main.app).post('/api/chat', json={'messages': [{'role': 'user', 'content': 'Hi'}], 'files': ['missing']})
            self.assertEqual(response.status_code, 404)

    def test_auto_tools_and_base64_images(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            image = Path(folder) / 'image.png'
            image.write_bytes(b'image')
            req = main.AgentRequest(messages=[{'role': 'user', 'content': 'find similar'}], files=['img'])
            messages, tools = build_request(req, {'img': {'type': 'image', 'path': image}})
            self.assertTrue(messages[-1]['content'][1]['image_url'].startswith('data:image/png;base64,'))
            self.assertIn({'type': 'code_interpreter'}, tools)
            self.assertIn({'type': 'image_search'}, tools)
            self.assertIn({'type': 'web_extractor'}, tools)

    def test_agent_failed_event_is_forwarded(self):
        class Stream:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            def __aiter__(self): return self.events()
            async def events(self):
                yield SimpleNamespace(model_dump=lambda: {'type': 'response.failed', 'response': {'error': {'message': 'quota exhausted'}}})
        class Client:
            def __init__(self, **kwargs): self.responses = self
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            async def create(self, **kwargs): return Stream()
        async def collect():
            return [x async for x in agent_events(main.AgentRequest(messages=[]), [], [], api_key='test', base_url='https://example.invalid', model='test')]
        with patch('agent_tools.AsyncOpenAI', Client):
            self.assertEqual(asyncio.run(collect()), [{'error': 'quota exhausted'}])

    def test_video_arguments_without_network(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            path = Path(folder) / 'test.mp4'
            path.touch()
            response = SimpleNamespace(status_code=200, output=SimpleNamespace(task_id='mock-task'))
            with patch.object(main, 'file_store', {'v': {'type': 'video', 'path': path}}), patch.object(main.VideoSynthesis, 'async_call', return_value=response) as call:
                result = asyncio.run(main.generate_video(main.VideoGenRequest(prompt='Edit this video', files=['v'], resolution='480P', ratio='adaptive', duration=-1, audio=False, prompt_extend=False, watermark=False, seed=42)))
                self.assertEqual(result['task_id'], 'mock-task')
                self.assertEqual(call.call_args.kwargs['model'], 'wan3.0-video-prime')
                self.assertEqual(call.call_args.kwargs['media'][0]['type'], 'reference_video')
                for key, value in {'resolution': '480P', 'ratio': 'adaptive', 'duration': -1, 'audio': False, 'prompt_extend': False, 'watermark': False, 'seed': 42}.items():
                    self.assertEqual(call.call_args.kwargs[key], value)
                self.assertNotIn('negative_prompt', call.call_args.kwargs)

    def test_image_advanced_parameters_without_network(self):
        response = SimpleNamespace(status_code=200, output=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=[{'image': 'https://example.invalid/test.png'}]))]))
        with patch.object(main.MultiModalConversation, 'call', return_value=response) as call:
            result = asyncio.run(main.generate_image(main.ImageGenRequest(prompt='test', n=6, size='768*1152', watermark=True, prompt_extend=False, negative_prompt='blur')))
            self.assertTrue(result['success'])
            for key, value in {'n': 6, 'size': '768*1152', 'watermark': True, 'prompt_extend': False, 'negative_prompt': 'blur'}.items():
                self.assertEqual(call.call_args.kwargs[key], value)

    def test_chat_controls_reach_provider_in_both_response_modes(self):
        response = SimpleNamespace(status_code=200, output=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=[{'text': 'ok'}], reasoning_content='reasoning'))]))
        for stream, thinking, search in [(False, True, False), (True, False, True)]:
            with self.subTest(stream=stream), patch.object(main.MultiModalConversation, 'call', return_value=iter([response]) if stream else response) as call:
                result = TestClient(main.app).post('/api/chat/stream' if stream else '/api/chat', json={'messages': [{'role': 'user', 'content': 'test'}], 'thinking': thinking, 'enable_search': search})
                self.assertEqual(result.status_code, 200)
                self.assertEqual(call.call_args.kwargs['enable_thinking'], thinking)
                self.assertEqual(call.call_args.kwargs['enable_search'], search)
                self.assertEqual(call.call_args.kwargs.get('stream', False), stream)

    def test_video_invalid_duration_does_not_call_provider(self):
        with patch.object(main.VideoSynthesis, 'async_call') as call:
            result = TestClient(main.app).post('/api/generate/video', json={'prompt': 'test', 'duration': 1})
            self.assertEqual(result.status_code, 400)
            call.assert_not_called()


if __name__ == '__main__':
    unittest.main()
