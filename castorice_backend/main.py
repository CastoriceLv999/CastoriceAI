from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import os, json, shutil, uuid, asyncio
from pathlib import Path
from dotenv import load_dotenv
from collections import OrderedDict
from typing import Literal
from agent_tools import build_request, agent_events
from configuration import Configuration
from settings_api import settings_router
from local_chat import chat_events
import httpx
from datetime import datetime
import numpy as np
from rank_bm25 import BM25Okapi
import jieba, PyPDF2, pdfplumber, pandas as pd, pytesseract
from docx import Document
from PIL import Image, ImageEnhance, ImageFilter
import dashscope
from dashscope import MultiModalConversation, TextEmbedding, VideoSynthesis

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

jieba.setLogLevel(jieba.logging.INFO)
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
DATA_DIR = Path(os.environ.get("CASTORICE_DATA_DIR", str(BASE_DIR)))
DATA_DIR.mkdir(parents=True, exist_ok=True)
if DATA_DIR != BASE_DIR:
    load_dotenv(DATA_DIR / ".env")

# ========== DashScope 全局配置 ==========
dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"
api_key = os.environ.get("DASHSCOPE_API_KEY", '')
dashscope.api_key = api_key

app = FastAPI(title="Castorice AI（DashScope 原生SDK）")
configuration = Configuration(DATA_DIR)
SETTINGS_ASSETS = DATA_DIR / 'settings-assets'
SETTINGS_ASSETS.mkdir(exist_ok=True)
app.mount('/settings-assets', StaticFiles(directory=SETTINGS_ASSETS), name='settings-assets')
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# ========== 系统提示配置（可外部化到环境变量或配置文件）==========

DEFAULT_SYSTEM_PROMPTS = {
    "zh-CN": {
        "base": "你是崩坏星穹铁道游戏里的角色遐蝶，你栖居在温柔的冥河花海，请根据游戏相应的剧情设定用中文回答用户（开拓者）的问题。",
        "search_auth": "\n\n【授权】你已获得连接星海资讯网络的权限。当开拓者询问时事、新闻或最新信息时，你可以搜索银河网络获取资讯，",
        "rag_prefix": "\n\n【参考资料】\n"
    },
    "en-US": {
        "base": "You are a helpful assistant. Please answer in English.",
        "search_auth": "\n\n[Authorized] You have been granted access to the information network. When asked about current events, news, or latest information, you may search the web and report findings.",
        "rag_prefix": "\n\n[References]\n"
    }
}

# 支持从环境变量覆盖
def get_system_prompt(lang: str, enable_search: bool = False, rag_context: str = ""):
    prompts = DEFAULT_SYSTEM_PROMPTS.get(lang, DEFAULT_SYSTEM_PROMPTS["zh-CN"])
    system_text = prompts["base"]
    custom_prompt = configuration.value['appearance'].get('system_prompt', '').strip()
    if custom_prompt:
        system_text = custom_prompt
    
    if enable_search:
        system_text += prompts["search_auth"]
    
    if rag_context:
        system_text += prompts["rag_prefix"] + rag_context
    
    return system_text

# ======================== 内存安全配置 ========================
MAX_CACHED_FILES = 15
FILE_INDEX = DATA_DIR / "upload_index.json"
def load_file_store():
    if not FILE_INDEX.exists():
        return {}
    records = json.loads(FILE_INDEX.read_text(encoding="utf-8"))
    result = {}
    for fid, meta in records.items():
        path = (UPLOAD_DIR / meta["stored_name"]).resolve()
        if path.parent == UPLOAD_DIR.resolve() and path.is_file():
            result[fid] = {"filename": meta["filename"], "type": meta["type"], "path": path}
    return result

file_store = load_file_store()

def save_file_store():
    records = {fid: {"filename": meta["filename"], "type": meta["type"], "stored_name": meta["path"].name}
               for fid, meta in file_store.items()}
    temporary = FILE_INDEX.with_suffix(".tmp")
    temporary.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    temporary.replace(FILE_INDEX)

rag_cache = OrderedDict()
app.include_router(settings_router(configuration, SETTINGS_ASSETS, rag_cache.clear))
EMBEDDING_MODEL = "text-embedding-v3"
EMBEDDING_DIM = 1024
EMBEDDING_BATCH_SIZE = 25
GENERATION_MODEL = os.getenv("CHAT_MODEL", "qwen3.8-max")
AGENT_MODEL = os.getenv("AGENT_MODEL", "qwen3.8-max")
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "qwen-image-3.0")
VIDEO_MODEL = os.getenv("VIDEO_MODEL", "wan3.0-video-prime")
RESPONSES_BASE_URL = os.getenv("RESPONSES_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

# ==================== 视频生成配置 ====================
video_task_cache = {}
VIDEO_MODEL_MAP = dict.fromkeys(("t2v", "i2v", "r2v", "edit"), VIDEO_MODEL)

# ==================== 通用异步迭代器工具 ====================
async def async_iterate_sync_generator(gen):
    """将同步 generator 转换为异步迭代，每次 next() 都 run_in_executor，不阻塞事件循环"""
    loop = asyncio.get_event_loop()
    
    def _next():
        try:
            return next(gen), False
        except StopIteration:
            return None, True
    
    while True:
        item, done = await loop.run_in_executor(None, _next)
        if done:
            break
        yield item


# ==================== 视频代理转存 ====================
async def proxy_video_url(original_url: str) -> str:
    if not original_url or original_url.startswith("/uploads/"):
        return original_url or ""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(original_url, timeout=120, follow_redirects=True)
            if resp.status_code != 200:
                print(f"[Proxy Warning] 下载失败 {resp.status_code}: {original_url}")
                return original_url
            ext = Path(original_url.split('?')[0]).suffix.lower()
            if ext not in [".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v"]:
                ext = ".mp4"
            local_name = f"video_{uuid.uuid4().hex}{ext}"
            local_path = UPLOAD_DIR / local_name
            with open(local_path, "wb") as f:
                f.write(resp.content)
            print(f"[Proxy OK] 已转存: {original_url} -> /uploads/{local_name}")
            return f"/uploads/{local_name}"
    except Exception as e:
        print(f"[Proxy Error] {type(e).__name__}: {e}")
        return original_url

# ==================== OCR ====================
def preprocess_for_ocr(image_path: Path):
    try:
        pil_img = Image.open(image_path)
        if HAS_CV2:
            img = np.array(pil_img)
            if img.shape[-1] == 4:
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            elif len(img.shape) == 3:
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
            binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            denoised = cv2.fastNlMeansDenoising(binary, None, 30, 7, 21)
            return Image.fromarray(denoised)
        else:
            img = pil_img.convert('L')
            img = ImageEnhance.Contrast(img).enhance(2.0).filter(ImageFilter.SHARPEN)
            img = img.point(lambda x: 0 if x < 128 else 255, '1')
            return img.convert('L')
    except Exception as e:
        print(f"[OCR Preprocess Error] {image_path.name}: {e}")
        return Image.open(image_path).convert('L')

def ocr_image(file_path: Path):
    try:
        img = preprocess_for_ocr(file_path)
        return pytesseract.image_to_string(img, config=r'--oem 3 --psm 6 -l chi_sim+eng').strip()
    except Exception as e:
        print(f"[Tesseract OCR Error] {file_path.name}: {e}")
        return ""

# ==================== 文档解析 ====================
def extract_document_text(file_path: Path, ext: str):
    ext = ext.lower()
    try:
        if ext == ".pdf":
            try:
                text = ""
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        t = page.extract_text()
                        if t:
                            text += t + "\n"
                return text
            except Exception as e:
                print(f"[pdfplumber fallback] {e}")
                return "\n".join(page.extract_text() or "" for page in PyPDF2.PdfReader(file_path).pages)
        elif ext == ".docx":
            return "\n".join(p.text for p in Document(file_path).paragraphs if p.text.strip())
        elif ext == ".csv":
            return pd.read_csv(file_path, encoding="utf-8", low_memory=False).to_string(index=False)
        elif ext in (".xlsx", ".xls"):
            return pd.read_excel(file_path).to_string(index=False)
        else:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
    except Exception as e:
        print(f"[Parse Error] {ext}: {e}")
        return ""

# ==================== 中文语义分割 ====================
class ChineseTextSplitter:
    def __init__(self, chunk_size=512, chunk_overlap=100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.seps = ["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]

    def split_text(self, text: str) -> list[str]:
        if not text:
            return []
        chunks = self._recursive_split(text, self.seps)
        return self._apply_overlap(chunks)

    def _recursive_split(self, text: str, seps: list[str]) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text]
        if not seps:
            step = max(self.chunk_size - self.chunk_overlap, 1)
            return [text[i:i + self.chunk_size] for i in range(0, len(text), step)]
        sep = seps[0]
        next_seps = seps[1:] if len(seps) > 1 else []
        splits = text.split(sep) if sep else list(text)
        final, current = [], ""
        for i, s in enumerate(splits):
            piece = (s + sep) if sep and i < len(splits) - 1 else s
            if len(current) + len(piece) <= self.chunk_size:
                current += piece
            else:
                if current.strip():
                    final.extend(self._recursive_split(current, next_seps))
                if len(piece) > self.chunk_size:
                    final.extend(self._recursive_split(piece, next_seps))
                    current = ""
                else:
                    current = piece
        if current.strip():
            final.extend(self._recursive_split(current, next_seps))
        return final

    def _apply_overlap(self, splits: list[str]) -> list[str]:
        if not splits:
            return []
        merged = [splits[0]]
        for i in range(1, len(splits)):
            prev, curr = merged[-1], splits[i]
            if self.chunk_overlap > 0 and len(prev) > self.chunk_overlap:
                candidate = prev[-self.chunk_overlap:] + curr
                if len(candidate) <= self.chunk_size:
                    merged.append(candidate)
                    continue
            merged.append(curr)
        return [m.strip() for m in merged if len(m.strip()) > 10]

splitter = ChineseTextSplitter()

def _safe_getattr(obj, key, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    try:
        return getattr(obj, key, default)
    except (AttributeError, KeyError):
        return default

def _extract_embeddings_safe(resp):
    try:
        output = _safe_getattr(resp, 'output')
        if output is None:
            print("[Embedding Extract] resp.output is None")
            return None
        if isinstance(output, dict):
            embeddings = output.get('embeddings', [])
            if not isinstance(embeddings, list):
                print(f"[Embedding Extract] output.embeddings is not list: {type(embeddings)}")
                return None
            return np.array([e.get('embedding', [0.0] * EMBEDDING_DIM) for e in embeddings], np.float32)
        embeddings = getattr(output, 'embeddings', None)
        if embeddings is None:
            print("[Embedding Extract] output.embeddings is None")
            return None
        if not isinstance(embeddings, (list, tuple)):
            print(f"[Embedding Extract] output.embeddings is not list: {type(embeddings)}")
            return None
        return np.array([e.embedding for e in embeddings], np.float32)
    except Exception as e:
        print(f"[Embedding Extract Error] {type(e).__name__}: {e}")
        return None

def _get_embeddings_batch(texts: list[str]):
    if not texts:
        return np.array([]).reshape(0, EMBEDDING_DIM)
    try:
        route = configuration.runtime('embedding')
        if route['provider'] != 'dashscope':
            with httpx.Client(timeout=180, trust_env=False) as client:
                if route['provider'] == 'ollama':
                    response = client.post(route['base_url'] + '/api/embed', json={'model': route['model'], 'input': texts})
                    response.raise_for_status()
                    return np.asarray(response.json()['embeddings'], dtype=np.float32)
                response = client.post(route['base_url'] + '/embeddings', json={'model': route['model'], 'input': texts}, headers={'Authorization': 'Bearer ' + route['api_key']})
                response.raise_for_status()
                return np.asarray([x['embedding'] for x in sorted(response.json()['data'], key=lambda x: x['index'])], dtype=np.float32)
        resp = TextEmbedding.call(model=route['model'], input=texts, api_key=route['api_key'])
        status_code = _safe_getattr(resp, 'status_code', 200)
        if status_code != 200:
            code = _safe_getattr(resp, 'code', 'Unknown')
            msg = _safe_getattr(resp, 'message', 'No message')
            print(f"[Embedding API Error] {code}: {msg}")
            return None
        result = _extract_embeddings_safe(resp)
        if result is not None and len(result) == len(texts):
            return result
        print(f"[Embedding Error] 返回维度不匹配: 期望 {len(texts)}, 实际 {len(result) if result is not None else None}")
        return None
    except Exception as e:
        print(f"[Embedding Error] {type(e).__name__}: {e}")
        return None

def _extract_reasoning_safe(message):
    """安全提取 reasoning_content，处理各种异常格式"""
    reasoning_content = _safe_getattr(message, 'reasoning_content', None)
    if not reasoning_content:
        return ''
    
    # 处理列表/数组格式
    if isinstance(reasoning_content, list):
        # 过滤空字符串和 None
        parts = [str(p).strip() for p in reasoning_content if p is not None and str(p).strip()]
        return '\n'.join(parts)
    
    # 处理字符串格式
    result = str(reasoning_content).strip()
    
    # 过滤掉纯占位符格式（如 []、()、{} 等空结构）
    if result in ('[]', '()', '{}', '[ ]', '( )', '{ }', ''):
        return ''
    
    return result

def get_embeddings(texts: list[str]) -> np.ndarray:
    if not texts:
        return np.array([]).reshape(0, EMBEDDING_DIM)
    all_embeddings = []
    for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[i:i + EMBEDDING_BATCH_SIZE]
        batch_vec = _get_embeddings_batch(batch)
        if batch_vec is None:
            raise HTTPException(502, '嵌入模型请求失败，请检查文档检索连接；不会自动转云端')
        all_embeddings.append(batch_vec)
    return np.vstack(all_embeddings)

# ==================== OSS 临时文件上传 ====================
async def upload_to_dashscope_oss(file_path: Path, model_name: str) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://dashscope.aliyuncs.com/api/v1/uploads",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            params={"action": "getPolicy", "model": model_name},
            timeout=30
        )
        if resp.status_code != 200:
            raise HTTPException(502, f"get policy failed: {resp.text}")
        policy_data = resp.json()["data"]
        file_name = file_path.name
        key = f"{policy_data['upload_dir']}/{file_name}"
        async with httpx.AsyncClient() as client:
            with open(file_path, "rb") as f:
                files = {
                    'OSSAccessKeyId': (None, policy_data['oss_access_key_id']),
                    'Signature': (None, policy_data['signature']),
                    'policy': (None, policy_data['policy']),
                    'x-oss-object-acl': (None, policy_data['x_oss_object_acl']),
                    'x-oss-forbid-overwrite': (None, policy_data['x_oss_forbid_overwrite']),
                    'key': (None, key),
                    'success_action_status': (None, '200'),
                    'file': (file_name, f)
                }
                resp = await client.post(policy_data['upload_host'], files=files, timeout=120)
                if resp.status_code != 200:
                    raise HTTPException(502, f"OSS upload failed: {resp.text}")
        return f"oss://{key}"

def cosine_similarity(q_vec: np.ndarray, doc_vecs: np.ndarray) -> np.ndarray:
    if doc_vecs.shape[0] == 0:
        return np.array([])
    dot = np.dot(doc_vecs, q_vec)
    return dot / (np.linalg.norm(q_vec) + 1e-9) / (np.linalg.norm(doc_vecs, axis=1) + 1e-9)

# ==================== RAG ====================
def build_rag_for_file(fid: str):
    signature = json.dumps(configuration.value['modules']['embedding'], sort_keys=True)
    if fid in rag_cache and rag_cache[fid].get('embedding_signature') == signature:
        rag_cache.move_to_end(fid)
        return rag_cache[fid]
    if fid not in file_store:
        return None
    meta = file_store[fid]
    if meta["type"] == "image":
        text = ocr_image(meta["path"])
    else:
        text = extract_document_text(meta["path"], Path(meta["filename"]).suffix)
    chunks = splitter.split_text(text)
    if not chunks:
        return None
    vecs = get_embeddings(chunks)
    tokens = [list(jieba.cut_for_search(c)) for c in chunks]
    bm25 = BM25Okapi(tokens)
    rag = {"chunks": chunks, "vecs": vecs, "bm25": bm25, "fname": meta["filename"], 'embedding_signature': signature}
    rag_cache[fid] = rag
    rag_cache.move_to_end(fid)
    if len(rag_cache) > MAX_CACHED_FILES:
        removed = rag_cache.popitem(last=False)
        print(f"[自动释放内存] 移除文件: {removed[0]}")
    return rag

def retrieve(query: str, fids: list[str], top_k: int = 4):
    rag_list = [build_rag_for_file(fid) for fid in fids if fid in file_store]
    rag_list = [r for r in rag_list if r and r["chunks"]]
    if not rag_list:
        return []
    q_vec = get_embeddings([query])[0]
    q_tokens = list(jieba.cut_for_search(query))
    k = 60
    all_results = []
    for rag in rag_list:
        chunks, vecs, bm25 = rag["chunks"], rag["vecs"], rag["bm25"]
        dense = cosine_similarity(q_vec, vecs)
        sparse = bm25.get_scores(q_tokens)
        dense_order = np.argsort(-dense)
        sparse_order = np.argsort(-sparse)
        dense_rank = {idx: r for r, idx in enumerate(dense_order)}
        sparse_rank = {idx: r for r, idx in enumerate(sparse_order)}
        for i in range(len(chunks)):
            score = 1.0 / (k + dense_rank[i] + 1) + 1.0 / (k + sparse_rank[i] + 1)
            all_results.append((score, rag["fname"], chunks[i]))
    all_results.sort(key=lambda x: x[0], reverse=True)
    return [(s, fn, ch) for s, fn, ch in all_results[:top_k]]

# ==================== 请求结构 ====================
class ChatRequest(BaseModel):
    messages: list
    thinking: bool = False
    files: list[str] = Field(default_factory=list)
    image_mode: Literal["auto", "ocr", "vision"] = "auto"
    enable_search: bool = False  # ← 新增：联网搜索开关
    connection: str | None = None
    model: str | None = None

class AgentRequest(BaseModel):
    messages: list
    tool: str = "auto"
    files: list[str] = Field(default_factory=list)
    thinking: bool = True

# ==================== 构建 DashScope 原生消息 ====================
async def build_messages(req: ChatRequest):
    print(f"[DEBUG] req.files = {req.files}")
    img_fids, text_fids, video_fids = [], [], []
    for fid in req.files:
        if fid not in file_store or not file_store[fid]["path"].is_file():
            raise HTTPException(404, "附件不存在，请重新上传")
        meta = file_store[fid]
        ftype = meta["type"]
        if ftype == "image":
            img_fids.append(fid)
        elif ftype == "video":
            video_fids.append(fid)
        else:
            text_fids.append(fid)
    query = ""
    for m in reversed(req.messages):
        if m.get("role") == "user" and isinstance(m.get("content"), str):
            query = m["content"]
            break
    rag_context = ""
    ocr_context = []
    if req.image_mode == "ocr":
        for fid in img_fids:
            text = await asyncio.to_thread(ocr_image, file_store[fid]["path"])
            if not text:
                raise HTTPException(422, "OCR 未识别到文字，请检查图片或切换视觉理解模式")
            ocr_context.append(text)
        img_fids = []
    if text_fids and query:
        hits = await asyncio.to_thread(retrieve, query, text_fids)
        if hits:
            rag_context = "\n---\n".join([f"【{fn}】{ch}" for _, fn, ch in hits])
    if ocr_context:
        rag_context += "\n【图片文字】\n" + "\n".join(ocr_context)
    ds_messages = []
    lang = "zh-CN"
    for m in req.messages:
        if m.get("role") == "system" and isinstance(m.get("content"), str):
            if "English" in m["content"]:
                lang = "en-US"
                break
    system_text = get_system_prompt(
        lang=lang,
        enable_search=req.enable_search,
        rag_context=rag_context
    )
    ds_messages.append({"role": "system", "content": [{"text": system_text}]})
    user_msgs = [m for m in req.messages if m.get("role") == "user"]
    last_user = user_msgs[-1] if user_msgs else None
    for m in req.messages:
        role = m.get("role")
        if role not in ("user", "assistant"):
            continue
        content = m.get("content", "")
        if not isinstance(content, str):
            content = ""
        if role == "user":
            is_last = (m is last_user)
            if is_last and (img_fids or video_fids):
                content_list = [{"text": content}]
                for fid in img_fids:
                    abs_path = str(file_store[fid]["path"].resolve())
                    content_list.append({"image": f"file://{abs_path}"})
                for fid in video_fids:
                    abs_path = str(file_store[fid]["path"].resolve())
                    content_list.append({"video": f"file://{abs_path}", "fps": 2})
                ds_messages.append({"role": "user", "content": content_list})
            else:
                ds_messages.append({"role": "user", "content": [{"text": content}]})
        elif role == "assistant":
            ds_messages.append({"role": "assistant", "content": [{"text": content}]})
    return ds_messages

# ==================== 流式适配器（Chat 模块使用）====================
async def dashscope_stream_adapter(response_generator, enable_thinking: bool = False):
    loop = asyncio.get_event_loop()
    
    def _next(gen):
        try:
            return next(gen), False
        except StopIteration:
            return None, True
    
    while True:
        item, done = await loop.run_in_executor(None, _next, response_generator)
        if done:
            break
        
        status_code = _safe_getattr(item, 'status_code', 200)
        if status_code != 200:
            err_msg = _safe_getattr(item, 'message', 'Unknown streaming error')
            yield sse({"error": f"API Error: {err_msg}"})
            return
        
        try:
            output = item.output
            if not output or not output.choices:
                continue
            
            choice = output.choices[0]
            if isinstance(choice, dict):
                message = choice.get('message', {})
            else:
                message = getattr(choice, 'message', None) or {}
            
            if not message:
                continue
            
            content_list = _safe_getattr(message, 'content', None)
            if isinstance(content_list, list):
                text = "".join(c.get("text", "") for c in content_list if isinstance(c, dict))
            else:
                text = str(content_list) if content_list is not None else ""
            
            payload = {}
            if text and text.strip():
                payload["content"] = text
            
            # ========== 修复：使用安全的 reasoning 提取，过滤空值 ==========
            if enable_thinking:
                reasoning = _extract_reasoning_safe(message)
                if reasoning:  # 只有非空才发送
                    payload["reasoning"] = reasoning
            # ============================================================
            
            if payload:
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        
        except (AttributeError, IndexError, KeyError) as e:
            print(f"[Stream Parse Warning] {e}")
            continue
    
    yield "data: [DONE]\n\n"

# ==================== 图像生成 ====================
class ImageGenRequest(BaseModel):
    prompt: str
    files: list[str] = Field(default_factory=list)
    size: str = "1024*1024"
    n: int = Field(default=1, ge=1, le=6)
    watermark: bool = False
    negative_prompt: str = " "
    prompt_extend: bool = True

# ==================== 视频生成请求模型 ====================
class VideoGenRequest(BaseModel):
    prompt: str = ""
    files: list[str] = Field(default_factory=list)
    resolution: Literal["480P", "720P", "1080P"] = "1080P"
    ratio: Literal["adaptive", "16:9", "9:16", "1:1", "4:3", "3:4", "21:9"] = "16:9"
    duration: int = Field(default=5, ge=-1, le=30)
    watermark: bool = True
    seed: int | None = Field(default=None, ge=-1, le=2147483647)
    prompt_extend: bool = True
    audio: bool = True

def infer_video_mode(files_meta: list[dict]) -> str:
    images = [f for f in files_meta if f["type"] == "image"]
    videos = [f for f in files_meta if f["type"] == "video"]
    if videos:
        return "edit"
    elif len(images) == 1:
        return "i2v"
    elif len(images) >= 2:
        return "r2v"
    else:
        return "t2v"

@app.post("/api/generate/image")
async def generate_image(req: ImageGenRequest):
    route = configuration.runtime('image')
    if not req.prompt.strip():
        raise HTTPException(400, "提示词不能为空")
    if len(req.files) > 3:
        raise HTTPException(400, "参考图最多 3 张")
    content = []
    for fid in req.files:
        if fid not in file_store:
            raise HTTPException(404, f"文件不存在: {fid}")
        meta = file_store[fid]
        if meta["type"] != "image":
            raise HTTPException(400, f"仅支持图片参考文件: {meta['filename']}")
        abs_path = str(meta["path"].resolve())
        content.append({"image": f"file://{abs_path}"})
    content.append({"text": req.prompt.strip()})
    messages = [{"role": "user", "content": content}]
    try:
        response = await asyncio.to_thread(MultiModalConversation.call,
            model=route['model'], api_key=route['api_key'],
            messages=messages,
            stream=False,
            n=req.n,
            watermark=req.watermark,
            negative_prompt=req.negative_prompt,
            prompt_extend=req.prompt_extend,
            size=req.size,
        )
        status_code = _safe_getattr(response, 'status_code', 200)
        if status_code != 200:
            code = _safe_getattr(response, 'code', 'Unknown')
            msg = _safe_getattr(response, 'message', 'No message')
            raise HTTPException(502, f"DashScope error {code}: {msg}")
        output = _safe_getattr(response, 'output', None)
        if not output or not output.choices:
            raise HTTPException(502, "模型未返回有效结果")
        message = output.choices[0].message
        contents = message.content if message else []
        image_urls = []
        if isinstance(contents, list):
            for c in contents:
                if isinstance(c, dict) and 'image' in c:
                    image_urls.append(c['image'])
        if not image_urls:
            raise HTTPException(502, "模型未返回图片")
        return {"success": True, "urls": image_urls, "count": len(image_urls)}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ImageGen Error] {type(e).__name__}: {e}")
        raise HTTPException(500, str(e))

# ==================== API 路由 ====================
@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    max_size = 100 * 1024 * 1024
    size = 0
    while chunk := await file.read(1024 * 1024):
        size += len(chunk)
        if size > max_size:
            raise HTTPException(400, "文件最大100MB")
    await file.seek(0)
    fid = str(uuid.uuid4())
    ext = Path(file.filename).suffix.lower()
    path = (UPLOAD_DIR / f"{fid}{ext}").resolve()
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    is_img = ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"]
    is_video = ext in [".mp4", ".avi", ".mov", ".mkv", ".webm"]
    file_store[fid] = {
        "filename": file.filename,
        "type": "image" if is_img else ("video" if is_video else "text"),
        "path": path,
    }
    save_file_store()
    return {
        "file_id": fid,
        "filename": file.filename,
        "type": "image" if is_img else ("video" if is_video else "text"),
        "url": f"/uploads/{fid}{ext}",
    }

# ==================== 视频生成路由 ====================
@app.post("/api/generate/video")
async def generate_video(req: VideoGenRequest):
    route = configuration.runtime('video')
    if req.duration in (0, 1):
        raise HTTPException(400, "视频时长须为 2–30 秒或智能时长 -1")
    media_list = []
    video_files, image_files = [], []
    for fid in req.files:
        if fid not in file_store:
            raise HTTPException(404, f"文件不存在: {fid}")
        meta = file_store[fid]
        ftype = meta["type"]
        abs_path = str(meta["path"].resolve())
        if ftype == "video":
            video_files.append(abs_path)
        elif ftype == "image":
            image_files.append(abs_path)
    mode = infer_video_mode_from_files(video_files, image_files)
    if mode == "edit" and video_files:
        media_list.append({"type": "reference_video", "url": f"file://{video_files[0]}"})
        for img_path in image_files[:4]:
            media_list.append({"type": "reference_image", "url": f"file://{img_path}"})
    elif mode == "i2v" and image_files:
        media_list.append({"type": "first_frame", "url": f"file://{image_files[0]}"})
    elif mode == "r2v" and image_files:
        for img_path in image_files[:9]:
            media_list.append({"type": "reference_image", "url": f"file://{img_path}"})
    try:
        call_kwargs = {
            "model": route['model'],
            "api_key": route['api_key'],
            "prompt": req.prompt.strip(),
            "resolution": req.resolution,
            "ratio": req.ratio,
            "duration": req.duration,
            "watermark": req.watermark,
            "prompt_extend": req.prompt_extend,
        }
        call_kwargs["audio"] = req.audio
        if req.seed is not None:
            call_kwargs["seed"] = req.seed
        if media_list:
            call_kwargs["media"] = media_list
        rsp = await asyncio.to_thread(VideoSynthesis.async_call, **call_kwargs)
        status_code = _safe_getattr(rsp, 'status_code', 200)
        if status_code != 200:
            code = _safe_getattr(rsp, 'code', 'Unknown')
            msg = _safe_getattr(rsp, 'message', 'No message')
            raise HTTPException(502, f"DashScope error {code}: {msg}")
        output = _safe_getattr(rsp, 'output', None)
        if not output:
            raise HTTPException(502, "模型未返回任务信息")
        task_id = getattr(output, 'task_id', None)
        if not task_id:
            raise HTTPException(502, "模型未返回 task_id")
        video_task_cache[task_id] = {
            "status": "PENDING",
            "result": {"videos": []},
            "created_at": datetime.now().isoformat(),
            "mode": mode,
            "prompt": req.prompt.strip(),
            "rsp": rsp,
            "api_key": route['api_key']
        }
        return {"success": True, "task_id": task_id, "status": "PENDING", "inferred_mode": mode}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[VideoGen Error] {type(e).__name__}: {e}")
        raise HTTPException(500, str(e))

def infer_video_mode_from_files(video_files: list, image_files: list) -> str:
    if video_files:
        return "edit"
    elif len(image_files) == 1:
        return "i2v"
    elif len(image_files) >= 2:
        return "r2v"
    else:
        return "t2v"

@app.get("/api/tasks/{task_id}")
async def query_task(task_id: str):
    cached = video_task_cache.get(task_id)
    if not cached:
        return {"task_id": task_id, "status": "FAILED", "error": "任务不存在或已过期"}
    try:
        if cached["status"] == "SUCCEEDED":
            return {"task_id": task_id, "status": "SUCCEEDED", "result": cached["result"]}
        rsp = cached["rsp"]
        status = await asyncio.to_thread(VideoSynthesis.fetch, task=rsp, api_key=cached.get('api_key', api_key))
        status_code = _safe_getattr(status, 'status_code', 200)
        if status_code != 200:
            code = _safe_getattr(status, 'code', 'Unknown')
            msg = _safe_getattr(status, 'message', 'No message')
            print(f"[Task Fetch Error] {code}: {msg}")
            return {"task_id": task_id, "status": "FAILED", "error": f"DashScope fetch error {code}: {msg}"}
        output = _safe_getattr(status, 'output', None)
        if not output:
            return {"task_id": task_id, "status": "PENDING", "progress": 5}
        task_status = getattr(output, 'task_status', 'PENDING')
        cached["status"] = task_status
        if task_status == 'SUCCEEDED':
            result = status
            result_output = _safe_getattr(result, 'output', None)
            raw_videos = []
            if result_output:
                video_url = getattr(result_output, 'video_url', None)
                if video_url:
                    raw_videos.append(video_url)
            videos = [await proxy_video_url(url) for url in raw_videos]
            cached["result"]["videos"] = videos
            cached["status"] = "SUCCEEDED"
            return {"task_id": task_id, "status": "SUCCEEDED", "result": {"videos": videos}}
        elif task_status == 'FAILED':
            error_msg = getattr(output, 'message', 'Unknown error')
            cached["status"] = "FAILED"
            return {"task_id": task_id, "status": "FAILED", "error": error_msg}
        else:
            progress = estimate_progress(task_status)
            return {"task_id": task_id, "status": task_status, "progress": progress}
    except Exception as e:
        print(f"[Task Query Error] {type(e).__name__}: {e}")
        raise HTTPException(502, f"任务查询失败: {e}")

def estimate_progress(task_status: str) -> int:
    progress_map = {
        "PENDING": 5, "RUNNING": 30, "SUCCEEDED": 100,
        "FAILED": 0, "CANCELLED": 0
    }
    if "WAIT" in task_status.upper():
        return 10
    elif "PROCESS" in task_status.upper():
        return 50
    elif "GENERATE" in task_status.upper():
        return 70
    elif "RENDER" in task_status.upper():
        return 85
    return progress_map.get(task_status, 20)

def chat_route(req):
    module = 'chat'
    kinds = [file_store[fid]['type'] for fid in req.files if fid in file_store]
    if 'image' in kinds and req.image_mode != 'ocr':
        module = 'vision'
    elif any(kind not in ('image', 'video') for kind in kinds):
        module = 'document'
    route = configuration.runtime(module)
    if req.connection:
        route = {**configuration.connection(req.connection), 'model': req.model or route['model']}
    elif req.model:
        route['model'] = req.model
    if not isinstance(route['model'], str) or not route['model'].strip() or len(route['model']) > 160:
        raise HTTPException(400, '模型名称无效')
    if route['provider'] != 'ollama' and not route['api_key']:
        raise HTTPException(400, '请在设置的连接与 API 中配置密钥，或切换本机 Ollama')
    return route

@app.post("/api/chat")
async def chat(req: ChatRequest):
    try:
        route = chat_route(req)
        messages = await build_messages(req)
        if route['provider'] != 'dashscope':
            result = {'content': '', 'reasoning': ''}
            async for event in chat_events(route, messages, req.thinking, req.enable_search):
                for key in result:
                    result[key] += event.get(key, '')
            return result
        
        # ========== 修复：根据 thinking 参数控制 enable_thinking ==========
        extra = {}
        extra["enable_thinking"] = req.thinking
        # =================================================================
        extra["enable_search"] = req.enable_search
        response = await asyncio.to_thread(MultiModalConversation.call,
            model=route['model'], api_key=route['api_key'],
            messages=messages,
            result_format='message',
            **extra  # ← 新增：传入 thinking 控制参数
        )
        
        status_code = _safe_getattr(response, 'status_code', 200)
        if status_code != 200:
            code = _safe_getattr(response, 'code', 'Unknown')
            msg = _safe_getattr(response, 'message', 'No message')
            raise HTTPException(502, f"DashScope error {code}: {msg}")
        
        output = response.output
        if output and output.choices:
            message = output.choices[0].message
            content_list = message.content
            if isinstance(content_list, list):
                text = "".join(c.get("text", "") for c in content_list if isinstance(c, dict))
            else:
                text = str(content_list)
            
            # ========== 修复：关闭思考时不返回 reasoning ==========
            reasoning = ''
            if req.thinking:  # ← 只在开启思考时提取 reasoning
                reasoning = getattr(message, 'reasoning_content', '') or ''
            # =====================================================
            
            if not text:
                raise HTTPException(502, "模型未返回回答")
            return {"content": text, "reasoning": reasoning}
        
        raise HTTPException(502, "模型未返回有效结果")
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Chat Error] {e}")
        raise HTTPException(500, str(e))

@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    route = chat_route(req)
    messages = await build_messages(req)
    if route['provider'] != 'dashscope':
        async def local_stream():
            try:
                async for event in chat_events(route, messages, req.thinking, req.enable_search):
                    yield sse(event)
            except Exception as exc:
                yield sse({'error': getattr(exc, 'detail', '连接失败，请检查本地服务或模型配置')})
            yield 'data: [DONE]\n\n'
        return StreamingResponse(local_stream(), media_type='text/event-stream')
    def sync_stream():
        extra = {}
        extra["enable_thinking"] = req.thinking
        extra["enable_search"] = req.enable_search
        return MultiModalConversation.call(
            model=route['model'], api_key=route['api_key'],
            messages=messages,
            result_format='message',
            stream=True,
            incremental_output=True,
            **extra
        )
    loop = asyncio.get_event_loop()
    response_gen = await loop.run_in_executor(None, sync_stream)
    
    async def gen():
        try:
            async for chunk in dashscope_stream_adapter(response_gen, req.thinking):
                yield chunk
        except Exception as e:
            print(f"[Stream Error] {e}")
            yield sse({"error": f"流式响应异常: {e}"})
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(gen(), media_type="text/event-stream")

@app.get("/")
def index():
    return {
        "status": "running",
        "memory_files": len(file_store),
        "cached_in_memory": len(rag_cache),
        "max_cache": MAX_CACHED_FILES,
    }

def sse(payload):
    return "data: " + json.dumps(payload, ensure_ascii=False) + "\n\n"


def get_agent_events(req, messages, tools):
    module = req.tool if req.tool in ('search_image', 'image_search') else 'agent'
    route = configuration.runtime(module)
    return agent_events(req, messages, tools, api_key=route['api_key'],
                        base_url=route['base_url'], model=route['model'])


@app.post("/api/agent")
async def agent_endpoint(req: AgentRequest):
    messages, tools = build_request(req, file_store)
    result = {"content": "", "reasoning": "", "images": [], "tool_calls": []}
    async for event in get_agent_events(req, messages, tools):
        if event.get("error"):
            raise HTTPException(502, event["error"])
        for key in ("content", "reasoning"):
            result[key] += event.get(key, "")
        if event.get("images"):
            result["images"].extend(event["images"])
        if event.get("tool_name") and not event.get("tool_calling"):
            result["tool_calls"].append({"tool": event["tool_name"], "status": "done"})
    return result


@app.post("/api/agent/stream")
async def agent_stream(req: AgentRequest):
    messages, tools = build_request(req, file_store)
    async def generate():
        async for event in get_agent_events(req, messages, tools):
            yield sse(event)
        yield "data: [DONE]\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
