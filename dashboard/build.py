"""Assemble the dashboard: page + script + data -> artifact page and a GitHub Pages index.html."""
import pathlib
root = pathlib.Path(__file__).parent
page = (root / "src/page.html").read_text()
app = (root / "src/app.js").read_text().replace("__DATA__", (root.parent / "results/dashboard_data.json").read_text())
body = page + "\n<script>\n" + app + "\n</script>\n"
(root / "artifact.html").write_text(body)  # page body without the html/head wrapper
(root.parent / "docs").mkdir(exist_ok=True)
(root.parent / "docs/index.html").write_text(
    '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
    + body.replace("</style>", "</style></head><body>", 1) + "</body></html>\n")
print("built", len(body) // 1024, "KB")
