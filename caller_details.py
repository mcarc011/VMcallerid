"""Caller details stay server-authorized, loaded only for a selected conversation."""
import re
from urllib.parse import urlparse
import requests
import streamlit as st

FIELDS=('patient_no','name','dob','last_visit','next_appointment','location','flowstatus','order_date','cl_flowstatus','cl_order_date','latest_text_message','latest_text_time')
def get_patient_details(phone):
    if not isinstance(phone,str) or not re.fullmatch(r'\+1[0-9]{10}',phone):return {'status':'unsupported','patients':[]}
    try:
        base=str(st.secrets['CALLER_ID_API_BASE_URL']).strip().replace('%20','').rstrip('/')
        key=str(st.secrets['CALLER_ID_API_KEY']).strip()
        parsed=urlparse(base)
        if not key or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('','/') or (parsed.scheme!='https' and not (parsed.scheme=='http' and parsed.hostname in {'127.0.0.1','localhost','::1'})):raise ValueError()
        response=requests.post(base+'/api/messaging/patient-details',json={'phone':phone},headers={'X-API-Key':key,'ngrok-skip-browser-warning':'true'},timeout=(2,4),allow_redirects=False)
        if response.status_code==404:return {'status':'needs_update','patients':[]}
        if response.status_code!=200:raise ValueError()
        value=response.json()
        if value.get('status') not in {'pending','matched','not_found','unavailable'}:raise ValueError()
        records=value.get('patients',[])
        if not isinstance(records,list):raise ValueError()
        return {'status':value['status'],'shared':bool(value.get('shared')),'patients':[{k:str(p.get(k) or '')[:2000] for k in FIELDS} for p in records[:20] if isinstance(p,dict)]}
    except (requests.RequestException,ValueError,KeyError,TypeError):return {'status':'unavailable','patients':[]}
