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



## SMS + WhatsApp inbox

The **SMS + WhatsApp** tab connects server-side to the VM's Ale Messaging service
at `https://vumessaging.ngrok.io` (VM port 5001). Install the unified-inbox VM
update first; updating `C:\apps\RCcallerid\viewer.py` alone does not update this
Streamlit Cloud deployment.

Each staff browser session must sign in to messaging using the existing Ale
Messaging staff username/password. These credentials stay in that server-side
session, are not embedded in URLs or code, and are cleared by caller ID sign-out.
Caller ID login expiry/revocation is checked on every messaging fragment refresh.
Caller extension permissions and call monitoring are unchanged; messaging access
requires the separate staff account and does not inherit the caller API key.

Optionally override the messaging URL in Streamlit **Settings → Secrets**:

```toml
ALE_MESSAGING_URL = "https://vumessaging.ngrok.io"
```

Keep this setting at the TOML root, before any `[section]` headers. No OpenAI,
Sinch, SQL or messaging password belongs in this repository. External URLs must
use HTTPS without embedded credentials or query strings; redirects are refused.
Changing the origin requires staff to sign in again before credentials are sent.
The existing VM basic authentication remains required for all message-history,
reply, pause and resume requests. A public caller ID URL alone never grants
messaging access.

The inbox supports separate SMS/WhatsApp threads, recent history, staff replies,
and pausing/resuming Ale. Staff sends use per-request IDs; uncertain sends need
Sinch review before retrying. SMS opt-outs and WhatsApp reply-window restrictions
are enforced by the VM service. Provider acceptance does not confirm delivery.
