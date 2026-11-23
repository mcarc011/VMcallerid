import base64,hashlib,json,unittest
from unittest.mock import patch,Mock
from caller_bridge import prepare_request,send_request
class BridgeTests(unittest.TestCase):
 def test_signed_request_contains_no_shared_key_or_password(self):
  request=prepare_request('GET','https://messages.example/messages/history','synthetic-key','operator',params={'recipient':'+13055550123'})
  header=request.headers['X-Ale-Caller-Authorization'];self.assertNotIn('synthetic-key',header);self.assertNotIn('Authorization',request.headers)
  value=json.loads(base64.urlsafe_b64decode(header.split('.')[0]+'=='))
  self.assertEqual(value['user'],'operator');self.assertEqual(value['target'],request.path_url);self.assertEqual(value['body'],hashlib.sha256(b'').hexdigest())
 def test_signature_binds_the_actual_prepared_json_bytes(self):
  request=prepare_request('POST','https://messages.example/ale/messages/send','synthetic-key','operator',json={'text':'Hola, señor'})
  value=json.loads(base64.urlsafe_b64decode(request.headers['X-Ale-Caller-Authorization'].split('.')[0]+'=='))
  self.assertEqual(value['body'],hashlib.sha256(request.body).hexdigest())
 def test_transport_refuses_redirects(self):
  with patch('caller_bridge.requests.Session') as session:
   session.return_value.__enter__.return_value.send.return_value=Mock(status_code=200)
   send_request('GET','https://messages.example/ale/status','synthetic-key','operator')
   self.assertFalse(session.return_value.__enter__.return_value.send.call_args.kwargs['allow_redirects'])
if __name__=='__main__':unittest.main()
