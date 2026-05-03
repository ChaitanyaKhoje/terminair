"""Auth adapters for Airflow API."""

import httpx


def build_auth(auth_config) -> httpx.Auth:
    auth_type = auth_config.type
    if auth_type == "basic":
        return httpx.BasicAuth(
            username=auth_config.username,
            password=auth_config.password,
        )
    elif auth_type == "token":
        token = auth_config.token
        if not token or not token.strip():
            raise ValueError(
                "Token auth is configured but the token value is empty.\n"
                "Set 'token' in your config.yaml or via an environment variable."
            )
        return TokenAuth(token.strip())
    else:
        raise ValueError(f"Unknown auth type: {auth_type}")


class TokenAuth(httpx.Auth):
    def __init__(self, token: str):
        self._token = token

    def auth_flow(self, request: httpx.Request):
        request.headers["Authorization"] = f"Bearer {self._token}"
        yield request
