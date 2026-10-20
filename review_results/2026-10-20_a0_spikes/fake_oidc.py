"""A0 spike: a tiny stand-in for Google's sign-in (OpenID Connect), local only. Serves discovery, authorize (auto-approves), token, jwks."""
import json, time, secrets, sys
from authlib.jose import JsonWebKey, jwt
from starlette.applications import Starlette
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Route
import uvicorn

PORT = 8600
ISS = f"http://localhost:{PORT}"
KEY = JsonWebKey.generate_key("RSA", 2048, is_private=True, options={"kid": "k1"})
CODES = {}

async def disco(request):
    return JSONResponse({"issuer": ISS, "authorization_endpoint": ISS + "/authorize", "token_endpoint": ISS + "/token",
                         "jwks_uri": ISS + "/jwks", "response_types_supported": ["code"], "subject_types_supported": ["public"],
                         "id_token_signing_alg_values_supported": ["RS256"], "scopes_supported": ["openid", "email", "profile"]})

async def jwks(request):
    return JSONResponse({"keys": [KEY.as_dict(is_private=False)]})

async def authorize(request):
    q = request.query_params
    code = secrets.token_urlsafe(8)
    CODES[code] = {"nonce": q.get("nonce"), "client_id": q.get("client_id")}
    return RedirectResponse(f"{q['redirect_uri']}?code={code}&state={q['state']}")

async def token(request):
    form = await request.form()
    info = CODES.pop(form["code"])
    now = int(time.time())
    claims = {"iss": ISS, "sub": "1048576000000000000001", "aud": info["client_id"], "iat": now, "exp": now + int(__import__("os").environ.get("TTL", "3600")), "nonce": info["nonce"],
              "email": "test.person@example.com", "email_verified": True, "name": "Test Person"}
    idt = jwt.encode({"alg": "RS256", "kid": "k1"}, claims, KEY).decode()
    return JSONResponse({"access_token": "at-" + secrets.token_urlsafe(6), "token_type": "Bearer", "expires_in": 3600, "id_token": idt})

app = Starlette(routes=[Route("/.well-known/openid-configuration", disco), Route("/jwks", jwks), Route("/authorize", authorize), Route("/token", token, methods=["POST"])])
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
