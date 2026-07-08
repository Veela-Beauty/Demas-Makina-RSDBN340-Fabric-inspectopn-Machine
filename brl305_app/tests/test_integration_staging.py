"""Live round-trip against a real newjacquard site using the shift-login (session) auth.
Skipped unless the ERP_* env vars are set, so the default suite stays hermetic. Run with:

  ERP_URL=... ERP_USR=... ERP_PWD=... ERP_TEST_WO=... ERP_TEST_ROLL=... \
      python -m pytest tests/test_integration_staging.py -v
"""
import os

import pytest

from erpnext_client import ErpnextClient

URL = os.environ.get("ERP_URL")
USR = os.environ.get("ERP_USR")
PWD = os.environ.get("ERP_PWD")
WO = os.environ.get("ERP_TEST_WO")
ROLL = os.environ.get("ERP_TEST_ROLL")

pytestmark = pytest.mark.skipif(not all([URL, USR, PWD, WO, ROLL]),
                                reason="staging env vars not set")


def test_round_trip_against_staging():
    c = ErpnextClient(URL)
    c.login(USR, PWD)
    assert c.user == USR
    jc = c.resolve_job_card(WO, ROLL)
    ctx = c.get_context(jc)
    assert ctx["job_card"] == jc
    assert "defect_types" in ctx
    out = c.save_inspection(jc, 87.45, 21.76, [])
    assert "grade" in out
