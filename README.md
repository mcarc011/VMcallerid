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

The **Messages** workspace connects server-side to the VM's Ale Messaging service
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


## Full-page inbox and caller ID patient names

Choose **Messages** in the sidebar to open the full-height Whatsappy-style inbox.
The conversation list has channel/status filters and name/phone search. Message
history and the reply composer stay in the right pane; drafts remain scoped to
each channel, patient phone, and business sender. Caller ID dashboards remain in
**Caller ID** and are not rendered above the inbox. Messages are plain text,
never interpolated HTML. Credentials and caller API keys never enter the component
arguments or browser JavaScript. Fragment refreshes never replay a send action.

Patient labels use the existing VM caller ID `lookup_family` function through
`POST /api/messaging/patient-names`, protected by its existing API key. Install the
separate VM name-endpoint update in `C:\apps\RCcallerid` and restart caller ID
monitoring. No caller API key, database password or patient data should be committed.
The endpoint returns names only, keeps the existing duplicate/family/office-number
rules, and does not alter patient verification for orders or bookings. Shared
numbers show multiple patient names. Unsupported international numbers are not
matched by their last ten digits. Until lookup is available, phone numbers and
existing WhatsApp profile names remain usable.

Names populate progressively in batches of up to 25, with selected conversations
prioritized. The VM uses two separate background workers so name queries do not
consume the live caller lookup executor. Cached names expire after five minutes.
No name lookup, registration, booking, or message send runs without the existing
caller login and messaging staff authorization.

Validation includes the existing login tests, workspace action/scope checks,
patient-name client tests, and five JavaScript interaction tests for selected
channel, escaped text, per-conversation drafts and no sends during refresh.
Browser screenshot verification was unavailable in the development environment.

Direct Messages workspace link: https://vmcallerid.streamlit.app/?view=messages


## Stable messaging page

Messages uses no automatic rerun timer. Choosing a conversation, scrolling,
searching loaded names, and typing stay entirely within the inbox component.
Click **Refresh** to fetch new messages and updated patient names; new messages do
not appear automatically. Explicit filter changes and staff send/pause/resume
requests still contact the server, with caller login rechecked for each action.
Caller ID live-call refresh behavior is unchanged and does not run on Messages.
**Take over** and staff replies pause only the selected channel+patient+business
number thread. **Resume Ale** applies to future messages in that same thread;
other conversations are unaffected and SMS opt-outs are still enforced.
