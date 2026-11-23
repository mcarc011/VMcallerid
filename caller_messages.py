"""Protected SMS/WhatsApp panel for the existing Streamlit caller ID viewer."""
import time,uuid,hashlib,os
from urllib.parse import urlparse
from pathlib import Path
import requests
import streamlit as st


def messaging_panel(calls=None,default_url=None):
    # Credentials are entered by each staff viewer, never inherited from a server
    # .env into a publicly accessible dashboard or embedded in an iframe URL.
    with st.expander('SMS + WhatsApp conversations',expanded=False):
        auth=st.session_state.get('_ale_staff_auth')
        configured=os.environ.get('ALE_MESSAGING_URL','').strip()
        if not configured:
            try:configured=str(st.secrets.get('ALE_MESSAGING_URL','')).strip()
            except Exception:configured=''
        if not configured and default_url:configured=str(default_url).strip()
        if configured:
            parsed=urlparse(configured)
            local=parsed.hostname in {'127.0.0.1','localhost','::1'}
            if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('','/') or (parsed.scheme!='https' and not (parsed.scheme=='http' and local)):
                st.error('ALE_MESSAGING_URL must be an HTTPS origin without credentials, path or query.');return
            base=configured.rstrip('/')
        else:
            port_file=Path('C:/apps/whatsappy/.ale-private/port.txt')
            if not port_file.is_file():
                st.info('Messaging is not configured for this deployment. Set ALE_MESSAGING_URL to the VM messaging HTTPS/ngrok address in Streamlit secrets.');return
            try:port=int(port_file.read_text().strip())
            except Exception:st.error('Messaging port configuration unavailable.');return
            if not 1024<=port<=65535:st.error('Messaging port configuration invalid.');return
            base=f'http://127.0.0.1:{port}'
        if auth and st.session_state.get('_ale_inbox_base')!=base:
            st.session_state.pop('_ale_staff_auth',None);st.session_state.pop('_ale_inbox_data',None);auth=None
        def call(method,path,**kwargs):
            response=requests.request(method,base+path,auth=st.session_state.get('_ale_staff_auth'),timeout=(3,15),allow_redirects=False,headers={'ngrok-skip-browser-warning':'true'},**kwargs)
            if response.status_code in (401,403):
                st.session_state.pop('_ale_staff_auth',None);st.session_state.pop('_ale_inbox_data',None)
                raise PermissionError('Staff sign-in required')
            return response
        if not auth:
            st.caption('Sign in with the Ale Messaging staff account. Messaging history requires its own staff authorization.')
            with st.form('ale_staff_login'):
                user=st.text_input('Messaging staff username',value='staff')
                password=st.text_input('Messaging staff password',type='password')
                login=st.form_submit_button('Sign in to messaging')
            if login:
                try:
                    response=requests.get(base+'/ale/status',auth=(user,password),timeout=(3,10),allow_redirects=False,headers={'ngrok-skip-browser-warning':'true'})
                    if response.status_code!=200:st.error('Messaging sign-in failed.');return
                    st.session_state['_ale_staff_auth']=(user,password);st.session_state['_ale_inbox_base']=base;st.rerun()
                except requests.RequestException:st.error('Messaging service unavailable.')
            return
        left,right=st.columns(2)
        if left.button('Refresh messages',key='ale_refresh'):
            st.session_state.pop('_ale_inbox_data',None)
        if right.button('Sign out of messaging',key='ale_logout'):
            for name in list(st.session_state):
                if name in ['_ale_staff_auth','_ale_inbox_data','_ale_reply_request','_ale_inbox_scope','_ale_inbox_base'] or name.startswith('ale_reply_text_'):st.session_state.pop(name,None)
            st.rerun()
        channel=st.selectbox('Channel',['ALL','SMS','WHATSAPP'],key='ale_inbox_channel')
        days=st.selectbox('History window (days)',[30,90,365],index=1,key='ale_inbox_days')
        active=sorted({str(c.get('phone') or '') for c in (calls or []) if c.get('phone')})
        active_phone=st.selectbox('Active caller',['All recent conversations']+active,key='ale_active_phone') if active else 'All recent conversations'
        search=st.text_input('Find patient phone number (optional)',key='ale_inbox_phone').strip()
        if not search and active_phone!='All recent conversations':search=active_phone
        params={'channel':channel,'days':days}
        if search:params['recipient']=search
        scope=(channel,days,search)
        cache=st.session_state.get('_ale_inbox_data')
        try:
            if not cache or cache['scope']!=scope or time.monotonic()-cache['time']>10:
                response=call('GET','/messages/history',params=params)
                if response.status_code!=200:st.error('Could not load conversations. Check the phone filter and messaging service.');return
                cache={'scope':scope,'time':time.monotonic(),'data':response.json()};st.session_state['_ale_inbox_data']=cache
            data=cache['data']
            for error in data.get('errors',{}).values():st.warning(error)
            conversations=data.get('conversations',[])
            if not conversations:st.info('No conversations in this history window.');return
            def label(i):
                c=conversations[i];return f"{c['channel']} · {c.get('name') or c['phone']} · {c['phone']} · business {c['sender']}"
            index=st.selectbox('Conversation',range(len(conversations)),format_func=label,key='ale_conversation_index')
            c=conversations[index]
            st.caption(('Staff handling / Ale paused' if c.get('paused') else 'Ale enabled')+' · '+c['channel'])
            # Plain text rendering: messages can never inject markup or scripts.
            with st.container(height=350):
                for message in c.get('messages',[]):
                    st.caption(('Staff/Ale → patient' if message['direction']=='outbound' else 'Patient → office')+' · '+str(message.get('timestamp','')))
                    st.text(str(message.get('message','')))
            col1,col2=st.columns(2)
            mode=None
            if col1.button('Take over / pause Ale',key='ale_pause'):mode=True
            if col2.button('Resume Ale',key='ale_resume'):mode=False
            if mode is not None:
                result=call('POST','/ale/threads/mode',json={'channel':c['channel'],'phone':c['phone'],'sender':c['sender'],'paused':mode})
                if result.status_code==200:st.session_state.pop('_ale_inbox_data',None);st.rerun()
                else:st.error('Could not change Ale mode.')
            composer=hashlib.sha256((c['channel']+'|'+c['phone']+'|'+c['sender']).encode()).hexdigest()[:20]
            with st.form('ale_reply_form_'+composer,clear_on_submit=False):
                reply=st.text_area('Staff reply (sends through the selected channel)',max_chars=3000,key='ale_reply_text_'+composer)
                submit=st.form_submit_button('Send reply and pause Ale')
            if submit and reply.strip():
                signature=(c['channel'],c['phone'],c['sender'],reply.strip())
                request=st.session_state.get('_ale_reply_request')
                if not request or request['signature']!=signature:request={'signature':signature,'id':uuid.uuid4().hex};st.session_state['_ale_reply_request']=request
                result=call('POST','/ale/messages/send',json={'channel':c['channel'],'to':c['phone'],'sender':c['sender'],'text':reply.strip(),'request_id':request['id']})
                response=result.json()
                if result.status_code==200:
                    st.success('Reply accepted by provider. Ale is paused for this conversation.')
                    if response.get('database_sync_pending'):st.warning('Database synchronization needs review; do not resend this reply.')
                    st.session_state.pop('_ale_inbox_data',None)
                else:st.error(response.get('detail','Send failed. Check Sinch before retrying.'))
        except PermissionError:st.error('Messaging sign-in expired. Sign in again.');return
        except requests.RequestException:st.error('Messaging request unavailable or send outcome unknown. Check Sinch before retrying a send.');return
        except (ValueError,KeyError,IndexError):st.error('Messaging response unavailable. Refresh the panel.');return
