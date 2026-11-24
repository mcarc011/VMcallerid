import importlib.util,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch

class CallerDetailsTests(unittest.TestCase):
 def load(self,base='https://caller.example.com'):
  spec=importlib.util.spec_from_file_location('detail_client',Path(__file__).resolve().parents[1]/'caller_details.py');module=importlib.util.module_from_spec(spec)
  with patch.dict(sys.modules,{'streamlit':SimpleNamespace(secrets={'CALLER_ID_API_BASE_URL':base,'CALLER_ID_API_KEY':'synthetic-key'})}):spec.loader.exec_module(module)
  return module
 def test_authenticated_on_demand_request_whitelists_response(self):
  m=self.load();response=Mock(status_code=200);response.json.return_value={'status':'matched','patients':[{'name':'Ana','patient_no':123,'private_field':'secret'}]}
  with patch.object(m.requests,'post',return_value=response) as post:
   value=m.get_patient_details('+13055550123')
  self.assertEqual(value['patients'][0]['patient_no'],'123');self.assertNotIn('private_field',str(value));self.assertFalse(post.call_args.kwargs['allow_redirects'])
  self.assertEqual(post.call_args.kwargs['json'],{'phone':'+13055550123'})
 def test_untrusted_url_and_phone_never_contact_backend(self):
  for url in ['http://example.com','https://user:password@example.com','https://example.com?key=bad']:
   m=self.load(url)
   with patch.object(m.requests,'post') as post:
    self.assertEqual(m.get_patient_details('+13055550123')['status'],'unavailable');post.assert_not_called()
  m=self.load()
  with patch.object(m.requests,'post') as post:
   self.assertEqual(m.get_patient_details('+442055550123')['status'],'unsupported');post.assert_not_called()
