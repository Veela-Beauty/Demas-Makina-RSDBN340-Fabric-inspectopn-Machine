import web_view_support as wv


def test_normalize_base_adds_scheme_and_strips_slash():
    assert wv.normalize_base("erp.example.com") == "https://erp.example.com"
    assert wv.normalize_base("https://erp.example.com/") == "https://erp.example.com"
    assert wv.normalize_base("  http://x.local/  ") == "http://x.local"
    assert wv.normalize_base("") == ""
    assert wv.normalize_base(None) == ""


def test_build_portal_url():
    assert wv.build_portal_url("erp.example.com", wv.INSPECTION_PATH) == \
        "https://erp.example.com/app/fabric-inspection"
    assert wv.build_portal_url("https://erp.example.com/", "/app") == "https://erp.example.com/app"
    assert wv.build_portal_url("erp.example.com", "") == "https://erp.example.com"
    assert wv.build_portal_url("", "app") == ""


def test_resolve_launch_plan_no_url():
    assert wv.resolve_launch_plan("") == "no_url"
    assert wv.resolve_launch_plan(None) == "no_url"


def test_resolve_launch_plan_browser_when_not_windows():
    plan = wv.resolve_launch_plan("erp.example.com")
    if wv.is_windows():
        assert plan in ("embedded", "browser")
    else:
        assert plan == "browser"


def test_resolve_launch_plan_prefer_embedded_false_is_browser():
    assert wv.resolve_launch_plan("erp.example.com", prefer_embedded=False) == "browser"
