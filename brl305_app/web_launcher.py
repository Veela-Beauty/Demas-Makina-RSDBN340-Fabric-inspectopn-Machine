"""Separate-process launcher for the embedded Prime Textile web view (Approach A: Edge WebView2 /
Chromium 109). pywebview owns the GUI event loop and must run on the main thread, and the BRL-305
app already owns a Tkinter main loop — so the web window runs here, in its own process. A crash in
the web view therefore can never take down the inspection app.

Entrypoints:
  dev:    python web_launcher.py <url> [title]
  frozen: BRL305.exe --web <url> [title]     (routed here by main.py)
"""
import sys


def _parse(argv):
    args = [a for a in argv[1:] if a != "--web"]
    url = args[0] if args else ""
    title = args[1] if len(args) > 1 else "Prime Textile"
    return url, title


def run_from_args(argv):
    url, title = _parse(argv)
    if not url:
        print("usage: web_launcher.py <url> [title]")
        return 2
    import webview
    webview.create_window(title, url, width=1180, height=760, min_size=(900, 600))
    # gui='edgechromium' forces the WebView2 backend (Chromium 109 on Win7). We ask explicitly so a
    # missing runtime fails loudly here instead of silently downgrading to the IE/MSHTML engine,
    # which cannot render the Prime Textile v15 desk.
    webview.start(gui="edgechromium")
    return 0


if __name__ == "__main__":
    sys.exit(run_from_args(sys.argv))
