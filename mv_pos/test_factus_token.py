import asyncio
import os

from app.application.services.factus_client import FactusClient
from app.config import settings


async def main():
    client = FactusClient()
    try:
        token = await client.get_access_token()
        print('TOKEN OK:', token)
    except Exception as exc:
        print('ERROR (password grant):', type(exc).__name__, exc)

    # If the caller provided a refresh token (via env var), try refresh flow
    refresh_token_env = os.getenv('FACTUS_REFRESH_TOKEN')
    access_token_env = os.getenv('FACTUS_ACCESS_TOKEN')
    if refresh_token_env:
        print('\nAttempting refresh via FactusClient.refresh_access_token() using env refresh token')
        client._refresh_token = refresh_token_env
        if access_token_env:
            client._access_token = access_token_env
        try:
            new = await client.refresh_access_token()
            print('REFRESH OK:', new)
        except Exception as exc:
            print('REFRESH ERROR (client):', type(exc).__name__, exc)
            # Also try direct HTTP request with Authorization header (as doc suggests)
            print('\nTrying direct refresh request with Authorization header')
            import httpx

            headers = {'Authorization': f'Bearer {access_token_env or ""}', 'Accept': 'application/json'}
            data = {
                'grant_type': 'refresh_token',
                'client_id': settings.factus_client_id,
                'client_secret': settings.factus_client_secret,
                'refresh_token': refresh_token_env,
            }
            r = httpx.post(settings.factus_api_base_url + '/oauth/token', data=data, headers=headers)
            print('direct refresh status=', r.status_code)
            print('direct refresh text=', r.text)
    else:
        print('\nNo FACTUS_REFRESH_TOKEN provided in environment; skipping refresh test.')


if __name__ == '__main__':
    asyncio.run(main())
