"""Prepare a signed server-to-server request; never expose the key to UI code."""
import base64,hashlib,hmac,json,time,uuid
import requests
PURPOSE=b'ale-callerid-messaging-v1'

def prepare_request(method,url,key,username,**kwargs):
    if not key:raise ValueError('Caller API key unavailable')
    request=requests.Request(method,url,headers={'ngrok-skip-browser-warning':'true'},**kwargs).prepare()
    body=request.body or b''
    if isinstance(body,str):body=body.encode('utf-8')
    value={'aud':'ale-messaging','user':username,'iat':int(time.time()),'nonce':uuid.uuid4().hex,'method':request.method,'target':request.path_url,'body':hashlib.sha256(body).hexdigest()}
    encoded=base64.urlsafe_b64encode(json.dumps(value,separators=(',',':')).encode()).rstrip(b'=').decode()
    derived=hmac.new(key.encode(),PURPOSE,hashlib.sha256).digest()
    request.headers['X-Ale-Caller-Authorization']=encoded+'.'+hmac.new(derived,encoded.encode(),hashlib.sha256).hexdigest()
    return request

def send_request(method,url,key,username,**kwargs):
    request=prepare_request(method,url,key,username,**kwargs)
    with requests.Session() as session:return session.send(request,timeout=(3,15),allow_redirects=False)
