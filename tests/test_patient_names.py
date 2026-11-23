import unittest,sys,importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
class NameClientTests(unittest.TestCase):
 def load(self):
  st=SimpleNamespace(secrets={'CALLER_ID_API_BASE_URL':'https://caller.example','CALLER_ID_API_KEY':'synthetic-only'},session_state={})
  path=Path(__file__).resolve().parents[1]/'patient_names.py';spec=importlib.util.spec_from_file_location('name_client_test',path);module=importlib.util.module_from_spec(spec)
  with patch.dict(sys.modules,streamlit=st):spec.loader.exec_module(module)
  return module
 def test_labels_use_caller_lookup_and_show_shared_number(self):
  module=self.load();response=Mock(status_code=200);response.json.return_value={'results':{'+13055550123':{'status':'matched','names':['Ana Example','Luis Example'],'shared':True}}}
  with patch.object(module.requests,'post',return_value=response) as call:
   result,error=module.with_patient_names([{'phone':'+13055550123','name':'WhatsApp name'}])
   self.assertIsNone(error);self.assertEqual(result[0]['name'],'Ana Example + 1');self.assertEqual(result[0]['patient_names'],['Ana Example','Luis Example']);self.assertEqual(result[0]['profile_name'],'WhatsApp name')
   self.assertEqual(call.call_args.args[0],'https://caller.example/api/messaging/patient-names');self.assertFalse(call.call_args.kwargs['allow_redirects'])
 def test_unavailable_names_do_not_hide_conversations(self):
  module=self.load()
  with patch.object(module.requests,'post',side_effect=module.requests.RequestException()):
   result,error=module.with_patient_names([{'phone':'+13055550123','name':'Existing label'}]);self.assertTrue(error);self.assertEqual(result[0]['name'],'Existing label')
 def test_non_us_phone_does_not_guess_patient_from_last_ten_digits(self):
  module=self.load()
  with patch.object(module.requests,'post') as call:
   result,error=module.with_patient_names([{'phone':'+442055550123','name':'Existing label'}]);call.assert_not_called();self.assertEqual(result[0]['name'],'Existing label')
 def test_selected_phone_has_lookup_priority(self):
  module=self.load();response=Mock(status_code=200);response.json.return_value={'results':{}}
  with patch.object(module.requests,'post',return_value=response) as call:
   module.with_patient_names([{'phone':'+13055550123'},{'phone':'+13055550124'}],preferred='+13055550124');self.assertEqual(call.call_args.kwargs['json']['phones'][0],'+13055550124')
if __name__=='__main__':unittest.main()
