"""Safe server-side Markdown and reference rendering."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Callable, Iterable
from urllib.parse import quote, urlparse

import bleach
import markdown


ALLOWED_TAGS = {
    "a", "blockquote", "br", "code", "del", "em", "h1", "h2", "h3", "h4",
    "hr", "li", "ol", "p", "pre", "strong", "ul",
}
ALLOWED_ATTRIBUTES = {"a": ["href", "title", "rel", "target"]}
SAFE_SCHEMES = {"http", "https", "mailto"}


@dataclass(frozen=True)
class ReferenceRule:
    name: str
    pattern: str
    url: str
    display: str = "{0}"
    case_sensitive: bool = True

    def compiled(self) -> re.Pattern[str]:
        return re.compile(self.pattern, 0 if self.case_sensitive else re.IGNORECASE)


AUTO_LINK_RULE = ReferenceRule(
    "autolink",
    r'(?<![\w/"\'=])((?:https?://|mailto:)[^\s<]*[A-Za-z0-9/#])',
    "{0}",
)


def _safe_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme.lower() in SAFE_SCHEMES and bool(parsed.netloc or parsed.scheme == "mailto")


def _render_url(template: str, match: re.Match[str]) -> str | None:
    try:
        values = [match.group(0), *[quote(group or "", safe="") for group in match.groups()]]
        url = template.format(*values)
    except (IndexError, KeyError, ValueError):
        return None
    return url if _safe_url(url) else None


class _ReferenceTextParser(HTMLParser):
    """Apply reference rules to text nodes while preserving protected markup."""

    def __init__(self, rules: Iterable[ReferenceRule], resolver: Callable[[str, str], str | None]):
        super().__init__(convert_charrefs=False)
        self.rules = [(rule.compiled(), rule) for rule in rules]
        self.resolver = resolver
        self.output: list[str] = []
        self.protected_depth = 0

    def _text(self, value: str) -> str:
        if self.protected_depth:
            return html.escape(value, quote=False)
        result: list[str] = []
        cursor = 0
        while cursor < len(value):
            selected: tuple[int, int, ReferenceRule, re.Match[str]] | None = None
            for regex, rule in self.rules:
                match = regex.search(value, cursor)
                if match and (selected is None or match.start() < selected[0]):
                    selected = (match.start(), match.end(), rule, match)
            if selected is None:
                result.append(html.escape(value[cursor:], quote=False))
                break
            start, end, rule, match = selected
            result.append(html.escape(value[cursor:start], quote=False))
            url = _render_url(rule.url, match)
            if rule.name in {"stream", "comment"}:
                url = self.resolver(rule.name, match.group(1))
            if url is None:
                result.append(html.escape(value[start:end], quote=False))
            else:
                label = rule.display.format(match.group(0), *match.groups())
                result.append(f'<a href="{html.escape(url, quote=True)}" rel="noreferrer">'
                              f'{html.escape(label, quote=False)}</a>')
            cursor = end
        return "".join(result)

    def handle_data(self, data: str) -> None:
        self.output.append(self._text(data))

    def handle_entityref(self, name: str) -> None:
        self.output.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.output.append(f"&#{name};")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"code", "pre", "a"}:
            self.protected_depth += 1
        rendered_attrs = []
        for key, value in attrs:
            if value is not None:
                rendered_attrs.append(f' {key}="{html.escape(value, quote=True)}"')
        self.output.append("<" + tag + "".join(rendered_attrs) + ">")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        self.output.append(f"</{tag}>")
        if tag in {"code", "pre", "a"}:
            self.protected_depth = max(0, self.protected_depth - 1)

    def handle_comment(self, data: str) -> None:
        return


class MarkdownRenderer:
    """Render untrusted Markdown with optional declarative references."""

    def __init__(self, rules: Iterable[ReferenceRule] = (), stream_lookup=None, comment_lookup=None):
        self.rules = tuple(rules)
        self.stream_lookup = stream_lookup
        self.comment_lookup = comment_lookup

    def render(self, source: str) -> str:
        rendered = markdown.markdown(source, extensions=["fenced_code", "nl2br", "sane_lists"])
        cleaned = bleach.clean(
            rendered, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES,
            protocols=SAFE_SCHEMES, strip=True,
        )
        parser = _ReferenceTextParser(self._all_rules(), self._resolve_reference)
        parser.feed(cleaned)
        parser.close()
        return "".join(parser.output)

    def _all_rules(self) -> tuple[ReferenceRule, ...]:
        builtins = (
            ReferenceRule("stream", r"\bStream:([A-Za-z0-9_-]+)\b", "/?focus=stream:{1}", "Stream:{1}"),
            ReferenceRule("comment", r"\bComment:([A-Za-z0-9_-]+)\b", "/?focus=comment:{1}", "Comment:{1}"),
        )
        return builtins + self.rules + (AUTO_LINK_RULE,)

    def _resolve_reference(self, kind: str, identifier: str) -> str | None:
        if kind == "stream" and self.stream_lookup:
            return "/?focus=stream:" + quote(identifier, safe="") if self.stream_lookup(identifier) else None
        if kind == "comment" and self.comment_lookup:
            return "/?focus=comment:" + quote(identifier, safe="") if self.comment_lookup(identifier) else None
        return None
