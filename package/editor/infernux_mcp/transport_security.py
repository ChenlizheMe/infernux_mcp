"""Authentication and browser boundaries shared by every HTTP route."""

import hmac

from starlette.responses import JSONResponse


class EditorTransportSecurity:
    def __init__(self, app, *, port: int, token: str):
        self.app = app
        self.hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        self.authorization = f"Bearer {token}".encode("ascii")

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = scope["headers"]
            hosts = [value.decode("ascii", errors="replace").lower() for name, value in headers if name.lower() == b"host"]
            origins = [value for name, value in headers if name.lower() == b"origin"]
            error = None
            if len(hosts) != 1 or hosts[0] not in self.hosts:
                error = JSONResponse({"error": "Invalid Host"}, status_code=421)
            elif origins:
                error = JSONResponse({"error": "Browser origins are not allowed"}, status_code=403)
            elif scope["path"] != "/health":
                authorization = [value for name, value in headers if name.lower() == b"authorization"]
                if len(authorization) != 1 or not hmac.compare_digest(authorization[0], self.authorization):
                    error = JSONResponse({"error": "Authentication required"}, status_code=401,
                                         headers={"WWW-Authenticate": "Bearer"})
            if error is not None:
                await error(scope, receive, send)
                return
        await self.app(scope, receive, send)
