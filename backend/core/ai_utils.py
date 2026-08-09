"""
Lightweight AI abstraction for Kistie Store.
Supports OpenAI-compatible endpoints and Google Gemini via direct HTTP (no extra packages needed).
Set AI_PROVIDER='openai' or 'gemini' in settings / .env.
"""
import json
import logging
import re
from typing import Any, Optional

import requests as _http
from django.conf import settings

logger = logging.getLogger(__name__)

_OPENAI_URL = 'https://api.openai.com/v1/chat/completions'
_GEMINI_URL_TPL = (
    'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}'
)
_GEMINI_DEFAULT_MODEL = 'gemini-2.0-flash'

# Hard cap per call to keep latency + cost low.
_MAX_TOKENS = 512
_TIMEOUT = 20  # seconds


def _call_openai(messages: list[dict], max_tokens: int = _MAX_TOKENS) -> Optional[str]:
    key = getattr(settings, 'OPENAI_API_KEY', '')
    if not key:
        return None
    model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')
    try:
        resp = _http.post(
            _OPENAI_URL,
            headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
            json={'model': model, 'messages': messages, 'max_tokens': max_tokens},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        return data['choices'][0]['message']['content'].strip()
    except Exception as exc:
        logger.warning('OpenAI call failed: %s', exc)
        return None


def _call_gemini(messages: list[dict], max_tokens: int = _MAX_TOKENS) -> Optional[str]:
    key = getattr(settings, 'GEMINI_API_KEY', '')
    if not key:
        return None
    model = getattr(settings, 'GEMINI_MODEL', _GEMINI_DEFAULT_MODEL)
    url = _GEMINI_URL_TPL.format(model=model, key=key)

    # Convert OpenAI-style messages to Gemini contents format.
    # Gemini uses 'user'/'model' roles; system prompt is prepended to first user turn.
    contents = []
    system_text = ''
    for msg in messages:
        role = msg.get('role', 'user')
        text = msg.get('content', '')
        if role == 'system':
            system_text = text
        elif role == 'user':
            combined = f"{system_text}\n\n{text}".strip() if system_text else text
            contents.append({'role': 'user', 'parts': [{'text': combined}]})
            system_text = ''  # only prepend once
        elif role == 'assistant':
            contents.append({'role': 'model', 'parts': [{'text': text}]})

    if not contents:
        return None

    try:
        resp = _http.post(
            url,
            json={
                'contents': contents,
                'generationConfig': {'maxOutputTokens': max_tokens},
            },
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        return data['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception as exc:
        logger.warning('Gemini call failed: %s', exc)
        return None


def chat_complete(messages: list[dict], max_tokens: int = _MAX_TOKENS) -> Optional[str]:
    """Call whichever provider is configured. Falls back to the other if primary fails."""
    provider = getattr(settings, 'AI_PROVIDER', 'openai').lower()
    if provider == 'gemini':
        result = _call_gemini(messages, max_tokens)
        if result is None:
            result = _call_openai(messages, max_tokens)
    else:
        result = _call_openai(messages, max_tokens)
        if result is None:
            result = _call_gemini(messages, max_tokens)
    return result


def ai_configured() -> bool:
    """True when at least one LLM provider key is set."""
    return bool(getattr(settings, 'OPENAI_API_KEY', '') or getattr(settings, 'GEMINI_API_KEY', ''))


def fit_recommender_uses_ai() -> bool:
    """Use LLM fit copy when explicitly enabled or when keys exist (default-on)."""
    flag = getattr(settings, 'FIT_RECOMMENDER_USE_AI', None)
    if flag is not None:
        return bool(flag)
    return ai_configured()


def _parse_json_object(raw: str) -> dict[str, Any] | None:
    if not raw:
        return None
    cleaned = raw.strip()
    if cleaned.startswith('```'):
        cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', cleaned, flags=re.I)
    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def parse_measurements_from_text(text: str) -> dict[str, float] | None:
    """
    Extract bust/waist/hips (cm) from natural language via LLM.
    Returns {'bust': 90.0, 'waist': 70.0, 'hips': 98.0} or None.
    """
    if not ai_configured():
        return None

    prompt = (
        'Extract body measurements in centimeters from this shopper message.\n'
        'Reply with JSON only, no markdown:\n'
        '{"bust": 90, "waist": 70, "hips": 98}\n'
        'Use null for any measurement not stated. If none are present, reply: {"bust": null, "waist": null, "hips": null}\n\n'
        f'Message: {text[:500]}'
    )
    result = chat_complete([{'role': 'user', 'content': prompt}], max_tokens=80)
    data = _parse_json_object(result or '')
    if not data:
        return None

    parsed: dict[str, float] = {}
    for key in ('bust', 'waist', 'hips'):
        value = data.get(key)
        if value is None or value == '':
            continue
        try:
            parsed[key] = float(value)
        except (TypeError, ValueError):
            continue

    if len(parsed) < 3:
        return None
    return parsed


def enhance_size_recommendation(bust: float, waist: float, hips: float, base: dict) -> str:
    """LLM shopper-friendly sizing note; falls back to the rule-based note."""
    base_note = base.get('note', '')
    if not ai_configured():
        return base_note

    prompt = (
        'You are a sizing assistant for Kistie Store (EU sizes 32–54, women\'s fashion).\n'
        'Write 2 short sentences for the shopper. Include the recommended EU size and practical fit advice.\n'
        'Do not invent a different size — use the one provided.\n\n'
        f'Measurements (cm): bust {bust}, waist {waist}, hips {hips}\n'
        f'Recommended EU size: {base.get("size")}\n'
        f'Baseline note: {base_note}'
    )
    result = chat_complete([{'role': 'user', 'content': prompt}], max_tokens=120)
    return result.strip() if result else base_note


def generate_demand_forecast_insights(forecasts: list[dict]) -> str:
    """
    LLM reorder guidance for staff from computed demand forecast rows.
    Each row: product, daily_rate, days_left, urgent.
    """
    if not forecasts or not ai_configured():
        return ''

    lines = []
    for row in forecasts[:12]:
        product = row['product']
        lines.append(
            f"- {product.name} ({product.category.name}): stock {product.stock_quantity}, "
            f"{row['daily_rate']}/day, ~{row['days_left']} days left"
            + (' [URGENT]' if row.get('urgent') else '')
        )

    prompt = (
        'You are an inventory analyst for Kistie Store, a Kampala fashion boutique.\n'
        'Given these demand forecasts (90-day sales velocity), write 3–5 bullet points for staff:\n'
        'prioritize reorders, flag urgent SKUs, and note any category patterns.\n'
        'Be concise and actionable.\n\n'
        + '\n'.join(lines)
    )
    result = chat_complete([{'role': 'user', 'content': prompt}], max_tokens=280)
    return result.strip() if result else ''


def _classify_inquiry_keywords(subject: str, message: str) -> str:
    text = f'{subject} {message}'.lower()
    if any(token in text for token in ('bulk', 'wholesale', 'large order', 'many pieces', 'corporate')):
        return 'bulk_order'
    if any(token in text for token in ('delivery', 'shipping', 'dispatch', 'courier', 'track')):
        return 'delivery'
    if any(token in text for token in ('complaint', 'refund', 'return', 'damaged', 'wrong size', ' unhappy')):
        return 'complaint'
    return 'general'


def _analyze_sentiment_keywords(text: str) -> str:
    lowered = text.lower()
    negative = ('bad', 'poor', 'terrible', 'disappoint', 'wrong', 'small', 'large', 'return', 'refund')
    positive = ('love', 'great', 'perfect', 'beautiful', 'recommend', 'excellent', 'amazing', 'happy')
    neg_hits = sum(1 for token in negative if token in lowered)
    pos_hits = sum(1 for token in positive if token in lowered)
    if pos_hits > neg_hits:
        return 'positive'
    if neg_hits > pos_hits:
        return 'negative'
    return 'neutral'


def classify_inquiry(subject: str, message: str) -> str:
    """Return one of: bulk_order | delivery | complaint | general."""
    prompt = (
        "Classify this customer inquiry into exactly ONE of these categories: "
        "bulk_order, delivery, complaint, general.\n"
        "Reply with only the category word, nothing else.\n\n"
        f"Subject: {subject}\nMessage: {message[:400]}"
    )
    result = chat_complete(
        [{'role': 'user', 'content': prompt}],
        max_tokens=10,
    )
    if result:
        tag = result.strip().lower().split()[0]
        if tag in ('bulk_order', 'delivery', 'complaint', 'general'):
            return tag
    return _classify_inquiry_keywords(subject, message)


def analyze_sentiment(text: str) -> str:
    """Return one of: positive | negative | neutral."""
    if not text.strip():
        return 'neutral'
    prompt = (
        "Classify the sentiment of this product review as exactly ONE of: "
        "positive, negative, neutral.\n"
        "Reply with only the sentiment word.\n\n"
        f"Review: {text[:500]}"
    )
    result = chat_complete(
        [{'role': 'user', 'content': prompt}],
        max_tokens=5,
    )
    if result:
        tag = result.strip().lower().split()[0]
        if tag in ('positive', 'negative', 'neutral'):
            return tag
    return _analyze_sentiment_keywords(text)


def generate_product_description(name: str, category: str, color: str) -> dict:
    """
    Generate an English description and Luganda translation.
    Returns {'description_en': '...', 'description_lg': '...'}.
    """
    prompt = (
        "You are a copywriter for Kistie Store, a Ugandan fashion boutique in Kampala. "
        "Write a punchy 2-3 sentence product description in English, then translate it into Luganda.\n\n"
        f"Product name: {name}\nCategory: {category}\nColor/material: {color or 'not specified'}\n\n"
        "Format your reply EXACTLY as:\n"
        "EN: <English description>\n"
        "LG: <Luganda translation>"
    )
    result = chat_complete(
        [{'role': 'user', 'content': prompt}],
        max_tokens=300,
    )
    en, lg = '', ''
    if result:
        for line in result.splitlines():
            if line.startswith('EN:'):
                en = line[3:].strip()
            elif line.startswith('LG:'):
                lg = line[3:].strip()
    return {'description_en': en, 'description_lg': lg}


# ---------------------------------------------------------------------------
# Size recommendation — EU table for accuracy, LLM for shopper-facing copy
# EU women's standard measurements (bust / waist / hips in cm)
# ---------------------------------------------------------------------------
_EU_SIZE_TABLE = [
    ('32', 76, 58, 84),
    ('34', 80, 62, 88),
    ('36', 84, 66, 92),
    ('38', 88, 70, 96),
    ('40', 92, 74, 100),
    ('42', 96, 78, 104),
    ('44', 100, 82, 108),
    ('46', 104, 86, 112),
    ('48', 108, 90, 116),
    ('50', 112, 94, 120),
    ('52', 116, 98, 124),
    ('54', 120, 102, 128),
]


def recommend_size(bust: float, waist: float, hips: float, *, use_ai_note: bool = True) -> dict:
    """
    Map body measurements (cm) to the best-matching EU size.
    Returns {'size': '38', 'note': '...'}.
    """
    best_size = '38'
    best_score = float('inf')

    for size, ref_bust, ref_waist, ref_hips in _EU_SIZE_TABLE:
        score = abs(bust - ref_bust) + abs(waist - ref_waist) + abs(hips - ref_hips)
        if score < best_score:
            best_score = score
            best_size = size

    base = {
        'size': best_size,
        'note': (
            f"Based on bust {bust} cm, waist {waist} cm, hips {hips} cm — "
            f"EU {best_size} is your closest match. Try one size up if you prefer a relaxed fit."
        ),
    }
    if use_ai_note:
        base['note'] = enhance_size_recommendation(bust, waist, hips, base)
    return base


def _safe_size_index(size: str) -> int:
    try:
        return [token for token, *_ in _EU_SIZE_TABLE].index(size)
    except ValueError:
        return -1


def _pick_adjacent_available_size(available_sizes: list[str], target_size: str) -> str:
    if not available_sizes:
        return target_size
    if target_size in available_sizes:
        return target_size

    target_index = _safe_size_index(target_size)
    if target_index < 0:
        return available_sizes[0]

    ranked = sorted(
        available_sizes,
        key=lambda size: abs(_safe_size_index(size) - target_index) if _safe_size_index(size) >= 0 else 999,
    )
    return ranked[0]


def _fit_base_size(available_sizes: list[str], bust, waist, hips, usual_size: str) -> str:
    if bust is not None and waist is not None and hips is not None:
        return recommend_size(float(bust), float(waist), float(hips))['size']
    if usual_size:
        return usual_size
    if available_sizes:
        return available_sizes[len(available_sizes) // 2]
    return '38'


def _fit_measurement_bonus(measurement_count: int) -> int:
    if measurement_count >= 3:
        return 18
    if measurement_count == 2:
        return 10
    if measurement_count == 1:
        return 5
    return 0


def _fit_size_bonus(available_sizes: list[str], usual_size: str, recommended_size: str) -> int:
    bonus = 0
    if usual_size:
        bonus += 8
        if usual_size == recommended_size:
            bonus += 8

    if available_sizes:
        bonus += min(15, len(available_sizes) * 3)
        if recommended_size in available_sizes:
            bonus += 8
        if len(available_sizes) <= 2:
            bonus -= 8
    else:
        bonus -= 10
    return bonus


def _fit_context_bonus(fit_preference: str, occasion: str, height) -> int:
    bonus = 0
    if fit_preference:
        bonus += 4
    if occasion:
        bonus += 2
    if height and float(height) >= 170:
        bonus += 2
    return bonus


def _fit_confidence(
    available_sizes: list[str],
    measurement_count: int,
    usual_size: str,
    recommended_size: str,
    fit_preference: str,
    occasion: str,
    height,
) -> int:
    confidence = 45
    confidence += _fit_measurement_bonus(measurement_count)
    confidence += _fit_size_bonus(available_sizes, usual_size, recommended_size)
    confidence += _fit_context_bonus(fit_preference, occasion, height)
    return max(10, min(95, confidence))


def _fit_bundle_suggestions(product):
    bundle_suggestions = []
    category = getattr(product, 'category', None)
    if category and hasattr(category, 'products'):
        related = (
            category.products.filter(stock_quantity__gt=0)
            .exclude(pk=product.pk)
            .prefetch_related('images')
            .order_by('-stock_quantity', '-created_at')[:2]
        )
        for related_product in related:
            bundle_suggestions.append({
                'id': related_product.id,
                'slug': related_product.slug,
                'name': related_product.name,
                'reason': 'Pairs well as a matching look and can lift basket value.',
            })

    if not bundle_suggestions:
        bundle_suggestions.append({
            'id': product.id,
            'slug': product.slug,
            'name': product.name,
            'reason': 'Use this as the main item and pair it with matching accessories.',
        })
    return bundle_suggestions


def _fit_explanation(product, available_sizes: list[str], recommended_size: str, fit_note: str, fit_preference: str, occasion: str) -> str:
    if not fit_recommender_uses_ai():
        return fit_note

    prompt = (
        "You are a fashion stylist for Kistie Store. Rewrite the following fit guidance into a short, "
        "friendly shopper message of 2 sentences max. Keep it practical and specific.\n\n"
        f"Product: {product.name}\n"
        f"Available sizes: {', '.join(available_sizes) or 'not specified'}\n"
        f"Recommended size: {recommended_size}\n"
        f"Fit preference: {fit_preference or 'not specified'}\n"
        f"Occasion: {occasion or 'not specified'}\n"
        f"Guidance: {fit_note}\n"
        "Reply with the shopper message only."
    )
    ai_explanation = chat_complete([{'role': 'user', 'content': prompt}], max_tokens=120)
    return ai_explanation.strip() if ai_explanation else fit_note


def recommend_fit(
    product,
    *,
    bust: float | None = None,
    waist: float | None = None,
    hips: float | None = None,
    height: float | None = None,
    usual_size: str = '',
    fit_preference: str = '',
    occasion: str = '',
) -> dict:
    """
    Return a fit score for a specific product.

    The first version is deterministic and explainable, but can optionally use the LLM
    for a shopper-friendly explanation.
    """
    available_sizes = product.size_list() if hasattr(product, 'size_list') else []
    measurements = [value for value in (bust, waist, hips) if value is not None]
    measurement_count = len(measurements)
    base_size = _fit_base_size(available_sizes, bust, waist, hips, usual_size)
    recommended_size = _pick_adjacent_available_size(available_sizes, base_size)
    confidence = _fit_confidence(
        available_sizes,
        measurement_count,
        usual_size,
        recommended_size,
        fit_preference,
        occasion,
        height,
    )
    if confidence >= 75:
        return_risk = 'low'
    elif confidence >= 50:
        return_risk = 'medium'
    else:
        return_risk = 'high'

    fit_note = (
        f"{product.name} is most likely to suit EU {recommended_size}. "
        f"Your fit confidence is {confidence}%, so the return risk is {return_risk}."
    )
    if fit_preference:
        fit_note += f" Preference noted: {fit_preference}."
    if occasion:
        fit_note += f" Best for {occasion} wear."

    bundle_suggestions = _fit_bundle_suggestions(product)
    explanation = _fit_explanation(
        product,
        available_sizes,
        recommended_size,
        fit_note,
        fit_preference,
        occasion,
    )

    fallback_sizes = [size for size in available_sizes if size != recommended_size]
    if fallback_sizes:
        fallback_size = _pick_adjacent_available_size(fallback_sizes, recommended_size)
    else:
        fallback_size = recommended_size

    return {
        'product_id': product.id,
        'product_name': product.name,
        'recommended_size': recommended_size,
        'fallback_size': fallback_size,
        'fit_confidence': confidence,
        'return_risk': return_risk,
        'why': explanation,
        'available_sizes': available_sizes,
        'bundle_suggestions': bundle_suggestions,
    }
