import tempfile
import webbrowser
import misaka
import sys
import os

class SearchReportRenderer(misaka.HtmlRenderer):
    # override the default renderer to add line breaks after every paragraph
    def paragraph(self, text):
        return "<p>%s</p><br><br>" % text

def render(md_path):
    renderer = SearchReportRenderer()
    md = misaka.Markdown(renderer)
    with open(md_path, "r", encoding='utf-8') as f:
        return md(f.read())

def render_and_view(md_path):
    html_path = os.path.join(*os.path.split(md_path)[:-1], os.path.splitext(os.path.split(md_path)[-1])[0] + ".html")
    with open(html_path, "w", encoding='utf-8') as f:
        f.writelines(render(md_path))

    webbrowser.open(html_path)

if __name__ == "__main__":
    render_and_view(sys.argv[1])