import httpx
from app.config import settings

payload = {
    'grant_type': settings.factus_grant_type,
    'client_id': settings.factus_client_id,
    'client_secret': settings.factus_client_secret,
    'username': settings.factus_username,
    'password': settings.factus_password,
}
files_payload = {k: (None, v) for k, v in payload.items()}
req = httpx.Request('POST', settings.factus_api_base_url + '/oauth/token', files=files_payload, headers={'Accept':'application/json'})
req.read()
print('REQUEST HEADERS:')
for k,v in req.headers.items():
    print(f"{k}: {v}")
print('\nREQUEST BODY (bytes):')
print(req.content[:2000])
print('\nREQUEST BODY (decoded):')
try:
    print(req.content.decode('utf-8'))
except Exception as e:
    print('decode error', e)
