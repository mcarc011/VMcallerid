import sys,types,unittest,importlib.util
from pathlib import Path
from unittest.mock import patch,Mock
class Box:
 def __enter__(self):return self
 def __exit__(self,*args):pass
 def button(self,*args,**kwargs):return False
class FakeStreamlit:
 def __init__(self,auth=False):self.secrets={'ALE_MESSAGING_URL':'http://127.0.0.1:5001'};self.session_state={'_ale_staff_auth':('staff','synthetic-secret'),'_ale_inbox_base':'http://127.0.0.1:5001'} if auth else {};self.display=[]
 def expander(self,*args,**kwargs):return Box()
 def form(self,*args,**kwargs):return Box()
 def container(self,*args,**kwargs):return Box()
 def columns(self,*args):return Box(),Box()
 def text_input(self,label,**kwargs):return ''
 def text_area(self,*args,**kwargs):return ''
 def form_submit_button(self,*args):return False
 def selectbox(self,label,options,**kwargs):return options[kwargs.get('index',0)]
 def __getattr__(self,name):return lambda *args,**kwargs:self.display.extend(str(a) for a in args)
def load(st):
 path=Path(__file__).resolve().parents[1]/'caller_messages.py'
 spec=importlib.util.spec_from_file_location('caller_messages_test',path);module=importlib.util.module_from_spec(spec)
 with patch.dict(sys.modules,streamlit=st):spec.loader.exec_module(module)
 return module
class CallerTests(unittest.TestCase):
 def test_no_messaging_data_requested_until_staff_signin(self):
  st=FakeStreamlit();module=load(st)
  with patch.object(module.requests,'request') as request,patch.object(module.requests,'get') as get:
   module.messaging_panel([]);request.assert_not_called();get.assert_not_called()
 def test_auth_is_server_side_and_message_is_plain_text(self):
  st=FakeStreamlit(True);module=load(st)
  response=Mock(status_code=200);response.json.return_value={'errors':{},'conversations':[{'channel':'SMS','phone':'+13055550123','sender':'+13055550124','messages':[{'direction':'inbound','message':'<script>unsafe</script>','timestamp':'synthetic'}]}]}
  with patch.object(module.requests,'request',return_value=response) as request:
   module.messaging_panel([])
   self.assertEqual(request.call_args.args[0],'GET');self.assertEqual(request.call_args.kwargs['auth'],('staff','synthetic-secret'))
   self.assertFalse(request.call_args.kwargs['allow_redirects']);self.assertIn('<script>unsafe</script>',st.display);self.assertFalse(any('synthetic-secret' in v for v in st.display))
 def test_cloud_url_requires_https_and_no_embedded_credentials(self):
  for url in ['http://example.com','https://staff:password@example.com','https://example.com/?secret=x']:
   st=FakeStreamlit(True);st.secrets['ALE_MESSAGING_URL']=url;module=load(st)
   with patch.object(module.requests,'request') as request:
    module.messaging_panel([]);request.assert_not_called()
 def test_cloud_origin_change_requires_new_staff_signin(self):
  st=FakeStreamlit(True);st.secrets['ALE_MESSAGING_URL']='https://example.ngrok-free.app';module=load(st)
  with patch.object(module.requests,'request') as request:
   module.messaging_panel([]);request.assert_not_called();self.assertNotIn('_ale_staff_auth',st.session_state)
 def test_messaging_fragment_rechecks_caller_login_before_fetch(self):
  import ast
  tree=ast.parse((Path(__file__).resolve().parents[1]/'viewer.py').read_text(encoding='utf-8'))
  fragment=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='messaging_view')
  self.assertEqual(fragment.body[0].value.func.id,'require_current_login')
 def test_cloud_default_uses_https_without_vm_file_dependency(self):
  st=FakeStreamlit();st.secrets={};module=load(st)
  with patch.object(module.requests,'request') as request:
   module.messaging_panel(default_url='https://vumessaging.ngrok.io');request.assert_not_called()
   self.assertFalse(any('not configured' in value for value in st.display))
 def test_messages_poll_only_their_fragment_every_five_seconds(self):
  import ast
  tree=ast.parse((Path(__file__).resolve().parents[1]/'viewer.py').read_text(encoding='utf-8'))
  fragment=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='messaging_view')
  decorator=fragment.decorator_list[0]
  self.assertIsInstance(decorator,ast.Call)
  self.assertEqual(next(k.value.value for k in decorator.keywords if k.arg=='run_every'),'5s')
 def test_caller_login_skips_extra_staff_login(self):
  st=FakeStreamlit();st.session_state['username']='operator';st.secrets.update(CALLER_ID_API_KEY='synthetic-key',users={'operator':{}});module=load(st)
  guard=Mock();draw=Mock();send=Mock(return_value=Mock(status_code=200))
  with patch.dict(sys.modules,{'login_state':types.SimpleNamespace(require_current_login=guard),'inbox_workspace':types.SimpleNamespace(draw_workspace=draw),'caller_bridge':types.SimpleNamespace(send_request=send)}):
   module.messaging_panel(full_page=True,caller_login=True)
   draw.assert_called_once();self.assertTrue(draw.call_args.kwargs['caller_login']);draw.call_args.args[0]('GET','/messages/history');self.assertEqual(send.call_args.args[2:4],('synthetic-key','operator'));self.assertEqual(guard.call_count,2)
   self.assertFalse(any('Sign in with the Ale' in text or 'synthetic-key' in text for text in st.display))
 def test_caller_account_can_be_denied_messaging_without_network(self):
  st=FakeStreamlit();st.session_state['username']='operator';st.secrets.update(CALLER_ID_API_KEY='synthetic-key',users={'operator':{'messaging_access':False}});module=load(st)
  draw=Mock();send=Mock()
  with patch.dict(sys.modules,{'login_state':types.SimpleNamespace(require_current_login=Mock()),'inbox_workspace':types.SimpleNamespace(draw_workspace=draw),'caller_bridge':types.SimpleNamespace(send_request=send)}):
   module.messaging_panel(full_page=True,caller_login=True);draw.assert_not_called();send.assert_not_called()
 def test_caller_login_must_validate_before_messaging(self):
  class NotLoggedIn(BaseException):pass
  st=FakeStreamlit();module=load(st);draw=Mock()
  with patch.dict(sys.modules,{'login_state':types.SimpleNamespace(require_current_login=Mock(side_effect=NotLoggedIn())),'inbox_workspace':types.SimpleNamespace(draw_workspace=draw),'caller_bridge':types.SimpleNamespace(send_request=Mock())}):
   with self.assertRaises(NotLoggedIn):module.messaging_panel(full_page=True,caller_login=True)
   draw.assert_not_called()
if __name__=='__main__':unittest.main()


