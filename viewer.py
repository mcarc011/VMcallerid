import json
import os

import bcrypt
import streamlit as st


# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="Vision Unlimited Caller ID",
    page_icon="☎️",
    layout="wide",
    initial_sidebar_state="expanded"
)


BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

ACTIVE_CALLS_FILE = os.path.join(
    BASE_DIR,
    "active_calls.json"
)


# ============================================================
# STYLE
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 2rem;
        max-width: 1800px;
    }

    .call-card {
        border: 1px solid #d7dce2;
        border-radius: 12px;
        padding: 16px;
        min-height: 320px;
        background: white;
        margin-bottom: 12px;
    }

    .call-phone {
        font-size: 1.45rem;
        font-weight: 700;
        margin-bottom: 2px;
    }

    .call-state {
        font-size: .9rem;
        font-weight: 600;
        margin-bottom: 12px;
    }

    .patient-name {
        font-size: 1.05rem;
        font-weight: 700;
        margin-top: 8px;
    }

    .patient-info {
        font-size: .90rem;
        line-height: 1.55;
    }

    .empty-card {
        border: 1px dashed #c7ccd2;
        border-radius: 12px;
        padding: 16px;
        min-height: 320px;
        opacity: .65;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# AUTHENTICATION
# ============================================================

def authenticate(username, password):

    users = st.secrets.get(
        "users",
        {}
    )

    if username not in users:
        return False

    user = users[
        username
    ]

    stored_hash = user[
        "password_hash"
    ]

    try:

        return bcrypt.checkpw(

            password.encode(
                "utf-8"
            ),

            stored_hash.encode(
                "utf-8"
            )
        )

    except Exception:

        return False


def login_screen():

    # Center the login form
    left, center, right = st.columns(
        [1.5, 1, 1.5]
    )

    with center:

        st.markdown(
            "<h2 style='text-align:center; margin-bottom:0;'>Vision Unlimited</h2>",
            unsafe_allow_html=True
        )
        
        st.markdown(
            "<p style='text-align:center; color:#777; margin-top:4px;'>Caller ID</p>",
            unsafe_allow_html=True
        )

        with st.form(
            "login_form"
        ):

            username = st.text_input(
                "Username"
            )

            password = st.text_input(
                "Password",
                type="password"
            )

            submitted = st.form_submit_button(
                "Sign in",
                use_container_width=True
            )

        if submitted:

            username = (
                username
                .strip()
                .lower()
            )

            if authenticate(
                username,
                password
            ):

                st.session_state[
                    "authenticated"
                ] = True

                st.session_state[
                    "username"
                ] = username

                st.rerun()

            else:

                st.error(
                    "Invalid username or password."
                )


# ============================================================
# CHECK LOGIN
# ============================================================

if not st.session_state.get(
    "authenticated",
    False
):

    login_screen()

    st.stop()


username = st.session_state[
    "username"
]

user = st.secrets[
    "users"
][username]


display_name = user.get(
    "display_name",
    username
)

allowed_extensions = [
    str(x)
    for x in user.get(
        "extensions",
        []
    )
]

role = user.get(
    "role",
    "operator"
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        f"### {display_name}"
    )

    st.caption(
        f"User: {username}"
    )

    st.caption(
        f"Role: {role}"
    )

    st.divider()

    if st.button(
        "Sign out",
        use_container_width=True
    ):

        st.session_state.clear()

        st.rerun()


# ============================================================
# EXTENSION NAME HELPERS
# ============================================================

def extension_name(
    extension_id
):

    try:

        names = st.secrets[
            "extension_names"
        ]

        return names.get(
            str(extension_id),
            str(extension_id)
        )

    except Exception:

        return str(
            extension_id
        )


# ============================================================
# LOAD CALL DATA
# ============================================================

import requests

def load_calls():

    url = (
        st.secrets["CALLER_ID_API_BASE_URL"].rstrip("/")
        + "/api/active-calls"
    )

    try:

        response = requests.get(
            url,
            headers={
                "X-API-Key":
                    st.secrets["CALLER_ID_API_KEY"]
            },
            timeout=3
        )

        response.raise_for_status()

        return response.json()

    except Exception as e:

        st.error(
            f"Caller ID server unavailable: {e}"
        )

        return []

# ============================================================
# FILTER BY USER EXTENSION
# ============================================================

def filter_calls_by_extension(
    calls,
    extension_id
):

    extension_id = str(
        extension_id
    ).strip()

    if not extension_id:
        return []

    visible = []

    for call in calls:

        call_extensions = {
            str(x).strip()
            for x in call.get(
                "active_extension_ids",
                []
            )
        }

        if extension_id in call_extensions:
            visible.append(call)

    return visible


# ============================================================
# HEADER
# ============================================================

header_left, header_right = st.columns(
    [4, 1]
)

with header_left:

    st.title(
        "Vision Unlimited Caller ID"
    )


with header_right:

    st.success(
        "● Connected"
    )


# ============================================================
# EXTENSION SELECTOR
# ============================================================

default_extension = ""

if allowed_extensions and "*" not in allowed_extensions:
    default_extension = allowed_extensions[0]

left, middle, right = st.columns(
    [1, 1.2, 4]
)

with middle:

    typed_extension = st.text_input(
        "Extension ID",
        value=st.session_state.get(
            "typed_extension",
            default_extension
        ),
        placeholder="Extension ID"
    )

typed_extension = typed_extension.strip()

st.session_state["typed_extension"] = typed_extension


# ============================================================
# FORMAT HELPERS
# ============================================================

def readable_date(value):

    if not value:
        return "None"

    try:

        from datetime import datetime

        dt = datetime.fromisoformat(
            value
        )

        return dt.strftime(
            "%m/%d/%Y"
        )

    except Exception:

        return str(
            value
        )


def readable_datetime(value):

    if not value:
        return "None"

    try:

        from datetime import datetime

        dt = datetime.fromisoformat(
            value
        )

        return dt.strftime(
            "%m/%d/%Y %I:%M %p"
        )

    except Exception:

        return str(
            value
        )


# ============================================================
# RENDER ONE CALL CARD
# ============================================================
if typed_extension:
    st.caption(
        f"Viewing RingCentral Extension ID: {typed_extension}"
    )
def render_call(call):

    phone = call.get(
        "phone",
        "Unknown"
    )

    state = call.get(
        "state",
        "Unknown"
    )

    patients = call.get(
        "patients",
        []
    )

    lookup_status = call.get(
        "patient_lookup_status",
        "complete"
    )

    extension_ids = call.get(
        "active_extension_ids",
        []
    )

    extensions_text = ", ".join(
        extension_name(x)
        for x in extension_ids
    )

    st.markdown(
        f"### ☎ {phone}"
    )

    st.markdown(
        f"**{state}**"
    )

    if extensions_text:

        st.caption(
            f"Extension(s): {extensions_text}"
        )

    st.divider()

    # ========================================================
    # PATIENT LOOKUP STILL RUNNING
    # ========================================================

    if lookup_status == "loading":

        st.info(
            "Looking up patient..."
        )

        return

    # ========================================================
    # DATABASE LOOKUP ERROR
    # ========================================================

    if lookup_status == "error":

        st.error(
            "Patient lookup failed."
        )

        return

    # ========================================================
    # LOOKUP FINISHED BUT NO MATCH
    # ========================================================

    if not patients:

        st.warning(
            "Phone number not found in patient database."
        )

        return

    # ========================================================
    # PATIENT MATCHES
    # ========================================================

    for index, patient in enumerate(
        patients
    ):

        if index > 0:
            st.divider()

        st.markdown(
            f"#### {patient.get('name', 'Unknown')}"
        )

        st.write(
            f"**Patient #:** "
            f"{patient.get('patient_no', '')}"
        )

        st.write(
            "**Last Visit:** "
            + readable_date(
                patient.get(
                    "last_visit"
                )
            )
        )

        st.write(
            "**Next Appointment:** "
            + readable_datetime(
                patient.get(
                    "next_appointment"
                )
            )
        )

        location = patient.get(
            "location"
        )

        if location:

            st.write(
                f"**Location:** {location}"
            )

        order = patient.get(
            "flowstatus"
        )

        if order:

            st.write(
                f"**Active Order:** {order}"
            )
            
# ============================================================
# LIVE CALL AREA
# ============================================================
@st.fragment(run_every="1s")
def live_calls():

    calls = load_calls()

    visible_calls = filter_calls_by_extension(
        calls,
        typed_extension
    )

    # ========================================================
    # FILTER CALLS
    # ========================================================

    if "*" in allowed_extensions:

        all_extensions = set()

        for call in calls:

            for extension_id in call.get(
                "active_extension_ids",
                []
            ):
                all_extensions.add(
                    str(extension_id)
                )

        manager_options = {
            "All Extensions": None
        }

        for extension_id in sorted(
            all_extensions
        ):
            manager_options[
                extension_name(extension_id)
            ] = extension_id

        selected_label = st.selectbox(
            "Filter by extension",
            list(manager_options.keys()),
            key="manager_extension_filter"
        )

        manager_extension = manager_options[
            selected_label
        ]

        visible_calls = filter_calls_by_extension(
            calls,
            manager_extension
        )

    else:

        visible_calls = filter_calls(
            calls,
            selected_extension
        )

    # ========================================================
    # HEADER
    # ========================================================

    if len(visible_calls) == 0:

        st.info(
            "No active calls."
        )

        return

    if len(visible_calls) == 1:

        st.subheader(
            "1 Active Call"
        )

    else:

        st.subheader(
            f"{len(visible_calls)} Active Calls"
        )

    # ========================================================
    # DYNAMIC CALL GRID
    # ========================================================
    
    columns_per_row = 3
    
    for start in range(
        0,
        len(visible_calls),
        columns_per_row
    ):
    
        row_calls = visible_calls[
            start:
            start + columns_per_row
        ]
    
        # Always create 3 columns so one call
        # doesn't stretch across the screen.
        columns = st.columns(
            columns_per_row
        )
    
        for index, call in enumerate(
            row_calls
        ):
    
            with columns[index]:
    
                with st.container(
                    border=True
                ):
    
                    render_call(
                        call
                    )

live_calls()
