import sys
import os

_pkg_dir = os.path.dirname(os.path.abspath(__file__))
if _pkg_dir not in sys.path:
    sys.path.insert(0, _pkg_dir)

def main():
    # Frozen re-exec entry for the embedded web view (Approach A): the built .exe relaunches
    # itself as `BRL305.exe --web <url> [title]` to host the Edge WebView2 window in its own
    # process, off the Tkinter main loop. Handle this BEFORE importing the GUI so the web
    # subprocess stays light (pywebview only, no CustomTkinter).
    if "--web" in sys.argv:
        import web_launcher
        sys.exit(web_launcher.run_from_args(sys.argv))

    from gui.main_window import App
    from preflight import check_environment
    ok, msg = check_environment()
    if not ok:
        try:
            import tkinter.messagebox as mb
            mb.showerror("Startup", msg)
        except Exception:
            print(msg)
    app = App()
    app.run()


if __name__ == "__main__":
    main()
