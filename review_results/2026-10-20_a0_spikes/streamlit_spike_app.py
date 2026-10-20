"""A0 spike page: sign in, show what st.user holds, mint the short-lived token the API would receive and verify it the way the API would."""
import time, uuid, json
import jwt, streamlit as st

SECRET = "spike-shared-secret-not-real"
st.title("A0 spike")
if not st.user.is_logged_in:
    st.button("Sign in", on_click=st.login)
else:
    claims = {k: v for k, v in st.user.to_dict().items()}
    st.write("LOGGED_IN")
    st.code(json.dumps(claims, default=str), language="json")
    toks = st.user.tokens
    st.write("TOKENS_KEYS=" + ",".join(sorted(toks.keys())))
    idt = toks.get("id") if toks else None
    if idt:
        payload = jwt.decode(idt, options={"verify_signature": False})
        st.write(f"ID_TOKEN_EXP_IN_SECONDS={payload['exp'] - int(time.time())}")
    now = int(time.time())
    tok = jwt.encode({"iss": "streamlit", "aud": "recourse-api", "sub": st.user.get("sub"), "email": st.user.get("email"),
                      "email_verified": st.user.get("email_verified"), "iat": now, "exp": now + 300, "jti": str(uuid.uuid4())}, SECRET, algorithm="HS256")
    back = jwt.decode(tok, SECRET, algorithms=["HS256"], audience="recourse-api", issuer="streamlit")
    st.write("MINTED_AND_VERIFIED sub=" + back["sub"] + " ttl=" + str(back["exp"] - back["iat"]))
    st.button("Log out", on_click=st.logout)
