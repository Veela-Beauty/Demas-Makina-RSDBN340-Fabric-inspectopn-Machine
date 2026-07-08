from preflight import check_environment


def test_check_environment_ok():
    ok, msg = check_environment()
    assert ok is True
    assert msg == "ok"
