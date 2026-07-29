"""Curated visual systems for Education slide documents.

The identifiers are part of the durable SlideDocument contract.  Agent output
selects one identifier; rendering tokens remain owned by the application so a
model cannot introduce unreadable colour combinations or arbitrary CSS.
"""

DEFAULT_PRESENTATION_THEME = "clear_classroom"

PRESENTATION_THEMES = {
    "clear_classroom": {
        "label": "清朗课堂",
        "description": "留白充足、青绿与暖橙点题，适合常规课堂讲授。",
        "background": "#F4FAF8",
        "surface": "#FFFFFF",
        "primary": "#176D63",
        "accent": "#E99B4B",
        "text": "#203633",
        "muted": "#6B817C",
        "font": "Microsoft YaHei",
    },
    "paper_annotation": {
        "label": "纸张批注",
        "description": "米白纸张、深蓝正文与朱红批注，适合阅读精讲。",
        "background": "#F3EBDD",
        "surface": "#FFF9EE",
        "primary": "#243B5A",
        "accent": "#C9563F",
        "text": "#312E29",
        "muted": "#766D62",
        "font": "Microsoft YaHei",
    },
    "storybook": {
        "label": "童趣绘本",
        "description": "柔和粉彩与圆润图形，适合小学语文故事和习作启发。",
        "background": "#F5F0FF",
        "surface": "#FFFCFA",
        "primary": "#31578C",
        "accent": "#EF7964",
        "secondary": "#71BEB4",
        "text": "#29364C",
        "muted": "#72809A",
        "font": "Microsoft YaHei",
    },
    "dark_focus": {
        "label": "深色聚焦",
        "description": "深蓝底与高对比亮色，适合投影、重点讲解和复盘。",
        "background": "#0F172A",
        "surface": "#17233A",
        "primary": "#67E8F9",
        "accent": "#FBBF24",
        "text": "#F8FAFC",
        "muted": "#CBD5E1",
        "font": "Microsoft YaHei",
    },
}


def presentation_theme(source):
    """Return a trusted theme dictionary for an arbitrary SlideDocument."""
    raw_theme = source.get("theme") if isinstance(source, dict) else {}
    raw_theme = raw_theme if isinstance(raw_theme, dict) else {}
    style = str(
        raw_theme.get("style")
        or raw_theme.get("preset")
        or raw_theme.get("id")
        or DEFAULT_PRESENTATION_THEME
    ).strip()
    if style not in PRESENTATION_THEMES:
        style = DEFAULT_PRESENTATION_THEME
    return style, dict(PRESENTATION_THEMES[style])
