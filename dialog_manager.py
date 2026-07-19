# -*- coding: utf-8 -*-
"""
Dialog Manager — LLM-контроллер «думающего» диалога.

Три интеллектуальных скилла из ТЗ живут здесь:
  Skill 1. Dynamic Questioning — в LLM уходит вся история диалога + бриф
           категории; модель либо задаёт ОДИН уточняющий вопрос, либо фиксирует
           параметры и переходит дальше.
  Skill 2. Auto-Quoting — по собранным данным модель даёт вилку цен (От/До) и
           срок СТРОГО из заданных тарифов (config.TARIFFS). Нет тарифа —
           говорит, что посчитает менеджер.
  Skill 3. CRM handoff — когда статус ready, модель отдаёт готовое ТЗ; отправку
           админу («🔥 горячая заявка») делает jarvis_bot.

Контракт: модель ВСЕГДА отвечает одним JSON-объектом:
{
  "thought":   "внутренние рассуждения (клиенту не показываем)",
  "status":    "asking" | "ready",
  "message":   "текст клиенту (один вопрос ИЛИ итоговая сводка)",
  "options":   ["короткие варианты ответа на вопрос — кнопки"],
  "collected": { "...": "..." },        // накопленные параметры заказа
  "quote":     { "min": "...", "max": "...", "term": "..." } | null,
  "brief":     "финальное ТЗ одним текстом (только при status=ready)"
}
"""

import json
import logging
import re
import requests

import config
import knowledge_base as kb

logger = logging.getLogger(__name__)

_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


# ── Системный промпт ──────────────────────────────────────────────────────────

def build_system_prompt(sess: dict) -> str:
    flow = sess.get("flow")
    cat = sess.get("category")
    payer = sess.get("payer")
    s = config.STUDIO

    payer_line = ""
    if payer == "ur":
        payer_line = "Тип плательщика: ЮРЛИЦО/ИП (нужны закрывающие документы)."
    elif payer == "fiz":
        payer_line = "Тип плательщика: ФИЗЛИЦО (частный заказ)."

    return f"""Ты — Джарвис, ИИ-ассистент студии «{s['name']}» ({s['city']}).
Ты одновременно эксперт-технолог полиграфии и опытный IT-аналитик.
Общайся на «ты» уважительно, тепло, без канцелярита и клише. Пиши по-русски.

ГЛАВНЫЙ ПРИНЦИП — ТЫ ДУМАЕШЬ, А НЕ ДОПРАШИВАЕШЬ.
- Используй базу знаний, чтобы САМ сузить выбор и не задавать глупых вопросов.
  (Пример глупого вопроса: для печати фото спрашивать про картон — так нельзя.)
- Задавай РОВНО ОДИН уточняющий вопрос за сообщение, самый важный сейчас.
- Не вываливай списки из многих вопросов сразу. Веди диалог порционно.
- ОДНО СООБЩЕНИЕ = ОДНО РЕШЕНИЕ. Нельзя в одном сообщении упомянуть выбор
  («холст или бумага») и тут же спросить о другом (размер). Сначала закрой
  выбор отдельным вопросом с кнопками options, и только следующим сообщением
  задавай открытый вопрос. Если ты написал в message слово «или» между
  вариантами — options НЕ может быть пустым.
- Если клиент уже дал ответ — не переспрашивай, фиксируй параметр и иди дальше.
- Когда ключевых параметров достаточно для заявки — переходи к статусу ready.

БРИФ ТЕКУЩЕЙ КАТЕГОРИИ (логика обдумывания — соблюдай строго):
{kb.category_brief(cat)}
{payer_line}

КОНТАКТЫ КЛИЕНТА уже получены и подтверждены через Telegram до начала диалога
(имя, телефон, username) — НЕ спрашивай номер телефона и имя повторно.

ОБРАЗЕЦ / ГОТОВЫЙ МАКЕТ — обязательное правило:
- Если клиент упоминает, что у него уже ЕСТЬ готовый дизайн/макет/фото/скан
  (например: печать по своему макету, допечатка тиража, открытка/приглашение/
  визитка «как раньше», восстановление старого макета, «у меня всё готово») —
  ОБЯЗАТЕЛЬНО спроси отдельным вопросом, есть ли у него фото или файл образца,
  и попроси прислать его прямо в этот чат (можно фото или документом). Это
  отдельный вопрос, options можно не давать (свободный ответ/файл).
- Если в истории уже видно, что клиент прислал фото/файл (системная пометка
  вида «[Клиент прислал фото/файл...]») — поблагодари один раз, зафиксируй в
  collected (например "образец": "прислан в чат") и НЕ проси повторно.
- Если клиент не может прислать сразу — не блокируй заявку: зафиксируй
  "образец": "клиент пришлёт позже" и продолжай диалог дальше.

РАСЧЁТ ЦЕНЫ (Auto-Quoting):
{config.tariff_line(cat)}
- Если тариф известен — дай ориентировочную вилку «От/До» и срок.
- Если тариф НЕ задан — НЕ выдумывай числа. Скажи, что точную сумму назовёт
  менеджер, а вилку/срок оставь пустыми (null).

УСЛОВИЯ ОПЛАТЫ (обязательно предупреди клиента в итоговой сводке при ready):
{config.PAYMENT_TERMS}

КОГДА ПЕРЕХОДИТЬ В status=ready:
- Собраны ключевые параметры (что печатаем/делаем, материал/технология,
  размер/формат, тираж/объём, для веба — суть задачи и функционал).
- В message дай короткую человеческую сводку заказа + вилку/срок (если есть) и
  спроси, всё ли верно.
- В поле brief сформируй аккуратное финальное ТЗ (см. формат ниже).

ФОРМАТ ПОЛЯ brief (только при ready), обычным текстом:
  Направление: <Типография | Веб-кодинг>
  Категория: <название>
  Параметры: <перечисли всё собранное по пунктам>
  Тираж/объём: <...>
  Ориентировочно: <вилка + срок или «рассчитает менеджер»>
  Оплата: предоплата 50%
  Комментарий клиента: <если был>

КНОПКИ-ВАРИАНТЫ (поле options) — ЖЁСТКОЕ ПРАВИЛО:
- Если в тексте вопроса ты перечисляешь варианты (через «или», запятыми,
  списком) — эти же варианты ОБЯЗАН продублировать кнопками в options.
  Вопрос со встроенными вариантами и пустым options — ОШИБКА.
- 2–4 кнопки, каждая до 30 символов, формулировка короткая:
  ["Матовая", "Глянцевая"], ["Ламинация", "Фольгирование", "Тиснение", "Без отделки"].
- Добавляй вариант «На ваше усмотрение» или «Без …», если уместно.
- Пустой options допустим ТОЛЬКО для свободных ответов: тираж числом,
  текст для макета, описание задачи, контакты, сроки конкретной датой.

ФОРМАТ ОТВЕТА — СТРОГО один JSON-объект, без markdown-обёртки и текста вокруг:
{{"thought": "...", "status": "asking|ready", "message": "...",
  "options": [], "collected": {{}}, "quote": null, "brief": null}}

Контакты студии для справки: {s['phone']}, {s['contact']}, {s['address']}, {s['hours']}.
"""


# ── Вызов LLM ─────────────────────────────────────────────────────────────────

def _call_llm(system_prompt: str, history: list[dict]) -> str:
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    messages = [{"role": "system", "content": system_prompt}] + history
    data = {
        "model": config.OPENROUTER_MODEL,
        "messages": messages,
        "temperature": config.LLM_TEMPERATURE,
        "max_tokens": config.LLM_MAX_TOKENS,
        # просим JSON, если провайдер модели поддерживает:
        "response_format": {"type": "json_object"},
    }
    r = requests.post(_ENDPOINT, headers=headers, json=data, timeout=config.LLM_TIMEOUT)

    # Некоторые модели/провайдеры не принимают response_format —
    # при ошибке пробуем ещё раз без него (JSON просим промптом).
    if r.status_code != 200:
        logger.warning("LLM call failed (%s): %s — retry without response_format",
                       r.status_code, r.text[:300])
        data.pop("response_format", None)
        r = requests.post(_ENDPOINT, headers=headers, json=data,
                          timeout=config.LLM_TIMEOUT)

    if r.status_code != 200:
        raise RuntimeError(f"API {r.status_code}: {r.text[:300]}")

    body = r.json()
    if "choices" not in body or not body["choices"]:
        raise RuntimeError(f"API вернул неожиданный ответ: {str(body)[:300]}")
    return body["choices"][0]["message"]["content"]


def _extract_json(raw: str) -> dict:
    """Достаём JSON, даже если модель обернула его в текст/```json."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(raw[start:end + 1])
        raise


def _normalize(result: dict) -> dict:
    result.setdefault("status", "asking")
    result.setdefault("message", "Уточни, пожалуйста, детали.")
    result.setdefault("collected", {})
    result.setdefault("quote", None)
    result.setdefault("brief", None)
    opts = result.get("options") or []
    if not isinstance(opts, list):
        opts = []
    # только строки, не длиннее 60 символов, максимум 4 кнопки
    result["options"] = [str(o)[:60] for o in opts if str(o).strip()][:4]
    return result


def _parse_or_fallback(raw: str) -> dict:
    try:
        return _normalize(_extract_json(raw))
    except Exception as e:  # noqa: BLE001
        logger.error("JSON parse failed: %s | raw=%s", e, raw[:300])
        # Мягкий фолбэк: показываем сырой текст как вопрос, не роняем диалог.
        return _normalize({
            "status": "asking",
            "message": raw[:1500] if raw else
                       "Уточни, пожалуйста, детали заказа ещё раз.",
        })


# Вопрос со словом «или» почти всегда содержит выбор — ему нужны кнопки.
_CHOICE_HINT = re.compile(r"\bили\b", re.IGNORECASE)

_FIX_OPTIONS_PROMPT = (
    "СИСТЕМНАЯ ПРОВЕРКА (клиент этого не видит): в твоём вопросе есть выбор "
    "(«или»), но options пуст — это нарушение правила. Если это реальный выбор "
    "для клиента — переформулируй сообщение (одно решение за раз!) и продублируй "
    "варианты кнопками в options. Если выбор мнимый (например, единицы "
    "измерения «в см или метрах») — верни вопрос без изменений и options: []. "
    "Ответь строго тем же JSON-форматом."
)


def process(sess: dict) -> dict:
    """
    Прогнать текущую историю диалога через LLM.
    Возвращает распарсенный dict контракта. Историю ассистента дописывает
    вызывающий код (jarvis_bot), сюда передаётся уже обновлённая история.
    """
    system_prompt = build_system_prompt(sess)
    raw = _call_llm(system_prompt, sess["history"])
    result = _parse_or_fallback(raw)

    # Контролёр: вопрос с выбором, но без кнопок → одна доработка.
    if (result["status"] == "asking" and not result["options"]
            and _CHOICE_HINT.search(result["message"])):
        logger.info("Вопрос с «или» без options — отправляю на доработку")
        followup = sess["history"] + [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": _FIX_OPTIONS_PROMPT},
        ]
        try:
            result2 = _parse_or_fallback(_call_llm(system_prompt, followup))
            if result2.get("message"):
                result = result2
        except Exception as e:  # noqa: BLE001
            logger.warning("Доработка не удалась (%s), отдаю первый вариант", e)

    return result
