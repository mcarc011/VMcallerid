# VMcallerid

## Persistent login

Successful sign-ins are remembered in this browser for **7 days**, including
page reloads, browser restarts, and Streamlit reconnects/server restarts. Sign
out removes the browser cookie. Password changes, disabled/deleted users, and
signing-key changes invalidate remembered logins. Permissions still come from
the server's current `users` secrets, never from the cookie.

No new secret is required for existing deployments: the existing server-only
`CALLER_ID_API_KEY` signs login tokens with a dedicated application salt.
Optionally configure a separate, stable, random signing key and duration in
Streamlit secrets (keep the same key across restarts and replicas):

```toml
[auth]
cookie_secret = "<a long random secret; never commit the actual value>"
session_days = 7 # integer, 1–30 days; absolute expiry, not renewed by polling
```

Deploy over HTTPS. Cookies are Secure, SameSite=Strict, and scoped to this host
and `/`. Only a username and a keyed password-version fingerprint are stored;
passwords, password hashes, API keys, and call/patient records stay server-side.
The cookie component uses JavaScript, so these cookies cannot be HttpOnly.
Sign out on shared workstations. A previously copied token remains usable until
expiry unless the password/signing key changes or the account is disabled.

After deploying, sign in once to create the new cookie. Browsers must allow
cookies for the app. Streamlit's temporary session state alone is no longer the
source of authentication. Cookie writes/deletes are acknowledged before reruns.

Run the auth regression tests with `python -m unittest discover -s tests -v`.
