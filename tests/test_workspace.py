import sys,tempfile,unittest,importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch,Mock

def load_module():
 path=Path(__file__).resolve().parents[1]/'inbox_workspace.py';spec=importlib.util.spec_from_file_location('workspace_test',path);module=importlib.util.module_from_spec(spec)
 fake=SimpleNamespace(session_state={})
 with patch.dict(sys.modules,{'streamlit':fake,'streamlit.components':SimpleNamespace(),'streamlit.components.v1':SimpleNamespace(declare_component=lambda *a,**k:None)}):spec.loader.exec_module(module)
 return module
class WorkspaceTests(unittest.TestCase):
 def setUp(self):
  self.module=load_module();self.thread={'channel':'SMS','phone':'+13055550123','sender':'+13055550124'}
 def action(self,**kwargs):return {'id':'a'*32,**self.thread,**kwargs}
 def test_send_scope_and_request_id_passed_without_credentials(self):
  call=Mock();call.return_value.status_code=200;call.return_value.json.return_value={}
  result=self.module.process_action(self.action(type='send',text='Reply',request_id='b'*32),[self.thread],call)
  self.assertTrue(result['ok']);self.assertEqual(call.call_args.args,('POST','/ale/messages/send'));self.assertEqual(call.call_args.kwargs['json']['request_id'],'b'*32);self.assertNotIn('Authorization',str(call.call_args.kwargs))
 def test_unknown_conversation_cannot_send(self):
  call=Mock()
  with self.assertRaises(ValueError):self.module.process_action(self.action(type='send',text='Reply',request_id='b'*32),[],call)
  call.assert_not_called()
 def test_mode_requires_explicit_boolean(self):
  with self.assertRaises(ValueError):self.module.process_action(self.action(type='mode',paused='false'),[self.thread],Mock())
 def test_bad_filter_never_calls_service(self):
  for value in [{'channel':'PRIVATE'},{'days':1000},{'recipient':'https://example.com'}]:
   with self.assertRaises(ValueError):self.module.filters_for(value)
 def test_archiving_preserves_scope(self):
  call=Mock();call.return_value.status_code=200;call.return_value.json.return_value={}
  result=self.module.process_action(self.action(type='archive'),[self.thread],call)
  self.assertTrue(result['ok']);self.assertEqual(call.call_args.kwargs['json'],self.thread)
 def test_failed_send_remains_failed(self):
  call=Mock();call.return_value.status_code=502;call.return_value.json.return_value={'detail':'Acceptance uncertain'}
  result=self.module.process_action(self.action(type='send',text='Reply',request_id='b'*32),[self.thread],call);self.assertFalse(result['ok']);self.assertEqual(call.call_count,1)


 def test_short_windows_and_legacy_session_migration(self):
  self.assertEqual(self.module.filters_for({})['hours'],24)
  self.assertEqual(self.module.filters_for({'hours':4})['days'],1)
  self.assertEqual(self.module.filters_for({'days':90})['hours'],24)
  with self.assertRaises(ValueError):self.module.filters_for({'hours':60})
 def test_latest_activity_filters_threads_and_keeps_context(self):
  from datetime import datetime,timezone
  now=1800000000
  def conversation(age):return {'messages':[{'timestamp':datetime.fromtimestamp(now-80000,timezone.utc).isoformat(),'message':'Earlier context'},{'timestamp':datetime.fromtimestamp(now-age,timezone.utc).isoformat(),'message':'Latest'}]}
  recent=conversation(3600);old=conversation(5*3600)
  self.assertEqual(self.module.recent_conversations([recent,old],4,now),[recent])
  self.assertEqual(len(self.module.recent_conversations([recent,old],24,now)),2)
  self.assertEqual(len(recent['messages']),2)
  self.assertEqual(self.module.recent_conversations([{'messages':[{'timestamp':'invalid'}]}],24,now),[])


 def test_details_require_an_available_conversation(self):
  import sys
  from types import SimpleNamespace
  lookup=Mock(return_value={'status':'pending','patients':[]})
  with patch.dict(sys.modules,{'caller_details':SimpleNamespace(get_patient_details=lookup)}):
   with self.assertRaises(ValueError):self.module.process_action(self.action(type='details'),[],Mock())
   lookup.assert_not_called()
   value=self.module.process_action(self.action(type='details'),[self.thread],Mock())
   self.assertEqual(value['profile']['status'],'pending');lookup.assert_called_once_with(self.thread['phone'])
