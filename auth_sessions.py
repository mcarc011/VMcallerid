"""Signed, expiring login tokens. No passwords or API keys leave the server."""
import hashlib
import hmac

from itsdangerous import BadData, URLSafeTimedSerializer

COOKIE_NAME = "vmcallerid_session"
DEFAULT_SESSION_DAYS = 7


class LoginSessions:
    def __init__(self, secret, days=DEFAULT_SESSION_DAYS):
        if not isinstance(secret, str) or not secret.strip():
            raise ValueError("A stable authentication signing secret is required")
        if type(days) is not int or not 1 <= days <= 30:
            raise ValueError("Session duration must be an integer from 1 to 30 days")
        self.max_age = days * 24 * 60 * 60
        self.secret = secret.encode("utf-8")
        self.serializer = URLSafeTimedSerializer(
            secret, salt="vmcallerid.login.v1",
            signer_kwargs={"digest_method": hashlib.sha256},
        )

    def _password_version(self, user):
        return hmac.new(
            self.secret, user["password_hash"].encode("utf-8"), hashlib.sha256,
        ).hexdigest()

    def issue(self, username, users):
        return self.serializer.dumps({
            "username": username,
            "version": self._password_version(users[username]),
        })

    def verify(self, token, users):
        if not isinstance(token, str) or not token:
            return None
        try:
            data = self.serializer.loads(token, max_age=self.max_age)
            if not isinstance(data, dict):
                return None
            username = data.get("username")
            version = data.get("version")
            if not isinstance(username, str) or not isinstance(version, str):
                return None
            user = users.get(username)
            if not user or user.get("disabled", False):
                return None
            if not hmac.compare_digest(version, self._password_version(user)):
                return None
            return username
        except (BadData, KeyError, TypeError, ValueError):
            return None
