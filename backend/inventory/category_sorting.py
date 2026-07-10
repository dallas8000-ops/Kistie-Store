import re


DEFAULT_CATEGORY_NAME = 'Default'

CATEGORY_KEYWORDS = {
    'Purses': (
        'bag',
        'bags',
        'clutch',
        'handbag',
        'hand bag',
        'purse',
        'purses',
        'tote',
        'wallet',
    ),
    'Shoes': (
        'boot',
        'boots',
        'heel',
        'heels',
        'loafer',
        'loafers',
        'sandal',
        'sandals',
        'shoe',
        'shoes',
        'sneaker',
        'sneakers',
        'stiletto',
        'stilettos',
    ),
    'Jewelry': (
        'bracelet',
        'bracelets',
        'earring',
        'earrings',
        'jewel',
        'jewelry',
        'jewellery',
        'necklace',
        'necklaces',
        'ring',
        'rings',
    ),
    'Dresses': (
        'dress',
        'dresses',
        'gown',
        'gowns',
        'midi',
        'mini',
        'maxi',
    ),
    'Suits': (
        'blazer',
        'blazers',
        'pantsuit',
        'pant suit',
        'skirt suit',
        'suit',
        'suits',
        'waistcoat',
    ),
}


def _normalized_tokens(value):
    return set(re.findall(r'[a-z0-9]+', value.lower()))


def infer_category_name(value):
    text = (value or '').strip()
    if not text:
        return DEFAULT_CATEGORY_NAME

    tokens = _normalized_tokens(text)
    compact_text = ' '.join(tokens)
    best_match = (0, DEFAULT_CATEGORY_NAME)

    for category_name, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            normalized_keyword = keyword.lower()
            if ' ' in normalized_keyword:
                if normalized_keyword in compact_text:
                    score += 2
            elif normalized_keyword in tokens:
                score += 1

        if score > best_match[0]:
            best_match = (score, category_name)

    return best_match[1]
