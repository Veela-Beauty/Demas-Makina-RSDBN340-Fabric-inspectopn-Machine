"""Turn a missing Win7 DLL / TLS problem into a readable message, not a silent crash.

The Prime Textile tunnel needs ssl (OpenSSL DLLs), sqlite3, and certifi. On a bare Win7 x86 box
these can be missing (no VC++ 2015-2022 x86 runtime). Checking them up front lets the app
say exactly what to install instead of crashing when the operator first hits Save."""


def check_environment():
    """Returns (ok, message). Verifies the imports the tunnel needs are loadable."""
    problems = []
    for mod in ("ssl", "sqlite3", "certifi"):
        try:
            __import__(mod)
        except Exception as e:  # noqa: BLE001
            problems.append("{}: {}".format(mod, e))
    if problems:
        return (False,
                "Missing runtime components (install VC++ 2015-2022 x86): " + "; ".join(problems))
    return True, "ok"
