import json
import os
import time

import streamlit as st


st.set_page_config(
    page_title="Vision Unlimited Caller ID",
    page_icon="☎️",
    layout="wide"
)


def load_calls():

    if not os.path.exists("active_calls.json"):
        return []

    try:
        with open(
            "active_calls.json",
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    except Exception:
        return []


st.title("Vision Unlimited Caller ID")

placeholder = st.empty()


while True:

    calls = load_calls()

    with placeholder.container():

        st.subheader(
            f"Active Calls: {len(calls)}"
        )

        # 4 columns x 2 rows = 8 call slots
        for start in range(0, 8, 4):

            columns = st.columns(4)

            for offset in range(4):

                slot = start + offset

                with columns[offset]:

                    if slot < len(calls):

                        call = calls[slot]

                        st.markdown(
                            f"### {call.get('phone', 'Unknown')}"
                        )

                        st.write(
                            f"**Status:** {call.get('state', '')}"
                        )

                        patients = call.get(
                            "patients",
                            []
                        )

                        if not patients:

                            st.info(
                                "No matching patient"
                            )

                        for patient in patients:

                            st.markdown(
                                f"**{patient.get('name', '')}**"
                            )

                            st.write(
                                f"Patient #: {patient.get('patient_no', '')}"
                            )

                            st.write(
                                f"Last visit: {patient.get('last_visit', 'None')}"
                            )

                            st.write(
                                f"Next appointment: {patient.get('next_appointment', 'None')}"
                            )

                            st.write(
                                f"Location: {patient.get('location', 'None')}"
                            )

                            st.write(
                                f"Order: {patient.get('flowstatus', 'None')}"
                            )

                            st.divider()

                    else:

                        st.markdown(
                            "### Available"
                        )

    time.sleep(1)
