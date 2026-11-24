# Castorice

Vue 3 + Vite frontend and FastAPI backend for character chat, document Q&A,
image/video creation, and an Agent with hosted tools.

## Development preview

This repository contains the frontend, backend, desktop shell, and regression tests.
The character videos, audio, avatars, and app icons are local assets. For a fresh
checkout, enter the app when the intro offers to skip the video, and select a
gradient, solid color, or your own background in Appearance settings. To build
an installer, supply your own icons at `desktop/assets/icon.ico` and
`desktop/assets/icon.png`.

## Layout and chat interaction

Keep the original title's styling, size, animation and position. Both chat and
Agent pages use this order: title → input → attachment tray (when present) →
conversation → session history. Improve interactions within this arrangement;
do not compact the header or move the input below the conversation.

Messages are chronological with the streaming reply at the bottom. Scrolling up
pauses automatic following; “Jump to latest” resumes it. Messages support copy,
delete and an eight-second undo. Fenced code has a separate copy button. The
original horizontal rounded input supports multiline text, Enter to send,
Shift+Enter for a newline and a stop button during generation.

Stage two adds editable questions, answer regeneration/retry, Markdown tables,
headings, lists, blockquotes and safe links, plus syntax highlighting for common
code languages. Editing and regeneration replace later turns from the selected
question. The previous conversation can be restored until a new question is sent
or another rewrite replaces that backup. Attachments can be removed while editing.

Active chat and Agent conversations are saved separately in this browser,
including input drafts, pending attachments and rewrite backups. Reloading during
generation restores partial text with an interruption notice; it never resubmits
the model request automatically. Failed requests keep the input and attachments.
Browser storage errors are displayed instead of silently claiming to save.
These local saves are not cross-device backups.

## Run on Windows

From the repository root, create an environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r castorice_backend/requirements.txt
```

Set `DASHSCOPE_API_KEY` in the environment or `castorice_backend/.env`.
Once Python and frontend dependencies are installed, start both services from
the project root:

```powershell
.\start-dev.ps1
```

The script reuses healthy services, starts missing ones in the background and
checks both are ready. Logs are in `.dev-logs`. Opening the frontend alone does
not start the AI backend.

To start the backend manually instead:

```powershell
cd castorice_backend
..\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

For this machine's verification environment, substitute `.check-venv` for `.venv`.
In another terminal:

```powershell
cd castorice_vue
npm ci
npm run dev
```

Open http://localhost:5173. Tesseract with `chi_sim` and `eng` language packs
must be available on PATH for local OCR. This machine already has both.

## Models

Sidebar controls and request bindings are documented in [SIDEBAR_AUDIT.md](SIDEBAR_AUDIT.md).
The sidebar starts collapsed on every page load; parameter choices are remembered.
Generation parameters are locked while a request runs. Image/video advanced controls
are grouped under Advanced, with a reset action scoped to the current mode.

| Environment override | Default model |
| --- | --- |
| CHAT_MODEL | qwen3.8-max |
| AGENT_MODEL | qwen3.8-max |
| IMAGE_MODEL | qwen-image-3.0 |
| VIDEO_MODEL | wan3.0-video-prime |

`RESPONSES_BASE_URL` optionally overrides the Agent endpoint. The default is
`https://dashscope.aliyuncs.com/compatible-mode/v1`.
Model permissions and quota are managed in the user's Alibaba Cloud account.
Video requests can incur charges; the verification below did not submit any.

Uploaded files live in `castorice_backend/uploads`; their metadata is stored in
`castorice_backend/upload_index.json` outside the public static directory.
Keep both when backing up. Older uploads made before indexing was implemented
may need to be uploaded again. Browser history remains in localStorage.
This remains a local single-user application; run one backend worker for the
in-memory RAG and video task caches. Video tasks do not survive a backend restart.

## Checks

```powershell
cd castorice_backend
..\.check-venv\Scripts\python.exe -m unittest test_regressions -v
cd ../castorice_vue
npm test
npm run build
```

The backend regression suite mocks model calls, including video submission.

The stage two browser fixture at `/tests/chat-stage-two.html` (Vite development
server only) uses simulated model output to check rendering, reload recovery and
cancellation without consuming model quota. Its data uses a separate storage key.

Verified on 2026-10-17:

- Production frontend build; 8 backend and 5 frontend regression tests.
- Browser chat displayed a successful streaming reply.
- Chat, document retrieval, OCR and visual understanding returned expected test text.
- qwen-image-3.0 returned one generated image.
- Agent code execution and auto mode actually invoked code_interpreter.
- Web extraction invoked web_extractor; text image search returned six images.
- Image-to-image search invoked image_search and correctly reported no matches
  for the synthetic test wordmark; a positive matching-image result is unverified.
- Video model and reference_video arguments checked only with mocks, never a live request.

Official API references:
- https://help.aliyun.com/zh/model-studio/qwen-api-via-openai-responses
- https://help.aliyun.com/zh/model-studio/qwen-image-generation-and-editing-api-reference
- https://help.aliyun.com/zh/model-studio/wan3-video-generation-guide
