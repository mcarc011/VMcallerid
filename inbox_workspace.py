"""Whatsappy-style inbox component. Credentials never enter component arguments."""
import re,time
from pathlib import Path
import requests
import streamlit as st
from streamlit.components.v1 import declare_component

_workspace=declare_component('ale_staff_inbox',path=str(Path(__file__).with_name('inbox_ui')))


def filters_for(value):
    value=value if isinstance(value,dict) else {}
    channel=value.get('channel','ALL');days=value.get('days',90);recipient=value.get('recipient','')
    if channel not in {'ALL','SMS','WHATSAPP'} or type(days) is not int or days not in {30,90,365}:raise ValueError('Invalid history filter')
    if not isinstance(recipient,str) or len(recipient)>40 or (recipient and not re.fullmatch(r'\+?[0-9 ().-]{7,40}',recipient)):raise ValueError('Enter a valid phone number to search older history.')
    return {'channel':channel,'days':days,'recipient':recipient}


def process_action(action,conversations,call):
    """Only explicitly selected, authenticated conversation scopes can be changed."""
    if not isinstance(action,dict) or not isinstance(action.get('id'),str) or not re.fullmatch(r'[a-f0-9]{32}',action['id']):raise ValueError('Invalid inbox action')
    kind=action.get('type');result={'id':action['id'],'type':kind,'ok':False}
    if kind=='filter':return {**result,'ok':True,'filters':filters_for(action),'message':''}
    if kind=='refresh':
        selected=action.get('selected_phone')
        if selected and not any(c.get('phone')==selected for c in conversations):raise ValueError('Select an available conversation first.')
        return {**result,'ok':True,'selected':selected,'message':'Conversations refreshed.'}
    scope=(action.get('channel'),action.get('phone'),action.get('sender'))
    if not any((c.get('channel'),c.get('phone'),c.get('sender'))==scope for c in conversations):raise ValueError('Select an available conversation first.')
    channel,phone,sender=scope
    if kind=='select':return {**result,'ok':True,'selected':phone,'message':''}
    result.update(channel=channel,phone=phone,sender=sender)
    if kind=='send':
        text=action.get('text');request_id=action.get('request_id')
        if not isinstance(text,str) or not 1<=len(text.strip())<=3000 or not isinstance(request_id,str) or not re.fullmatch(r'[a-f0-9]{32}',request_id):raise ValueError('Enter a reply of up to 3000 characters.')
        response=call('POST','/ale/messages/send',json={'channel':channel,'to':phone,'sender':sender,'text':text.strip(),'request_id':request_id})
    elif kind=='mode':
        if type(action.get('paused')) is not bool:raise ValueError('Invalid conversation mode')
        response=call('POST','/ale/threads/mode',json={'channel':channel,'phone':phone,'sender':sender,'paused':action['paused']})
    elif kind=='archive':
        response=call('POST','/ale/messages/archive',json={'channel':channel,'phone':phone,'sender':sender})
    else:raise ValueError('Unsupported inbox action')
    try:data=response.json()
    except ValueError:data={}
    if response.status_code!=200:
        detail=data.get('detail')
        result['message']=detail if isinstance(detail,str) else 'Request failed. Check Sinch before retrying a send.'
        return result
    result['ok']=True
    if kind=='send':result['message']='Reply accepted by provider. Ale is paused for staff handling.'+(' Database synchronization needs review; do not resend.' if data.get('database_sync_pending') else '')
    if kind=='mode':result['message']='Ale paused for this conversation.' if action['paused'] else 'Ale resumed for future messages. Existing opt-outs remain in effect.'
    if kind=='archive':
        import json
        result['key']=json.dumps(list(scope),separators=(',',':'));result['message']='Conversation archived. History retained.'
    return result


def draw_workspace(call):
    filters=filters_for(st.session_state.get('_ale_workspace_filters'))
    cache=st.session_state.get('_ale_workspace_cache')
    errors={}
    try:
        if not cache or cache['filters']!=filters or time.monotonic()-cache['time']>=9:
            response=call('GET','/messages/history',params={k:v for k,v in filters.items() if v!=''})
            if response.status_code!=200:raise requests.RequestException('History unavailable')
            data=response.json()
            if not isinstance(data.get('conversations'),list):raise ValueError('Invalid history response')
            cache={'filters':filters,'time':time.monotonic(),'data':data};st.session_state['_ale_workspace_cache']=cache
    except PermissionError:
        st.session_state.pop('_ale_workspace_cache',None);st.error('Messaging sign-in expired. Sign in again.');return
    except (requests.RequestException,ValueError):
        if not cache:st.error('Could not load the inbox. Refresh or check the messaging service.');return
        errors['refresh']='Refresh unavailable. Showing the last loaded messages.'
    data=cache['data'];conversations=data.get('conversations',[])
    from patient_names import with_patient_names
    conversations,name_error=with_patient_names(conversations,preferred=st.session_state.get('_ale_workspace_selected'))
    if name_error:errors['patient_names']=name_error
    errors={**data.get('errors',{}),**errors}
    action=_workspace(conversations=conversations,filters=filters,errors=errors,result=st.session_state.get('_ale_workspace_result'),height=740,key='ale_workspace_component',default=None)
    if not isinstance(action,dict):return
    event_id=action.get('id');handled=st.session_state.get('_ale_workspace_handled',[])
    if not isinstance(event_id,str) or event_id in handled:return
    # Mark before dispatch: fragment refreshes must never replay a provider write.
    st.session_state['_ale_workspace_handled']=(handled+[event_id])[-100:]
    try:
        result=process_action(action,conversations,call)
        if result.get('selected'):st.session_state['_ale_workspace_selected']=result['selected']
        if result.get('filters'):st.session_state['_ale_workspace_filters']=result['filters']
        if result['ok']:st.session_state.pop('_ale_workspace_cache',None)
    except PermissionError:
        st.session_state.pop('_ale_workspace_cache',None);st.error('Messaging sign-in expired.');return
    except ValueError as error:result={'id':event_id,'type':action.get('type'),'ok':False,'message':str(error)}
    except requests.RequestException:result={'id':event_id,'type':action.get('type'),'ok':False,'message':'Request outcome unknown. Check Sinch before retrying a send; this action will not be replayed automatically.'}
    st.session_state['_ale_workspace_result']=result
    st.rerun(scope='fragment')
