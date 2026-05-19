def integration_local_password(*, username: str) -> str:
    """
    LOCAL password for hosted Postiz / Chatwoot accounts provisioned by Autobus.

    Sign in with the user's email and this value (Autobus ``fullname``, exposed as
    username in the API). It is intentionally independent of the Autobus login
    password so backend password resets do not break integration SSO-style login.
    """
    pwd = (username or "").strip()
    if not pwd:
        raise ValueError("username is required for integration local password")
    return pwd
