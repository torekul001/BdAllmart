"""Sanitize public course descriptions before storing or rendering HTML."""
import html
import re
from html.parser import HTMLParser
from urllib.parse import urlparse


def video_code(value):
    from course_service import youtube_id
    code = youtube_id(value)
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", code):
        raise ValueError("Enter a valid YouTube video link or 11-character video ID.")
    return code


class CourseHTML(HTMLParser):
    tags = {"p", "br", "div", "h2", "h3", "h4", "strong", "b", "em", "i", "u", "ul", "ol", "li", "blockquote", "a", "img", "iframe"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output = []

    def handle_starttag(self, tag, attrs):
        if tag not in self.tags:
            return
        attrs = dict(attrs)
        safe = {}
        if tag == "a":
            url = attrs.get("href", "")
            if urlparse(url).scheme in {"http", "https"}:
                safe = {"href": url, "rel": "noopener noreferrer"}
        elif tag == "img":
            url = attrs.get("src", "")
            if not (url.startswith("/static/course-images/") or urlparse(url).scheme == "https"):
                return
            safe = {"src": url, "alt": attrs.get("alt", "Course image"), "loading": "lazy"}
        elif tag == "iframe":
            parsed = urlparse(attrs.get("src", ""))
            if parsed.scheme != "https" or parsed.netloc != "www.youtube.com" or not re.fullmatch(r"/embed/[A-Za-z0-9_-]{11}", parsed.path):
                return
            safe = {"src": attrs["src"], "title": "Course video", "allowfullscreen": "", "loading": "lazy"}
        rendered = "".join(' {}="{}"'.format(k, html.escape(v, quote=True)) for k, v in safe.items())
        self.output.append("<" + tag + rendered + ">")

    def handle_endtag(self, tag):
        if tag in self.tags and tag not in {"img", "br"}:
            self.output.append("</" + tag + ">")

    def handle_data(self, data):
        self.output.append(html.escape(data))


def sanitize_course_content(value):
    parser = CourseHTML()
    parser.feed(str(value or ""))
    return "".join(parser.output)
