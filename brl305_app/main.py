import sys
import os

_pkg_dir = os.path.dirname(os.path.abspath(__file__))
if _pkg_dir not in sys.path:
    sys.path.insert(0, _pkg_dir)

from gui.main_window import App
from preflight import check_environment


def main():
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
