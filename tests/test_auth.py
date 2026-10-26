import copy
import importlib
import sys
import types
import unittest
from unittest.mock import patch

from auth_sessions import COOKIE_NAME, LoginSessions

SECRET = "test-only-signing-key-not-for-production"
USERS = {"operator": {"password_hash": "test-password-hash", "extensions": ["101"]}}


class TokenTests(unittest.TestCase):
    def setUp(self):
        self.sessions = LoginSessions(SECRET)
        self.token = self.sessions.issue("operator", USERS)

    def test_restores_after_new_server_instance(self):
        self.assertEqual(LoginSessions(SECRET).verify(self.token, USERS), "operator")

    def test_tampering_is_rejected(self):
        self.assertIsNone(self.sessions.verify(self.token + "tampered", USERS))

    def test_expired_and_future_tokens_are_rejected(self):
        with patch("itsdangerous.timed.TimestampSigner.get_timestamp", return_value=1000):
            token = self.sessions.issue("operator", USERS)
        for now in [999, 1000 + self.sessions.max_age + 1]:
            with self.subTest(now=now), patch(
                "itsdangerous.timed.TimestampSigner.get_timestamp", return_value=now,
            ):
                self.assertIsNone(self.sessions.verify(token, USERS))

    def test_valid_until_absolute_seven_day_limit(self):
        with patch("itsdangerous.timed.TimestampSigner.get_timestamp", return_value=1000):
            token = self.sessions.issue("operator", USERS)
        with patch("itsdangerous.timed.TimestampSigner.get_timestamp", return_value=605800):
            self.assertEqual(self.sessions.verify(token, USERS), "operator")

    def test_password_change_invalidates_token(self):
        users = copy.deepcopy(USERS)
        users["operator"]["password_hash"] = "replacement-hash"
        self.assertIsNone(self.sessions.verify(self.token, users))

    def test_removed_disabled_and_rotated_key(self):
        self.assertIsNone(self.sessions.verify(self.token, {}))
        users = copy.deepcopy(USERS)
        users["operator"]["disabled"] = True
        self.assertIsNone(self.sessions.verify(self.token, users))
        self.assertIsNone(LoginSessions("other-key").verify(self.token, USERS))

    def test_malformed_signed_payloads_are_rejected(self):
        for payload in [[], None, "operator", {}, {"username": [], "version": 1}]:
            with self.subTest(payload=payload):
                self.assertIsNone(self.sessions.verify(self.sessions.serializer.dumps(payload), USERS))
        for token in [None, "", 1, "not-a-token"]:
            self.assertIsNone(self.sessions.verify(token, USERS))

    def test_no_credentials_in_cookie_payload(self):
        payload = self.sessions.serializer.loads(self.token)
        self.assertEqual(set(payload), {"username", "version"})
        self.assertNotIn(USERS["operator"]["password_hash"], str(payload))
        self.assertNotIn(SECRET, str(payload))

    def test_configuration_validation(self):
        for days in [0, 31, True, 1.5, "7"]:
            with self.assertRaises(ValueError):
                LoginSessions(SECRET, days)
        with self.assertRaises(ValueError):
            LoginSessions("")


class Stopped(Exception):
    pass


class Rerun(Exception):
    pass


class LoginFlowTests(unittest.TestCase):
    def setUp(self):
        self.st = types.ModuleType("streamlit")
        self.st.session_state = {}
        self.st.secrets = {"users": copy.deepcopy(USERS), "CALLER_ID_API_KEY": SECRET}
        self.st.info = lambda message: None
        self.st.stop = lambda: (_ for _ in ()).throw(Stopped())
        self.st.rerun = lambda **kwargs: (_ for _ in ()).throw(Rerun())
        self.result = None
        self.calls = []
        manager = types.SimpleNamespace(cookie_manager=self.cookie_component)
        stx = types.ModuleType("extra_streamlit_components")
        stx.CookieManager = lambda **kwargs: manager
        self.modules = patch.dict(sys.modules, {"streamlit": self.st, "extra_streamlit_components": stx})
        self.modules.start()
        self.addCleanup(self.modules.stop)
        sys.modules.pop("login_state", None)
        self.flow = importlib.import_module("login_state")

    def cookie_component(self, **kwargs):
        self.calls.append(kwargs)
        return self.result

    def test_waits_for_browser_before_showing_login(self):
        with self.assertRaises(Stopped):
            self.flow.restore_login()
        self.assertNotIn("authenticated", self.st.session_state)

    def test_reload_restores_cookie_without_password(self):
        token = self.flow.sessions().issue("operator", USERS)
        self.result = {COOKIE_NAME: token}
        self.flow.restore_login()
        self.assertTrue(self.st.session_state["authenticated"])
        self.assertEqual(self.st.session_state["username"], "operator")
        # A later server rerun validates the saved token, without resetting expiry.
        self.result = None
        self.flow.restore_login()
        self.assertEqual(self.st.session_state["_auth_token"], token)

    def test_empty_or_forged_cookie_does_not_authenticate(self):
        for cookies in [{}, {COOKIE_NAME: "forged"}]:
            self.st.session_state = {"authenticated": True}
            self.result = cookies
            self.flow.restore_login()
            self.assertFalse(self.st.session_state["authenticated"])

    def test_login_waits_for_cookie_write_acknowledgement(self):
        self.flow.begin_login("operator")
        with self.assertRaises(Stopped):
            self.flow.restore_login()
        call = self.calls[-1]
        self.assertEqual(call["method"], "set")
        self.assertTrue(call["options"]["secure"])
        self.assertEqual(call["options"]["sameSite"], "strict")
        self.assertNotIn("authenticated", self.st.session_state)
        self.result = True
        with self.assertRaises(Rerun):
            self.flow.restore_login()
        self.flow.restore_login()
        self.assertTrue(self.st.session_state["authenticated"])

    def test_logout_blocks_stale_cookie_and_clears_call_data(self):
        self.st.session_state.update(authenticated=True, last_good_calls=["private-call"])
        self.flow.begin_logout()
        self.assertNotIn("last_good_calls", self.st.session_state)
        self.result = {COOKIE_NAME: self.flow.sessions().issue("operator", USERS)}
        with self.assertRaises(Stopped):
            self.flow.restore_login()
        self.assertEqual(self.calls[-1]["method"], "delete")
        self.result = True
        with self.assertRaises(Rerun):
            self.flow.restore_login()
        self.result = {}
        self.flow.restore_login()
        self.assertFalse(self.st.session_state["authenticated"])

    def test_fragments_force_login_after_revocation(self):
        self.st.session_state["_auth_token"] = self.flow.sessions().issue("operator", USERS)
        self.flow.require_current_login()
        self.st.secrets["users"] = {}
        with self.assertRaises(Rerun):
            self.flow.require_current_login()
        self.assertNotIn("_auth_token", self.st.session_state)
        self.assertIsNone(self.st.session_state["_auth_pending"]["token"])


if __name__ == "__main__":
    unittest.main()
