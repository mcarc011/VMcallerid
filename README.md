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

The Messages page uses the existing caller ID login, with no second messaging
password prompt. Install `Ale-Caller-Login-Update.zip` on the VM to enable the
bridge. Streamlit signs short-lived, single-use requests server-side using its
existing `CALLER_ID_API_KEY`; the VM reads the matching key from
`C:\apps\RCcallerid\ringcentral.env`. No new Streamlit secret is needed.
The key never enters browser JavaScript, URLs, or component arguments.

Caller login expiry/revocation is checked before each messaging action. All
caller accounts have messaging access by default; set `messaging_access = false`
in an individual user's secrets section to deny it. Messaging access includes
all conversations in the inbox, independently of call extension permissions.
The standalone Whatsappy `/gui` page retains its staff password.

Signed requests bind the exact HTTP method, path, query and body; expire after
75 seconds; and reject replayed nonces. Only inbox history, status, replies,
thread mode and archive endpoints accept this delegation. Keep VM time synced.
After rotating the caller API key, update both sides and restart Ale Messaging.

Optionally set root-level `ALE_MESSAGING_URL` in Streamlit Secrets to an HTTPS
origin without credentials or query strings. The default is
`https://vumessaging.ngrok.io`. Redirects are refused. No OpenAI, Sinch, SQL or
messaging password belongs in this repository. A public caller ID URL alone
never grants access to conversations.

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
caller login and server-side messaging authorization.

Validation includes the existing login tests, workspace action/scope checks,
patient-name client tests, and five JavaScript interaction tests for selected
channel, escaped text, per-conversation drafts and no sends during refresh.
Browser screenshot verification was unavailable in the development environment.

Direct Messages workspace link: https://vmcallerid.streamlit.app/?view=messages


## Stable messaging page

Messages checks for new messages every five seconds while the page is open,
using an independently scheduled Streamlit fragment. Each check revalidates caller
login. History reads have a four-second cache; no separate browser timer or direct
browser-to-VM credentials are used. Visible changes are rendered in the inbox;
unchanged lists/messages retain DOM nodes, the selected thread, draft and reading
position. New messages scroll into view only when the reader was already near
the bottom. Repeated updates never replay staff sends. Manual Refresh remains
available. Caller ID dashboard timers do not run on Messages. The inbox offers
Last 4 hours and Last 24 hours, with 24 hours as the default.
**Take over** and staff replies pause only the selected channel+patient+business
number thread. **Resume Ale** applies to future messages in that same thread;
other conversations are unaffected and SMS opt-outs are still enforced.




## On-demand caller ID details in Messages

Click a conversation's phone number in its header to open a native dialog styled
as a side panel. It shows the same caller lookup's patient number, DOB, last visit,
next appointment, location, optical/contact-lens order status/dates and latest
text today. Shared numbers show separate patient cards. Close or Escape returns
to the inbox without sending anything or losing the draft.

Install `Ale-Caller-Patient-Details.zip` on the VM caller ID backend. The endpoint
requires the existing caller API key and reuses `lookup_family` and
`serialize_patient`; no new SQL lookup or identity rules are introduced. Only
explicitly clicked conversations request details. Server-side login/permission
checks and conversation scope validation precede the call. Keys never enter the
component. Responses whitelist displayed fields; patient data is never passed to
Ale's model. The existing name-only endpoint remains name-only.

Pending lookups run on a dedicated two-thread executor, bounded to 16 outstanding
phones, with a 60-second successful-result cache. The panel polls pending results
on existing five-second messaging updates for at most 45 seconds. Closing clears
rendered details and late results cannot reopen it. Only caller ID monitoring
restarts for the VM install; voice, messaging, bookingapp and ngrok stay running.
