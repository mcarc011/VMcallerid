import json
import os
import time
from pathlib import Path

import requests
import streamlit as st
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / "ringcentral.env", override=True)

API_URL = os.getenv(
    "CALLER_ID_API_URL",
    "http://127.0.0.1:5002"
).rstrip("/")

API_KEY = os.getenv("CALLER_ID_API_KEY", "")

ACTIVE_CALLS_FILE = BASE_DIR / "active_calls.json"


st.set_page_config(
    page_title="Vision Unlimited Caller ID",
    page_icon="☎️",
    layout="wide"
)


def load_calls():
    try:
        with ACTIVE_CALLS_FILE.open(
            "r", encoding="utf-8"
        ) as f:
            records = json.load(f)

        return records if isinstance(records, list) else []

    except (OSError, ValueError):
        return []


def refresh_metrics():
    """Keep the last successful result if the API is unavailable."""
    now = time.monotonic()

    if now - st.session_state.get("metrics_attempt", -100) < 30:
        return

    st.session_state["metrics_attempt"] = now

    if not API_KEY:
        st.session_state["metrics_error"] = (
            "CALLER_ID_API_KEY is missing from ringcentral.env."
        )
        return

    try:
        response = requests.get(
            f"{API_URL}/api/appointments-created-today",
            headers={"X-API-Key": API_KEY},
            timeout=(2, 5)
        )
        response.raise_for_status()
        data = response.json()

        if not isinstance(data.get("by_username"), list):
            raise ValueError("Invalid metrics response")

        st.session_state["appointment_metrics"] = data
        st.session_state["metrics_error"] = None

    except (requests.RequestException, ValueError):
        st.session_state["metrics_error"] = (
            "Appointment counts could not refresh. "
            "Any displayed counts are from the last successful update."
        )


def refresh_message_metrics():
    now = time.monotonic()

    if now - st.session_state.get("message_attempt", -100) < 30:
        return

    st.session_state["message_attempt"] = now

    try:
        response = requests.get(
            f"{API_URL}/api/messages-responded-today",
            headers={"X-API-Key": API_KEY},
            timeout=(2, 5)
        )
        response.raise_for_status()
        data = response.json()

        if not isinstance(data.get("total"), int):
            raise ValueError("Invalid message metrics response")

        st.session_state["message_metrics"] = data
        st.session_state["message_error"] = None

    except (requests.RequestException, ValueError):
        st.session_state["message_error"] = (
            "No se pudo actualizar el conteo. "
            "Los datos visibles corresponden a la última actualización."
        )

st.title("Vision Unlimited Caller ID")
placeholder = st.empty()

while True:
    calls = load_calls()
    refresh_metrics()
    refresh_message_metrics()

    with placeholder.container():
        st.subheader("Actividad de hoy")

        metrics = st.session_state.get("appointment_metrics")
        error = st.session_state.get("metrics_error")

        appointment_col, message_col = st.columns(2)

        with appointment_col:
            with st.container(border=True):
                st.metric(
                    "Citas creadas hoy",
                    metrics["total"] if metrics else "—"
                )

                if metrics:
                    st.caption(
                        f"Fecha: {metrics['date']} · "
                        f"Actualizado: {metrics['updated_at']}"
                    )

                    rows = [
                        {
                            "Usuario": item["username"],
                            "Citas creadas": item[
                                "appointments_created"
                            ]
                        }
                        for item in metrics["by_username"]
                    ]

                    if rows:
                        st.dataframe(
                            rows,
                            hide_index=True,
                            use_container_width=True
                        )
                    else:
                        st.info("No se han creado citas hoy.")

                if error:
                    st.warning(error)

        with message_col:
            with st.container(border=True):
                message_metrics = st.session_state.get(
                    "message_metrics"
                )

                st.metric(
                    "Mensajes contestados desde VUM hoy",
                    message_metrics["total"]
                    if message_metrics else "—"
                )

                st.caption(
                    "Mensajes entrantes marcados como contestados "
                    "hoy, excluyendo respuestas automáticas."
                )

                if message_metrics:
                    st.caption(
                        f"Fecha: {message_metrics['date']} · "
                        f"Actualizado: {message_metrics['updated_at']}"
                    )

                message_error = st.session_state.get(
                    "message_error"
                )

                if message_error:
                    st.warning(message_error)

        st.divider()
        st.subheader(f"Calls: {len(calls)}")

        # Keep eight slots, expanding when more calls are present.
        slots = max(8, ((len(calls) + 3) // 4) * 4)

        for start in range(0, slots, 4):
            columns = st.columns(4)

            for offset, column in enumerate(columns):
                slot = start + offset

                with column:
                    with st.container(border=True):
                        if slot >= len(calls):
                            st.markdown("### Available")
                            continue

                        call = calls[slot]

                        st.subheader(
                            call.get("phone") or "Unknown"
                        )
                        st.write(
                            "**Status:**",
                            call.get("state") or ""
                        )

                        patients = call.get("patients") or []

                        if not patients:
                            status = call.get(
                                "patient_lookup_status"
                            )

                            if status == "loading":
                                st.info("Looking up patient…")
                            elif status == "error":
                                st.warning("Patient lookup failed")
                            elif status == "ignored":
                                st.info("Office / outbound number")
                            else:
                                st.info("No matching patient")

                        for patient in patients:
                            st.write(patient.get("name") or "")
                            st.write(
                                "Patient #:",
                                patient.get("patient_no", "")
                            )
                            st.write(
                                "Last visit:",
                                patient.get("last_visit") or "None"
                            )
                            st.write(
                                "Next appointment:",
                                patient.get("next_appointment")
                                or "None"
                            )
                            st.write(
                                "Location:",
                                patient.get("location") or "None"
                            )
                            st.write(
                                "Order:",
                                patient.get("flowstatus") or "None"
                            )
                            st.divider()

    time.sleep(1)
