"""Offline configuration and routing tests. No cloud or video calls."""
import asyncio
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from PIL import Image

from configuration import Configuration, protect, validate_url
from settings_api import settings_router
from local_chat import chat_events, compatible_messages

class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.config = Configuration(self.root)
        self.assets = self.root / 'assets'
        self.assets.mkdir()
        self.app = FastAPI()
        self.app.include_router(settings_router(self.config, self.assets, lambda: None))
        self.client = TestClient(self.app)

    def tearDown(self):
        self.directory.cleanup()

    def test_credentials_encrypted_hidden_and_retained(self):
        data = self.config.public()
        data['connections'][0]['api_key'] = 'test-private-key-123'
        saved = self.config.save(data)
        self.assertNotIn('test-private-key-123', json.dumps(saved))
        self.assertNotIn('test-private-key-123', self.config.path.read_text(encoding='utf-8'))
        self.assertEqual(Configuration(self.root).connection('bailian')['api_key'], 'test-private-key-123')
        self.config.save(saved)
        self.assertEqual(self.config.connection('bailian')['api_key'], 'test-private-key-123')
        data=self.config.public()
        data['connections'][0]['clear_key']=True
        self.config.save(data)
        self.assertEqual(self.config.connection('bailian')['api_key'],'')

    def test_local_route_and_revision_conflict(self):
        data = self.config.public()
        data['modules']['chat'] = {'connection':'ollama','model':'qwen3.5:4b'}
        self.config.save(data)
        self.assertEqual(self.config.runtime('chat')['provider'], 'ollama')
        with self.assertRaises(HTTPException) as error:
            self.config.save(data)
        self.assertEqual(error.exception.status_code, 409)

    def test_unsupported_tools_not_accepted_as_working(self):
        data = self.config.public()
        data['modules']['image']['connection'] = 'ollama'
        with self.assertRaises(HTTPException):
            self.config.save(data)

    def test_bad_url_rejected(self):
        for address in ('file:///etc/passwd','http://example.com/v1','https://user:password@example.com','https://example.com?key=secret'):
            with self.assertRaises(HTTPException):
                validate_url(address)

    def test_remote_origin_cannot_read_or_write_settings(self):
        self.assertEqual(self.client.get('/api/settings',headers={'Origin':'https://untrusted.example'}).status_code,403)
        self.assertEqual(self.client.put('/api/settings',json=self.config.public(),headers={'Origin':'https://untrusted.example'}).status_code,403)

    def test_uploaded_avatar_validated_and_retained(self):
        stream=io.BytesIO()
        Image.new('RGBA',(8,8),(255,0,0,120)).save(stream,'PNG')
        response=self.client.post('/api/settings/asset?kind=avatar',files={'file':('avatar.png',stream.getvalue(),'image/png')})
        self.assertEqual(response.status_code,200)
        self.assertTrue((self.assets / response.json()['url'].split('/')[-1]).exists())
        self.assertEqual(self.client.post('/api/settings/asset?kind=avatar',files={'file':('fake.png',b'not-an-image')}).status_code,400)
        self.assertEqual(self.client.post('/api/settings/asset?kind=avatar',files={'file':('bad.svg',b'<svg/>')}).status_code,400)
        animated=io.BytesIO()
        frames=[Image.new('RGB',(8,8),color) for color in ('red','blue')]
        frames[0].save(animated,'GIF',save_all=True,append_images=frames[1:],duration=100,loop=0)
        response=self.client.post('/api/settings/asset?kind=avatar',files={'file':('animated.gif',animated.getvalue(),'image/gif')})
        self.assertEqual(response.status_code,200)
        self.assertEqual((self.assets / response.json()['url'].split('/')[-1]).read_bytes(),animated.getvalue())

    def test_invalid_appearance_does_not_overwrite_config(self):
        data=self.config.public()
        data['appearance']['user_avatar']='https://remote.example/avatar.png'
        self.assertEqual(self.client.put('/api/settings',json=data).status_code,400)
        self.assertEqual(self.config.public()['revision'],0)

    def test_local_adapter_stream_and_search_rejection(self):
        route={'provider':'ollama','base_url':'http://localhost:11434','model':'qwen3.5:4b','api_key':''}
        messages=[{'role':'user','content':[{'text':'hello'}]}]
        transport=httpx.MockTransport(lambda request:httpx.Response(200,json={'capabilities':['completion']}) if request.url.path.endswith('/show') else httpx.Response(200,content=b'{"message":{"content":"ok"}}\n{"done":true}\n'))
        original=httpx.AsyncClient
        async def run():
            with patch('local_chat.httpx.AsyncClient', side_effect=lambda *a,**k: original(transport=transport)):
                return [event async for event in chat_events(route,messages,False,False)]
        self.assertEqual(asyncio.run(run())[0]['content'],'ok')
        async def denied():
            return [event async for event in chat_events(route,messages,False,True)]
        with self.assertRaises(HTTPException):
            asyncio.run(denied())

    def test_models_list_does_not_generate(self):
        transport=httpx.MockTransport(lambda request:httpx.Response(200,json={'models':[{'name':'qwen3.5:4b'}]}))
        client=httpx.AsyncClient(transport=transport)
        with patch('settings_api.httpx.AsyncClient',return_value=client):
            response=self.client.post('/api/settings/models',json={'connection':'ollama'})
        self.assertEqual(response.json()['models'],[{'id':'qwen3.5:4b'}])

if __name__=='__main__':
    unittest.main()
