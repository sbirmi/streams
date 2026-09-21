import unittest

from app.markdown_renderer import MarkdownRenderer, ReferenceRule


class MarkdownRendererTestCase(unittest.TestCase):
    def test_markdown_links_and_safe_autolinks_render(self) -> None:
        html = MarkdownRenderer().render("**bold** [docs](https://example.test) <https://safe.test> https://bare.test/path")
        self.assertIn("<strong>bold</strong>", html)
        self.assertIn('href="https://example.test"', html)
        self.assertIn('href="https://safe.test"', html)
        self.assertIn('href="https://bare.test/path"', html)

    def test_unsafe_html_and_urls_are_removed(self) -> None:
        html = MarkdownRenderer().render('<script>alert(1)</script> [bad](javascript:alert(1))')
        self.assertNotIn("<script", html)
        self.assertNotIn("javascript:", html)

    def test_references_skip_links_and_code(self) -> None:
        rules = [ReferenceRule("foo", r"\bFoo([0-9]+)\b", "https://foo.test/{1}", "Foo{1}")]
        html = MarkdownRenderer(rules).render("Foo123 `Foo456` [Foo789](https://already.test)")
        self.assertIn('href="https://foo.test/123"', html)
        self.assertIn("<code>Foo456</code>", html)
        self.assertIn('href="https://already.test"', html)
        self.assertNotIn("foo.test/456", html)
        self.assertNotIn("foo.test/789", html)

    def test_internal_references_require_existing_objects(self) -> None:
        renderer = MarkdownRenderer(stream_lookup=lambda value: value == "known")
        html = renderer.render("Stream:known Stream:missing")
        self.assertIn('href="/?focus=stream:known"', html)
        self.assertIn("Stream:missing", html)
