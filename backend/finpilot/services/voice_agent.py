"""
Sarvam AI TTS & STT + OpenAI Chat FastAPI Backend
==================================================
Endpoints:
  POST /stt/transcribe       - Upload audio file → get transcript
  POST /stt/stream           - WebSocket proxy for real-time STT
    POST /chat/completions     - Text messages → OpenAI response
    POST /agent/respond        - Text messages → OpenAI response + Sarvam TTS audio
  POST /tts/generate         - Text → audio file (WAV/MP3)
  WS   /tts/stream           - WebSocket streaming TTS
  GET  /health               - Health check
"""

import os
import io
import json
import base64
import asyncio
import contextlib
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket, WebSocketDisconnect, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Any, Optional
from dotenv import load_dotenv
from sarvamai import AsyncSarvamAI
from sarvamai.core.api_error import ApiError
from openai import AsyncOpenAI, OpenAIError

load_dotenv()

CA_SYSTEM_PROMPT = """You are a highly experienced Chartered Accountant (CA) based in India, with deep expertise in Indian taxation, GST, FEMA, RBI regulations, and international trade compliance.

Your role is to guide users through practical, real-world financial and regulatory scenarios.

For every query, explain:
- Applicable laws and regulations in the Indian context
- Step-by-step compliance requirements
- Required documents and filings
- Tax implications, if any
- Common mistakes to avoid
- Practical tips used by professionals

When the user provides a scenario, break down the answer clearly and systematically.

Use simple language but maintain professional accuracy. Wherever needed, include examples.

Always mention if rules may change based on updates or specific business structures.

Write in a warm, human, easy-to-read style. Avoid markdown symbols like # and * in the response.
Do not use dense formatting or a checklist style. Avoid numbered lists and overly bullet-heavy answers.
Prefer short paragraphs, simple labels such as "GST treatment:", "Documents needed:", and "Next steps:", and clear line breaks instead of tables unless they are truly helpful.
Keep the tone professional, practical, conversational, and naturally human, as if a knowledgeable CA is speaking directly to the customer.
Sound empathetic, helpful, and calm. Avoid robotic, overly formal, or generic AI-style phrasing.
Use plain language, natural transitions, and clear explanations that feel like a real person is guiding the user step by step.
Write in Indian English, using wording that feels natural to users in India."""

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BACKEND_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"
_sarvam_client: Optional[AsyncSarvamAI] = None
_sarvam_client_key: Optional[str] = None
_openai_client: Optional[AsyncOpenAI] = None
_openai_client_key: Optional[str] = None

app = FastAPI(
    title="Sarvam AI TTS & STT + OpenAI Chat Agent",
    description="FastAPI backend for Sarvam AI Speech-to-Text, Text-to-Speech, and OpenAI Chat",
    version="1.1.0",
)

# Allow all origins during development; restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Pydantic Models ────────────────────────────────────────────────────────

class TTSRequest(BaseModel):
    text: str
    target_language_code: str = "en-IN"    # BCP-47 language tag
    speaker: str = "shubh"                  # bulbul:v3 default voice
    model: str = "bulbul:v3"               # bulbul:v2 or bulbul:v3
    pace: float = 1.0                       # 0.5 – 2.0
    output_format: str = "wav"              # wav | mp3 | opus etc.
    speech_sample_rate: Optional[int] = None
    temperature: Optional[float] = None


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    model: str = "gpt-4o-mini"
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    reasoning_effort: Optional[str] = None
    max_tokens: Optional[int] = None
    wiki_grounding: Optional[bool] = None


class ChatResponse(BaseModel):
    id: Optional[str] = None
    object: Optional[str] = None
    created: Optional[int] = None
    model: Optional[str] = None
    choices: list[dict[str, Any]] = Field(default_factory=list)
    usage: Optional[dict[str, Any]] = None

    model_config = {"extra": "allow"}


class AgentRequest(ChatRequest):
    target_language_code: str = "en-IN"
    speaker: str = "shubh"
    tts_model: str = "bulbul:v3"
    pace: float = 1.0
    output_format: str = "wav"


class TranslateRequest(BaseModel):
    input: str
    source_language_code: str = "auto"
    target_language_code: str = "gu-IN"
    speaker_gender: Optional[str] = "Male"
    mode: Optional[str] = None
    model: Optional[str] = None
    output_script: Optional[str] = None
    numerals_format: Optional[str] = None


class STTResponse(BaseModel):
    request_id: Optional[str] = None
    transcript: str
    language_code: Optional[str] = None
    language_probability: Optional[float] = None
    timestamps: Optional[dict[str, Any]] = None
    diarized_transcript: Optional[dict[str, Any]] = None


class TranslateResponse(BaseModel):
    request_id: Optional[str] = None
    translated_text: str
    source_language_code: Optional[str] = None


class AgentResponse(BaseModel):
    assistant_text: str
    chat: dict[str, Any]
    audio_format: str
    audio_base64: str


# ─── Helpers ────────────────────────────────────────────────────────────────

def _get_sarvam_api_key() -> str:
    api_key = os.getenv("SARVAM_API_KEY") or SARVAM_API_KEY
    if not api_key:
        raise HTTPException(status_code=500, detail="SARVAM_API_KEY not configured")
    return api_key


def _sarvam() -> AsyncSarvamAI:
    global _sarvam_client, _sarvam_client_key

    api_key = _get_sarvam_api_key()
    if _sarvam_client is None or _sarvam_client_key != api_key:
        _sarvam_client = AsyncSarvamAI(api_subscription_key=api_key)
        _sarvam_client_key = api_key
    return _sarvam_client


def _openai() -> AsyncOpenAI:
    global _openai_client, _openai_client_key

    api_key = os.getenv("OPENAI_API_KEY") or OPENAI_API_KEY
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

    if _openai_client is None or _openai_client_key != api_key:
        _openai_client = AsyncOpenAI(api_key=api_key)
        _openai_client_key = api_key

    return _openai_client


def _sdk_model_dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "dict"):
        return value.dict()
    return value


def _clean_audio_content_type(content_type: Optional[str]) -> str:
    if not content_type:
        return "audio/wav"
    return content_type.split(";", 1)[0].strip().lower()


def _raise_sdk_error(exc: ApiError) -> None:
    status_code = exc.status_code or 502
    detail = exc.body if exc.body is not None else str(exc)
    raise HTTPException(status_code=status_code, detail=detail)


def _chat_messages(messages: list[ChatMessage]) -> list[dict[str, str]]:
    if not messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    allowed_roles = {"system", "user", "assistant", "tool"}
    normalized = []
    for index, message in enumerate(messages):
        role = message.role.strip().lower()
        content = message.content.strip()
        if role not in allowed_roles:
            raise HTTPException(status_code=400, detail=f"messages[{index}].role is invalid")
        if not content:
            raise HTTPException(status_code=400, detail=f"messages[{index}].content cannot be empty")
        normalized.append({"role": role, "content": content})
    return normalized


def _chat_payload(req: ChatRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "messages": [{"role": "system", "content": CA_SYSTEM_PROMPT}] + _chat_messages(req.messages),
        "model": req.model,
    }
    # Include these fields if they are not None
    # NOTE: We NEVER include reasoning_effort to avoid thinking mode
    #       which wastes tokens and returns reasoning_content instead of content
    for field in ("temperature", "top_p", "max_tokens", "wiki_grounding"):
        value = getattr(req, field)
        if value is not None:
            payload[field] = value
    
    return payload


def _extract_assistant_text(chat: dict[str, Any]) -> str:
    # Try the standard OpenAI format
    choices = chat.get("choices") or []
    if choices:
        first_choice = choices[0] or {}
        # Try nested message structure
        message = first_choice.get("message") or {}
        content = message.get("content") or ""
        if content:
            return str(content).strip()
        # Try direct content field
        if first_choice.get("content"):
            return str(first_choice.get("content")).strip()
    
    # Try alternative formats
    if chat.get("output"):
        return str(chat.get("output")).strip()
    if chat.get("text"):
        return str(chat.get("text")).strip()
    if chat.get("message"):
        msg = chat.get("message")
        if isinstance(msg, dict) and msg.get("content"):
            return str(msg.get("content")).strip()
        return str(msg).strip()
    
    return ""
async def _create_chat_completion(req: ChatRequest) -> dict[str, Any]:
    """Create a chat completion using OpenAI."""
    payload = _chat_payload(req)
    try:
        response = await _openai().chat.completions.create(**payload)
    except OpenAIError as exc:
        status_code = getattr(exc, "status_code", None) or 502
        raise HTTPException(status_code=status_code, detail=f"OpenAI error: {str(exc)}")

    data = _sdk_model_dump(response)
    if not _extract_assistant_text(data):
        raise HTTPException(status_code=502, detail="OpenAI chat completion returned an empty assistant response")
    return data



async def _generate_tts_audio(req: TTSRequest) -> bytes:
    payload = {
        "text": req.text,
        "target_language_code": req.target_language_code,
        "speaker": req.speaker,
        "model": req.model,
        "pace": req.pace,
        "output_audio_codec": req.output_format,
    }
    if req.speech_sample_rate is not None:
        payload["speech_sample_rate"] = req.speech_sample_rate
    if req.temperature is not None:
        payload["temperature"] = req.temperature

    try:
        response = await _sarvam().text_to_speech.convert(**payload)
    except ApiError as exc:
        _raise_sdk_error(exc)

    if not response.audios:
        raise HTTPException(status_code=502, detail="Sarvam TTS returned no audio")
    return base64.b64decode(response.audios[0])


# ─── Health ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def ui():
    ui_path = FRONTEND_DIR / "ui.html"
    if ui_path.exists():
        return ui_path.read_text(encoding="utf-8")

    voice_path = FRONTEND_DIR / "voice.html"
    if voice_path.exists():
        return voice_path.read_text(encoding="utf-8")

    raise HTTPException(status_code=404, detail="ui.html or voice.html not found")


@app.get("/data.json")
async def personal_data():
    data_path = FRONTEND_DIR / "data.json"
    if not data_path.exists():
        raise HTTPException(status_code=404, detail="data.json not found")
    return json.loads(data_path.read_text(encoding="utf-8"))


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "sarvam_key_set": bool(os.getenv("SARVAM_API_KEY") or SARVAM_API_KEY),
        "openai_key_set": bool(os.getenv("OPENAI_API_KEY") or OPENAI_API_KEY),
        "sarvam_sdk": "sarvamai",
    }


# ─── STT REST ───────────────────────────────────────────────────────────────

@app.post("/stt/transcribe", response_model=STTResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    language_code: Optional[str] = Form(None),   # e.g. "en-IN"; omit or use "unknown" for auto-detect
    model: str = Form("saaras:v3"),              # saaras:v3 (recommended) | saarika:v2.5
    mode: str = Form("transcribe"),              # transcribe | translate | verbatim | translit | codemix
    input_audio_codec: Optional[str] = Form(None),
):
    """
    Upload an audio file and receive a text transcript.
    Supported formats: WAV, MP3, AAC, AIFF, OGG, OPUS, FLAC, MP4/M4A, WebM, AMR, WMA, PCM.
    Max duration: 30 seconds (use /stt/batch for longer files).
    """
    audio_bytes = await file.read()

    kwargs: dict[str, Any] = {
        "model": model,
        "mode": mode,
        "file": (file.filename, io.BytesIO(audio_bytes), _clean_audio_content_type(file.content_type)),
    }
    if language_code:
        kwargs["language_code"] = language_code
    if input_audio_codec:
        kwargs["input_audio_codec"] = input_audio_codec

    try:
        response = await _sarvam().speech_to_text.transcribe(**kwargs)
    except ApiError as exc:
        _raise_sdk_error(exc)

    return STTResponse(
        request_id=response.request_id,
        transcript=response.transcript,
        language_code=response.language_code,
        language_probability=response.language_probability,
        timestamps=_sdk_model_dump(response.timestamps) if response.timestamps else None,
        diarized_transcript=_sdk_model_dump(response.diarized_transcript) if response.diarized_transcript else None,
    )


# ─── STT WebSocket (Real-time Streaming) ────────────────────────────────────

@app.websocket("/stt/stream")
async def stt_stream(websocket: WebSocket):
    """
    Real-time STT via WebSocket.

    Protocol (client → server):
      1. Send JSON config:   {"language_code": "unknown", "model": "saaras:v3"}
      2. Send binary audio chunks (WAV or raw PCM at 16 kHz)
      3. Send JSON end signal: {"type": "end"}

    Protocol (server → client):
      - JSON transcript events: {"transcript": "...", "is_final": true/false}
      - JSON error events:      {"error": "..."}
    """
    await websocket.accept()

    try:
        _get_sarvam_api_key()
    except HTTPException:
        await websocket.send_json({"error": "SARVAM_API_KEY not configured"})
        await websocket.close()
        return

    # Receive config from the client first
    try:
        config_msg = await websocket.receive_text()
        config = json.loads(config_msg)
    except Exception:
        await websocket.send_json({"error": "First message must be a JSON config"})
        await websocket.close()
        return

    language_code = config.get("language_code", "unknown")
    model = config.get("model", "saaras:v3")
    mode = config.get("mode", "transcribe")
    encoding = config.get("encoding", "audio/wav")
    sample_rate = int(config.get("sample_rate", 16000))

    connect_kwargs = {
        "language_code": language_code,
        "model": model,
        "mode": mode,
    }
    for option in ("high_vad_sensitivity", "vad_signals", "flush_signal", "input_audio_codec"):
        if config.get(option) is not None:
            connect_kwargs[option] = config[option]
    if config.get("connection_sample_rate") is not None:
        connect_kwargs["sample_rate"] = str(config["connection_sample_rate"])

    try:
        async with _sarvam().speech_to_text_streaming.connect(**connect_kwargs) as sarvam_ws:

            async def forward_audio():
                """Forward client audio chunks through the official Sarvam SDK."""
                try:
                    while True:
                        msg = await websocket.receive()
                        if msg.get("type") == "websocket.disconnect":
                            break
                        if msg.get("bytes") is not None:
                            audio_b64 = base64.b64encode(msg["bytes"]).decode("ascii")
                            await sarvam_ws.transcribe(
                                audio_b64,
                                encoding=encoding,
                                sample_rate=sample_rate,
                            )
                        elif msg.get("text") is not None:
                            data = json.loads(msg["text"])
                            if data.get("type") in {"flush", "end"}:
                                await sarvam_ws.flush()
                            if data.get("type") == "end":
                                break
                except WebSocketDisconnect:
                    pass

            async def receive_transcripts():
                """Forward Sarvam transcript events to the client."""
                try:
                    async for message in sarvam_ws:
                        await websocket.send_json(_sdk_model_dump(message))
                except Exception:
                    pass

            forward_task = asyncio.create_task(forward_audio())
            receive_task = asyncio.create_task(receive_transcripts())
            await forward_task
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(receive_task, timeout=10)
            if not receive_task.done():
                receive_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await receive_task

    except ApiError as e:
        await websocket.send_json({"error": str(e), "status_code": e.status_code})
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()


# ─── Chat Completion ────────────────────────────────────────────────────────

@app.post("/chat/completions", response_model=ChatResponse)
async def chat_completions(req: ChatRequest):
    """
    Send multi-turn text messages to Sarvam Chat Completion.
    """
    return await _create_chat_completion(req)


# ─── Voice Agent Text Pipeline ──────────────────────────────────────────────

@app.post("/agent/respond", response_model=AgentResponse)
async def agent_respond(req: AgentRequest):
    """
    Run messages → chat completion → TTS audio.
    Returns JSON with assistant text, raw chat response, and base64 audio.
    """
    chat = await _create_chat_completion(req)
    assistant_text = _extract_assistant_text(chat)
    audio_bytes = await _generate_tts_audio(TTSRequest(
        text=assistant_text,
        target_language_code=req.target_language_code,
        speaker=req.speaker,
        model=req.tts_model,
        pace=req.pace,
        output_format=req.output_format,
    ))

    return AgentResponse(
        assistant_text=assistant_text,
        chat=chat,
        audio_format=req.output_format,
        audio_base64=base64.b64encode(audio_bytes).decode("ascii"),
    )


# ─── TTS REST ───────────────────────────────────────────────────────────────

@app.post("/tts/generate")
async def generate_speech(req: TTSRequest):
    """
    Convert text to speech. Returns audio as a streaming file response.
    Max text length: 2500 characters per request.
    """
    audio_bytes = await _generate_tts_audio(req)
    mime = "audio/wav" if req.output_format == "wav" else f"audio/{req.output_format}"
    return StreamingResponse(
        io.BytesIO(audio_bytes),
        media_type=mime,
        headers={"Content-Disposition": f"attachment; filename=output.{req.output_format}"},
    )


# ─── Text Translation ───────────────────────────────────────────────────────

@app.post("/text/translate", response_model=TranslateResponse)
async def translate_text(req: TranslateRequest):
    """
    Translate text using the official Sarvam AI SDK quickstart path.
    """
    payload = {
        "input": req.input,
        "source_language_code": req.source_language_code,
        "target_language_code": req.target_language_code,
    }
    for field in ("speaker_gender", "mode", "model", "output_script", "numerals_format"):
        value = getattr(req, field)
        if value is not None:
            payload[field] = value

    try:
        response = await _sarvam().text.translate(**payload)
    except ApiError as exc:
        _raise_sdk_error(exc)

    return TranslateResponse(
        request_id=response.request_id,
        translated_text=response.translated_text,
        source_language_code=response.source_language_code,
    )


# ─── TTS WebSocket (Real-time Streaming) ────────────────────────────────────

@app.websocket("/tts/stream")
async def tts_stream(websocket: WebSocket):
    """
    Real-time streaming TTS via WebSocket.

    Protocol (client → server):
    1. Send JSON config:  {"speaker": "shubh", "target_language_code": "en-IN", "model": "bulbul:v3"}
      2. Send JSON text chunks: {"text": "नमस्ते, आप कैसे हैं?"}
      3. Send JSON flush:   {"type": "flush"}
      4. Send JSON end:     {"type": "end"}

    Protocol (server → client):
      - Binary audio chunks (WAV PCM)
      - JSON events: {"type": "event", "data": {"event_type": "final"}} when finished
    """
    await websocket.accept()

    try:
        _get_sarvam_api_key()
    except HTTPException:
        await websocket.send_json({"error": "SARVAM_API_KEY not configured"})
        await websocket.close()
        return

    try:
        config_msg = await websocket.receive_text()
        config = json.loads(config_msg)
    except Exception:
        await websocket.send_json({"error": "First message must be a JSON config"})
        await websocket.close()
        return

    try:
        model = config.get("model", "bulbul:v3")
        async with _sarvam().text_to_speech_streaming.connect(
            model=model,
            send_completion_event="true",
        ) as sarvam_ws:
            await sarvam_ws.configure(
                target_language_code=config.get("target_language_code", "en-IN"),
                speaker=config.get("speaker", "shubh"),
                pace=float(config.get("pace", 1.0)),
                speech_sample_rate=int(config.get("speech_sample_rate", 24000)),
                output_audio_codec=config.get("output_format", "mp3"),
                output_audio_bitrate=config.get("output_audio_bitrate", "128k"),
                min_buffer_size=int(config.get("min_buffer_size", 50)),
                max_chunk_length=int(config.get("max_chunk_length", 150)),
                dict_id=config.get("dict_id"),
            )

            async def forward_text():
                """Forward text chunks from the client through the Sarvam SDK."""
                try:
                    while True:
                        msg = await websocket.receive_text()
                        data = json.loads(msg)
                        if data.get("text"):
                            await sarvam_ws.convert(data["text"])
                        if data.get("type") == "flush":
                            await sarvam_ws.flush()
                        if data.get("type") == "end":
                            await sarvam_ws.flush()
                            break
                except WebSocketDisconnect:
                    pass

            async def receive_audio():
                """Forward generated audio chunks from Sarvam to the client."""
                try:
                    async for message in sarvam_ws:
                        data = _sdk_model_dump(message)
                        if data.get("type") == "audio":
                            audio = base64.b64decode(data["data"]["audio"])
                            await websocket.send_bytes(audio)
                        else:
                            await websocket.send_json(data)
                            if data.get("type") == "event" and data.get("data", {}).get("event_type") == "final":
                                break
                except Exception:
                    pass

            forward_task = asyncio.create_task(forward_text())
            receive_task = asyncio.create_task(receive_audio())
            await forward_task
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(receive_task, timeout=30)
            if not receive_task.done():
                receive_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await receive_task

    except ApiError as e:
        await websocket.send_json({"error": str(e), "status_code": e.status_code})
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()
