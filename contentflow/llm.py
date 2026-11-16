"""Yapay zeka çağrılarının tek giriş noktası.

Neden tek bir modül? Loglama, kota yönetimi (429), önbellek, yeniden deneme ve marka sesi
enjeksiyonu her çağrıda AYNI şekilde uygulansın diye. Sayfalar ve üreticiler SDK'ları
doğrudan çağırmaz; sağlayıcı değişse bile yalnızca bu dosya değişir.

Genel fonksiyonlar:
- generate_structured(...)  -> pydantic nesnesi (Gemini + structured output)
- generate_text(...)        -> düz metin (Gemini)
- generate_speech(...)      -> MP3 dosya yolu (edge-tts, anahtar gerektirmez)
- log_image_upload(...)     -> harici araçla (ChatGPT/Gemini/Canva) üretilip yüklenen görseli logla
- log_human_edit(...)       -> elle düzenlemeyi logla (edited_by_human: true)
- requests_today()          -> bugünkü Gemini istek sayısı (kenar çubuğu sayacı)
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, TypeVar

from pydantic import BaseModel, ValidationError

from contentflow import config, storage

T = TypeVar("T", bound=BaseModel)

# Günlük istek sayacına giren log türleri (Gemini çağrıları)
GEMINI_KINDS = {"structured", "text"}

# Testlerde beklemeyi atlamak için değiştirilebilir
_sleep: Callable[[float], None] = time.sleep


# --------------------------------------------------------------------------- hatalar


class LLMError(Exception):
    """Kullanıcıya gösterilecek Türkçe, anlaşılır hata."""


class QuotaExhausted(LLMError):
    """Günlük ücretsiz kota doldu; beklemek bugün işe yaramaz."""


class ServerBusy(LLMError):
    """Model geçici olarak yoğun / sunucu hatası (5xx); yedek modele geçilebilir."""


@dataclass
class CallResult:
    """Her üretim çağrısının dönüşü: çıktı + izlenebilirlik bilgisi."""
    output: Any            # pydantic nesnesi, str veya dosya yolu (Path)
    log_id: str
    cached: bool


# --------------------------------------------------------------------------- Gemini istemcisi

_client_instance = None


def _client():
    """Gemini istemcisini ilk ihtiyaçta oluşturur (import sırasında anahtar gerekmez)."""
    global _client_instance
    if _client_instance is None:
        if not config.api_key_present():
            raise LLMError("GEMINI_API_KEY bulunamadı. aistudio.google.com'dan ücretsiz anahtar alıp "
                           "proje klasöründeki .env dosyasına yaz.")
        from google import genai
        _client_instance = genai.Client(api_key=os.environ["GEMINI_API_KEY"].strip())
    return _client_instance


def _error_details(exc: Exception) -> list[dict]:
    details = getattr(exc, "details", None)
    if isinstance(details, dict):
        details = details.get("error", details).get("details", [])
    return details if isinstance(details, list) else []


def rate_limit_info(exc: Exception) -> tuple[float | None, bool]:
    """429 hatasından (önerilen bekleme sn, günlük kota mı) bilgisini çıkarır.

    Gemini 429 gövdesi `RetryInfo.retryDelay` (ör. "33s") ve `QuotaFailure.violations[].quotaId`
    (ör. "GenerateRequestsPerDayPerProjectPerModel-FreeTier") taşır.
    """
    delay, daily = None, False
    for d in _error_details(exc):
        if not isinstance(d, dict):
            continue
        if m := re.match(r"([\d.]+)s", str(d.get("retryDelay", ""))):
            delay = float(m.group(1))
        for v in d.get("violations", []) or []:
            if "perday" in str(v.get("quotaId", "")).lower():
                daily = True
    if "per day" in str(exc).lower() or "perday" in str(exc).lower():
        daily = True
    return delay, daily


def _translate_error(exc: Exception) -> LLMError:
    code = getattr(exc, "code", None)
    msg = str(getattr(exc, "message", "") or exc)
    if code == 429:
        _, daily = rate_limit_info(exc)
        if daily:
            return QuotaExhausted(
                "Gemini günlük ücretsiz kotası doldu. Kota genellikle Pasifik saatiyle gece yarısı (TR ~10:00-11:00) "
                "sıfırlanır. Beklerken önbellekteki içeriklerle devam edebilir ya da .env'de TEXT_MODEL'i başka bir "
                "ücretsiz modele çevirebilirsin (her modelin kotası ayrıdır).")
        return LLMError("Gemini dakikalık istek sınırına takıldık ve beklemeye rağmen açılmadı. Bir dakika sonra tekrar dene.")
    if code in (401, 403) or "API key not valid" in msg or "API_KEY_INVALID" in msg:
        return LLMError("Gemini API anahtarı geçersiz veya yetkisiz. .env içindeki GEMINI_API_KEY değerini kontrol et.")
    if code == 404:
        return LLMError("Model bulunamadı. .env'deki TEXT_MODEL / REVIEW_MODEL adı yanlış ya da kullanımdan kalkmış olabilir.")
    if code == 400:
        if "location" in msg.lower() and "not supported" in msg.lower():
            return LLMError("Gemini ücretsiz katmanı bulunduğun bölgede desteklenmiyor görünüyor.")
        return LLMError(f"İstek reddedildi (geçersiz parametre veya şema): {msg[:300]}")
    if code and code >= 500:
        return ServerBusy("Gemini modelleri şu an aşırı yoğun (Google tarafında geçici sunucu hatası). "
                          "Yedek modeller de denendi; birkaç dakika sonra tekrar dene.")
    if _is_network_error(exc):
        return LLMError("Gemini'ye bağlanılamadı veya zaman aşımı oldu. İnternet bağlantını kontrol et.")
    return LLMError(f"Beklenmeyen hata: {type(exc).__name__}: {msg[:300]}")


def _is_network_error(exc: Exception) -> bool:
    return isinstance(exc, (ConnectionError, TimeoutError)) or type(exc).__module__.split(".")[0] in {
        "httpx", "httpx2", "httpcore", "aiohttp", "requests", "urllib3"}


def _with_retry(fn: Callable[[], Any]) -> Any:
    """Geçici hatalarda yeniden dener.

    - 429 dakikalık kota: API'nin önerdiği süre kadar (yoksa üstel) bekleyip tekrar dener.
    - 429 günlük kota: beklemek işe yaramaz; hemen QuotaExhausted fırlatır.
    - 5xx ve ağ hataları: üstel geri çekilme (2, 4, 8 ... sn).
    """
    from google.genai import errors

    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            return fn()
        except errors.APIError as exc:
            if exc.code == 429:
                delay, daily = rate_limit_info(exc)
                if daily:
                    raise _translate_error(exc) from exc
                wait = min(delay or config.RETRY_BASE_DELAY_S * 2 ** attempt, config.MAX_RATE_LIMIT_WAIT_S)
            elif exc.code and exc.code >= 500:
                # Yoğunlukta aynı modelde uzun beklemek yerine kısa deneyip yedek modele geç
                if attempt >= config.SERVER_ERROR_RETRIES:
                    raise _translate_error(exc) from exc
                wait = config.RETRY_BASE_DELAY_S * 2 ** (attempt - 1)
            else:
                raise _translate_error(exc) from exc
            if attempt == config.MAX_RETRIES:
                raise _translate_error(exc) from exc
            _sleep(wait)
        except Exception as exc:  # ağ hataları
            if not _is_network_error(exc):
                raise
            if attempt == config.MAX_RETRIES:
                raise _translate_error(exc) from exc
            _sleep(config.RETRY_BASE_DELAY_S * 2 ** (attempt - 1))


# --------------------------------------------------------------------------- günlük sayaç


def requests_today() -> int:
    """Bugün yapılan (önbellekten gelmeyen, başarılı) Gemini istek sayısı."""
    today = datetime.now().astimezone().date().isoformat()
    return sum(1 for r in storage.read_jsonl(storage.prompt_log_path())
               if r.get("kind") in GEMINI_KINDS and str(r.get("timestamp", "")).startswith(today))


# --------------------------------------------------------------------------- marka sesi


def brand_voice_block() -> str | None:
    """Güncel Marka Sesi Rehberini system prompt'a eklenecek metne çevirir. Yoksa None."""
    from contentflow import render

    voice = storage.get_current("brand_voice")
    if not voice:
        return None
    seed = storage.load_brand_seed()
    try:
        body = render.brand_voice_markdown(voice)
    except (KeyError, TypeError):  # beklenmeyen/eski biçim: genel dönüşüm
        body = render.generic_markdown(voice)
    return f"## MARKA SESİ REHBERİ — {seed.get('name', 'Marka')} (her çıktıda buna uy)\n{body}"


BASE_SYSTEM_RULES = (
    "Kurgusal bir marka için Türkçe içerik üreten bir uzmansın. Tüm çıktılar Türkçe olmalı.\n"
    "Kurallar: gerçek kişi, ünlü veya başka markaların slogan/görsel kimliğini kullanma; "
    "isim bazlı stil taklidi yapma; istatistik, tarih veya alıntı uydurma — sayısal bir iddia "
    "gerekirse cümlenin sonuna [KAYNAK GEREKLİ] yaz; marka hakkındaki bilgileri yalnızca verilen "
    "marka bağlamından al."
)


def build_system_prompt(system_prompt: str = "", with_brand_voice: bool = True) -> tuple[str, bool]:
    """(son system prompt, marka sesi eklendi mi) döndürür."""
    parts = [BASE_SYSTEM_RULES]
    if system_prompt:
        parts.append(system_prompt.strip())
    injected = False
    if with_brand_voice:
        block = brand_voice_block()
        if block:
            parts.append(block)
            injected = True
    return "\n\n".join(parts), injected


# --------------------------------------------------------------------------- önbellek + log


def _cache_key(kind: str, payload: dict) -> str:
    raw = json.dumps({"kind": kind, **payload}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _cache_get(key: str) -> dict | None:
    return storage.read_json(storage.subdir("cache") / f"{key}.json")


def _cache_put(key: str, data: dict) -> None:
    storage.write_json(storage.subdir("cache") / f"{key}.json", data)


def _log(**fields: Any) -> str:
    record = {
        "id": uuid.uuid4().hex[:12],
        "timestamp": storage.now_iso(),
        "stage": fields.pop("stage", ""),
        "task": fields.pop("task", ""),
        "formula": fields.pop("formula", ""),
        "model": fields.pop("model", ""),
        "system_prompt": fields.pop("system_prompt", ""),
        "user_prompt": fields.pop("user_prompt", ""),
        "output": fields.pop("output", ""),
        "input_tokens": fields.pop("input_tokens", 0),
        "output_tokens": fields.pop("output_tokens", 0),
        "calendar_item_id": fields.pop("calendar_item_id", None),
        "edited_by_human": fields.pop("edited_by_human", False),
        **fields,  # ek alanlar: kind, brand_voice_injected, tool, parent_log_id ...
    }
    storage.append_jsonl(storage.prompt_log_path(), record)
    return record["id"]


def _usage(response: Any) -> tuple[int, int]:
    u = getattr(response, "usage_metadata", None)
    if u is None:
        return 0, 0
    out = (getattr(u, "candidates_token_count", 0) or 0) + (getattr(u, "thoughts_token_count", 0) or 0)
    return int(getattr(u, "prompt_token_count", 0) or 0), int(out)


# --------------------------------------------------------------------------- metin (Gemini)


def _parse(response: Any, schema: type[T]) -> T:
    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, schema):
        return parsed
    text = getattr(response, "text", None) or ""
    try:
        return schema.model_validate_json(text)
    except ValidationError as exc:
        feedback = getattr(response, "prompt_feedback", None)
        if feedback is not None and getattr(feedback, "block_reason", None):
            raise LLMError("İstek Gemini güvenlik filtresine takıldı. Promptu yumuşatıp tekrar dene.") from exc
        raise LLMError("Model şemaya uygun çıktı döndürmedi. 'Yeniden üret' ile tekrar dene.") from exc


def _text_call(
    *, kind: str, task: str, stage: str, formula: str, user_prompt: str, system_prompt: str,
    with_brand_voice: bool, calendar_item_id: str | None, model: str | None, use_cache: bool,
    schema: type[BaseModel] | None,
) -> CallResult:
    from google.genai import types

    model = model or config.TEXT_MODEL
    system, injected = build_system_prompt(system_prompt, with_brand_voice)
    key = _cache_key(kind, {"model": model, "system": system, "user": user_prompt,
                            "schema": schema.__name__ if schema else None})

    # Önbellek ücretsiz kotayı korur: aynı prompt tekrar gönderilmez.
    if use_cache and (hit := _cache_get(key)):
        out = schema.model_validate(hit["output"]) if schema else hit["output"]
        return CallResult(out, hit["log_id"], cached=True)

    cfg = {"system_instruction": system}
    if schema:
        cfg |= {"response_mime_type": "application/json", "response_schema": schema}
    client = _client()

    # Ana model yoğunsa (503) veya günlük kotası dolduysa yedek ücretsiz modellere sırayla geç.
    chain = [model] + [m for m in config.FALLBACK_MODELS if m != model]
    response, used_model, last_exc = None, model, None
    for candidate in chain:
        try:
            response = _with_retry(lambda m=candidate: client.models.generate_content(
                model=m, contents=user_prompt, config=types.GenerateContentConfig(**cfg)))
            used_model = candidate
            break
        except (ServerBusy, QuotaExhausted) as exc:
            last_exc = exc
    if response is None:
        raise last_exc

    if schema:
        parsed = _parse(response, schema)
        output_store: Any = parsed.model_dump(mode="json")
        result_out: Any = parsed
    else:
        output_store = result_out = response.text or ""
        if not output_store:
            raise LLMError("Model boş yanıt döndürdü. 'Yeniden üret' ile tekrar dene.")

    in_tok, out_tok = _usage(response)
    log_id = _log(
        stage=stage, task=task, formula=formula, model=used_model, system_prompt=system,
        user_prompt=user_prompt,
        output=output_store if isinstance(output_store, str) else json.dumps(output_store, ensure_ascii=False),
        input_tokens=in_tok, output_tokens=out_tok, calendar_item_id=calendar_item_id,
        kind=kind, brand_voice_injected=injected,
        **({"fallback_from": model} if used_model != model else {}),
    )
    _cache_put(key, {"output": output_store, "log_id": log_id})
    return CallResult(result_out, log_id, cached=False)


def generate_structured(
    *, task: str, stage: str, formula: str, user_prompt: str, schema: type[T],
    system_prompt: str = "", with_brand_voice: bool = True, calendar_item_id: str | None = None,
    model: str | None = None, use_cache: bool = True,
) -> CallResult:
    """Pydantic şemasına uyan yapılandırılmış çıktı üretir. use_cache=False → 'Yeniden üret'."""
    return _text_call(kind="structured", task=task, stage=stage, formula=formula, user_prompt=user_prompt,
                      system_prompt=system_prompt, with_brand_voice=with_brand_voice,
                      calendar_item_id=calendar_item_id, model=model, use_cache=use_cache, schema=schema)


def generate_text(
    *, task: str, stage: str, formula: str, user_prompt: str, system_prompt: str = "",
    with_brand_voice: bool = True, calendar_item_id: str | None = None, model: str | None = None,
    use_cache: bool = True,
) -> CallResult:
    return _text_call(kind="text", task=task, stage=stage, formula=formula, user_prompt=user_prompt,
                      system_prompt=system_prompt, with_brand_voice=with_brand_voice,
                      calendar_item_id=calendar_item_id, model=model, use_cache=use_cache, schema=None)


# --------------------------------------------------------------------------- ses (edge-tts)


def generate_speech(
    *, task: str, stage: str, text: str, voice: str | None = None, rate: str = "+0%", pitch: str = "+0Hz",
    filename_stem: str = "voiceover", calendar_item_id: str | None = None, use_cache: bool = True,
) -> CallResult:
    """Metni edge-tts ile seslendirir, workspace/audio/ altına MP3 kaydeder. Anahtar gerekmez,
    ancak internet bağlantısı gerekir (Microsoft Edge'in çevrimiçi okuma servisi)."""
    import edge_tts

    voice = voice or config.TTS_VOICE
    key = _cache_key("speech", {"engine": config.TTS_ENGINE, "text": text, "voice": voice,
                                "rate": rate, "pitch": pitch})
    if use_cache and (hit := _cache_get(key)) and Path(hit["output"]).exists():
        return CallResult(Path(hit["output"]), hit["log_id"], cached=True)

    path = storage.subdir("audio") / f"{filename_stem}_{uuid.uuid4().hex[:6]}.mp3"

    async def _save():
        await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(str(path))

    last_exc: Exception | None = None
    for attempt in range(1, 4):
        try:
            asyncio.run(_save())
            last_exc = None
            break
        except Exception as exc:  # ağ / servis hatası
            last_exc = exc
            path.unlink(missing_ok=True)
            if attempt < 3:
                _sleep(config.RETRY_BASE_DELAY_S * 2 ** (attempt - 1))
    if last_exc is not None or not path.exists() or path.stat().st_size == 0:
        raise LLMError("Seslendirme servisine (edge-tts) ulaşılamadı. İnternet bağlantını kontrol edip tekrar dene."
                       + (f" Ayrıntı: {type(last_exc).__name__}" if last_exc else ""))

    log_id = _log(stage=stage, task=task, formula="TTS", model=f"{config.TTS_ENGINE}:{voice}",
                  system_prompt=f"rate={rate}, pitch={pitch}", user_prompt=text, output=str(path),
                  calendar_item_id=calendar_item_id, kind="speech", voice=voice)
    _cache_put(key, {"output": str(path), "log_id": log_id})
    return CallResult(path, log_id, cached=False)


# --------------------------------------------------------------------------- harici görsel


def log_image_upload(
    *, task: str, stage: str, prompt: str, tool: str, path: str, calendar_item_id: str | None = None,
    prompt_log_id: str | None = None,
) -> str:
    """Kullanıcının harici bir araçta (ChatGPT/Gemini/Canva) ürettiği görseli prompt loguna işler.
    Prompt kütüphanesi ve AI kullanım raporu bu kayıttan beslenir."""
    return _log(stage=stage, task=task, formula="harici görsel aracı", model=tool, user_prompt=prompt,
                output=path, calendar_item_id=calendar_item_id, kind="image_upload", tool=tool,
                parent_log_id=prompt_log_id)


# --------------------------------------------------------------------------- elle düzenleme


def log_human_edit(
    *, task: str, stage: str, output: Any, parent_log_id: str | None = None,
    calendar_item_id: str | None = None,
) -> str:
    """Kullanıcının elle yaptığı düzenlemeyi prompt loguna işler."""
    out = output if isinstance(output, str) else json.dumps(output, ensure_ascii=False)
    return _log(stage=stage, task=task, formula="elle düzenleme", model="insan", output=out,
                calendar_item_id=calendar_item_id, edited_by_human=True, kind="human_edit",
                parent_log_id=parent_log_id)
