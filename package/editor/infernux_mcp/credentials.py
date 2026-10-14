"""Per-user credentials for the loopback Editor transport."""

from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
import secrets
from urllib.parse import urlsplit


def credential_path(endpoint: str) -> Path:
    parsed = urlsplit(endpoint)
    if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}
            or parsed.path != "/mcp" or parsed.username or parsed.password
            or parsed.query or parsed.fragment or not parsed.port):
        raise ValueError("MCP credentials require a loopback HTTP /mcp endpoint")
    if os.name == "nt":
        directory = Path(os.environ["LOCALAPPDATA"]) / "Infernux" / "MCP"
    else:
        directory = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "infernux/mcp"
    return directory / f"{parsed.port}.json"


def _protect_directory(path: Path) -> None:
    if os.name != "nt":
        path.chmod(0o700)
        return
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    advapi.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    advapi.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    advapi.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
    advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p]
    advapi.GetSecurityDescriptorDacl.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.BOOL), ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.BOOL)]
    advapi.SetNamedSecurityInfoW.argtypes = [wintypes.LPWSTR, ctypes.c_int, wintypes.DWORD, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]

    def checked(ok):
        if not ok:
            raise ctypes.WinError(ctypes.get_last_error())

    token = wintypes.HANDLE()
    sid_string = wintypes.LPWSTR()
    descriptor = ctypes.c_void_p()
    checked(advapi.OpenProcessToken(kernel.GetCurrentProcess(), 0x0008, ctypes.byref(token)))
    try:
        size = wintypes.DWORD()
        advapi.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
        data = ctypes.create_string_buffer(size.value)
        checked(advapi.GetTokenInformation(token, 1, data, size, ctypes.byref(size)))
        sid = ctypes.cast(data, ctypes.POINTER(ctypes.c_void_p))[0]
        checked(advapi.ConvertSidToStringSidW(sid, ctypes.byref(sid_string)))
        checked(advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            f"D:P(A;OICI;FA;;;{sid_string.value})", 1, ctypes.byref(descriptor), None))
        present, defaulted, dacl = wintypes.BOOL(), wintypes.BOOL(), ctypes.c_void_p()
        checked(advapi.GetSecurityDescriptorDacl(descriptor, ctypes.byref(present), ctypes.byref(dacl), ctypes.byref(defaulted)))
        result = advapi.SetNamedSecurityInfoW(str(path), 1, 0x80000004, None, None, dacl, None)
        if result:
            raise ctypes.WinError(result)
    finally:
        kernel.CloseHandle(token)
        if sid_string:
            kernel.LocalFree(sid_string)
        if descriptor:
            kernel.LocalFree(descriptor)


def publish_credentials(endpoint: str) -> tuple[Path, str]:
    path = credential_path(endpoint)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    _protect_directory(path.parent)
    token = secrets.token_urlsafe(32)
    staging = path.with_name(f".{path.name}.{os.getpid()}")
    try:
        with open(staging, "w", encoding="utf-8") as handle:
            if os.name != "nt":
                os.fchmod(handle.fileno(), 0o600)
            json.dump({"endpoint": endpoint, "pid": os.getpid(), "token": token}, handle)
        os.replace(staging, path)
    finally:
        staging.unlink(missing_ok=True)
    return path, token


def load_token(endpoint: str) -> str:
    document = json.loads(credential_path(endpoint).read_text(encoding="utf-8"))
    if urlsplit(document["endpoint"]).port != urlsplit(endpoint).port:
        raise ValueError("MCP credential endpoint does not match")
    token = document["token"]
    if not isinstance(token, str) or not token:
        raise ValueError("MCP credential token is missing")
    return token


def remove_credentials(endpoint: str, token: str) -> None:
    path = credential_path(endpoint)
    try:
        current = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return
    if current.get("token") == token:
        path.unlink()
