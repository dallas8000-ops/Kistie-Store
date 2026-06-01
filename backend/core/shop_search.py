"""Rule-based + optional AI parsing for natural-language shop search."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from django.db.models import Q, QuerySet

logger = logging.getLogger(__name__)

_SIZE_RE = re.compile(
    r'\b(?:size|saizi|eu)?\s*(3[2-9]|[4-5][0-4])\b',
    re.IGNORECASE,
)

_COLOR_HINTS = (
    'black', 'white', 'navy', 'blue', 'red', 'green', 'pink', 'magenta', 'plum',
    'gold', 'beige', 'cream', 'brown', 'grey', 'gray', 'purple', 'orange', 'yellow',
    'maroon', 'burgundy', 'khaki', 'olive', 'coral', 'teal', 'ivory', 'charcoal',
)

_STOPWORDS = frozenset({
    'a', 'an', 'the', 'in', 'on', 'for', 'with', 'and', 'or', 'my', 'me', 'i',
    'want', 'need', 'show', 'find', 'looking', 'dress', 'dresses', 'shirt', 'shoe',
    'shoes', 'size', 'saizi', 'eu', 'under', 'below', 'around', 'about',
})


def _parse_max_price_usd(text: str) -> float | None:
    lower = text.lower()
    patterns = (
        r'(?:under|below|max|less than)\s*\$?\s*(\d+(?:\.\d+)?)',
        r'\$\s*(\d+(?:\.\d+)?)\s*(?:or less|max)',
    )
    for pattern in patterns:
        match = re.search(pattern, lower)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
    return None


def parse_search_query(raw: str) -> dict[str, Any]:
    """Extract EU size, colors, price cap, and remaining keyword terms."""
    text = (raw or '').strip()
    if not text:
        return {
            'original': '',
            'terms': [],
            'eu_size': '',
            'colors': [],
            'max_price_usd': None,
            'source': 'empty',
        }

    eu_size = ''
    size_match = _SIZE_RE.search(text)
    if size_match:
        eu_size = size_match.group(1)
        text = _SIZE_RE.sub(' ', text)

    colors = [c for c in _COLOR_HINTS if re.search(rf'\b{re.escape(c)}\b', text, re.I)]
    max_price = _parse_max_price_usd(text)

    scrubbed = text.lower()
    for color in colors:
        scrubbed = re.sub(rf'\b{re.escape(color)}\b', ' ', scrubbed)
    scrubbed = re.sub(r'\$?\d+(?:\.\d+)?', ' ', scrubbed)
    scrubbed = re.sub(r'[^\w\s]', ' ', scrubbed)

    terms = []
    for token in scrubbed.split():
        if len(token) < 2 or token in _STOPWORDS:
            continue
        if token not in terms:
            terms.append(token)

    return {
        'original': raw.strip(),
        'terms': terms,
        'eu_size': eu_size,
        'colors': colors,
        'max_price_usd': max_price,
        'source': 'rules',
    }


def parse_search_query_ai(raw: str) -> dict[str, Any] | None:
    """Optional AI parse for phrases like \"blue dress size 38\"."""
    text = (raw or '').strip()
    if len(text) < 4 or len(text.split()) < 2:
        return None

    from django.conf import settings

    if not (getattr(settings, 'OPENAI_API_KEY', '') or getattr(settings, 'GEMINI_API_KEY', '')):
        return None

    from core.ai_utils import chat_complete

    prompt = (
        'Parse a fashion shop search query. Reply with JSON only, no markdown:\n'
        '{"terms":["keyword"],"eu_size":"38 or empty","colors":["blue"],"max_price_usd":null}\n'
        'eu_size must be an even EU integer 32-54 or empty string. '
        'max_price_usd is a number or null.\n\n'
        f'Query: {text}'
    )
    result = chat_complete([{'role': 'user', 'content': prompt}], max_tokens=120)
    if not result:
        return None

    try:
        cleaned = result.strip()
        if cleaned.startswith('```'):
            cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', cleaned, flags=re.I)
        data = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        logger.warning('AI shop search parse failed for: %s', text[:80])
        return None

    terms = [str(t).strip().lower() for t in (data.get('terms') or []) if str(t).strip()]
    eu_size = str(data.get('eu_size') or '').strip()
    if eu_size and not re.fullmatch(r'3[2-9]|[4-5][0-4]', eu_size):
        eu_size = ''

    colors = [str(c).strip().lower() for c in (data.get('colors') or []) if str(c).strip()]
    max_price = data.get('max_price_usd')
    if max_price is not None:
        try:
            max_price = float(max_price)
        except (TypeError, ValueError):
            max_price = None

    return {
        'original': text,
        'terms': terms,
        'eu_size': eu_size,
        'colors': colors,
        'max_price_usd': max_price,
        'source': 'ai',
    }


def merge_parsed(rule: dict[str, Any], ai: dict[str, Any] | None) -> dict[str, Any]:
    if not ai:
        return rule
    merged = dict(rule)
    if ai.get('eu_size') and not merged.get('eu_size'):
        merged['eu_size'] = ai['eu_size']
    for color in ai.get('colors') or []:
        if color not in merged['colors']:
            merged['colors'].append(color)
    for term in ai.get('terms') or []:
        if term not in merged['terms']:
            merged['terms'].append(term)
    if merged.get('max_price_usd') is None and ai.get('max_price_usd') is not None:
        merged['max_price_usd'] = ai['max_price_usd']
    if ai.get('source') == 'ai' and (
        ai.get('eu_size') or ai.get('colors') or ai.get('terms')
    ):
        merged['source'] = 'rules+ai'
    return merged


def apply_parsed_search(products: QuerySet, parsed: dict[str, Any]) -> QuerySet:
    """Filter queryset using parsed search structure; fallback to plain text if empty parse."""
    if not parsed.get('original'):
        return products

    has_structure = bool(
        parsed.get('terms')
        or parsed.get('eu_size')
        or parsed.get('colors')
        or parsed.get('max_price_usd') is not None
    )

    if not has_structure:
        q = parsed['original']
        return products.filter(
            Q(name__icontains=q)
            | Q(description__icontains=q)
            | Q(color__icontains=q)
            | Q(category__name__icontains=q)
        )

    qs = products
    if parsed.get('eu_size'):
        qs = qs.filter(sizes__icontains=parsed['eu_size'])

    if parsed.get('max_price_usd') is not None:
        qs = qs.filter(price_usd__lte=parsed['max_price_usd'])

    for color in parsed.get('colors') or []:
        qs = qs.filter(
            Q(color__icontains=color)
            | Q(name__icontains=color)
            | Q(description__icontains=color)
        )

    for term in parsed.get('terms') or []:
        qs = qs.filter(
            Q(name__icontains=term)
            | Q(description__icontains=term)
            | Q(color__icontains=term)
            | Q(category__name__icontains=term)
            | Q(sizes__icontains=term)
        )

    return qs


def smart_shop_search(products: QuerySet, raw: str) -> tuple[QuerySet, dict[str, Any]]:
    """Parse query (rules + optional AI) and return filtered queryset + parse metadata."""
    text = (raw or '').strip()
    if not text:
        return products, {'original': '', 'source': 'empty', 'terms': [], 'eu_size': '', 'colors': []}

    rule = parse_search_query(text)
    ai = None
    if len(text.split()) >= 2 and not (rule['eu_size'] and rule['colors'] and rule['terms']):
        ai = parse_search_query_ai(text)

    parsed = merge_parsed(rule, ai)
    return apply_parsed_search(products, parsed), parsed


def search_hint_label(parsed: dict[str, Any]) -> str:
    """Human-readable summary for the shop UI."""
    if not parsed.get('original'):
        return ''
    parts = []
    if parsed.get('colors'):
        parts.append(', '.join(parsed['colors']))
    if parsed.get('eu_size'):
        parts.append(f'EU {parsed["eu_size"]}')
    if parsed.get('terms'):
        parts.append(' '.join(parsed['terms']))
    if parsed.get('max_price_usd') is not None:
        parts.append(f'under USD {parsed["max_price_usd"]:g}')
    if not parts:
        return parsed['original']
    label = ' · '.join(parts)
    if parsed.get('source') in ('ai', 'rules+ai'):
        return f'{label} (smart match)'
    return label
