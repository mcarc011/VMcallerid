"""Server-side patient names from the same protected caller ID lookup."""
import time,re
from urllib.parse import urlparse
import requests
import streamlit as st

def with_patient_names(conversations,preferred=None):
    try:
        base=str(st.secrets['CALLER_ID_API_BASE_URL']).strip().replace('%20','').rstrip('/')
        token=str(st.secrets['CALLER_ID_API_KEY']).strip()
    except Exception:return conversations,'Patient names are not configured; phone numbers remain available.'
    parsed=urlparse(base)
    if not token or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('','/') or (parsed.scheme!='https' and not (parsed.scheme=='http' and parsed.hostname in {'127.0.0.1','localhost','::1'})):
        return conversations,'Patient name lookup is not configured securely.'
    cache=st.session_state.setdefault('_ale_patient_name_cache',{});now=time.monotonic();missing=[]
    for c in conversations:
        phone=c.get('phone','')
        if re.fullmatch(r'\+1\d{10}',phone) and (phone not in cache or cache[phone]['expires']<now) and phone not in missing:missing.append(phone)
    if preferred in missing:missing.remove(preferred);missing.insert(0,preferred)
    error=None
    if missing:
        try:
            response=requests.post(base+'/api/messaging/patient-names',json={'phones':missing[:25]},headers={'X-API-Key':token,'ngrok-skip-browser-warning':'true'},timeout=(2,4),allow_redirects=False)
            if response.status_code!=200:raise requests.RequestException('Name lookup unavailable')
            results=response.json().get('results',{})
            for phone,value in results.items():
                if phone not in missing or not isinstance(value,dict):continue
                cache[phone]={'expires':now+(300 if value.get('status')=='matched' else 7),'value':value}
        except (requests.RequestException,ValueError):error='Patient name lookup is waiting for the VM caller ID update or is temporarily unavailable. Conversations remain usable.'
    result=[]
    for c in conversations:
        value=cache.get(c.get('phone'),{}).get('value',{});names=value.get('names',[])
        names=[' '.join(n.split())[:100] for n in names if isinstance(n,str) and n.strip()][:20]
        item={**c,'patient_names':names,'shared_number':bool(value.get('shared'))}
        if names:item['profile_name']=c.get('name');item['name']=names[0]+(' + '+str(len(names)-1) if len(names)>1 else (' · shared number' if item['shared_number'] else ''))
        result.append(item)
    return result,error
