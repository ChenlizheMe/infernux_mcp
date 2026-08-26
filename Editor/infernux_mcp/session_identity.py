"""Build identity capture used by validation sessions."""

from __future__ import annotations

import hashlib
from importlib import metadata as importlib_metadata
import json
import os
from pathlib import Path
import subprocess
import time
import tomllib
from typing import Any

from Infernux.engine.path_utils import relative_path, resolved_path


def capture_build_identity(
    policy: dict[str, Any], build_profile: str
) -> dict[str, Any]:
    source_root = _find_source_root()
    return {
        "captured_at": time.time(),
        "source_root": source_root,
        "package_version": _read_package_version(source_root),
        "git": _git_identity(source_root),
        "cmake": _cmake_identity(source_root, policy, build_profile),
        "python_package": _python_package_identity(source_root),
        "native_artifact": _native_artifact_identity(source_root),
    }


def _find_source_root() -> str:
    module_path = Path(resolved_path(__file__))
    for candidate in (module_path.parent, *module_path.parents):
        if (candidate / "pyproject.toml").is_file() and (
            candidate / "CMakePresets.json"
        ).is_file():
            return str(candidate)
    return ""


def _read_package_version(source_root: str) -> str:
    pyproject = Path(source_root) / "pyproject.toml" if source_root else None
    if pyproject and pyproject.is_file():
        try:
            with open(pyproject, "rb") as stream:
                project = tomllib.load(stream).get("project") or {}
            return str(project.get("version", "") or "")
        except (OSError, tomllib.TOMLDecodeError):
            pass
    try:
        return str(importlib_metadata.version("Infernux") or "")
    except importlib_metadata.PackageNotFoundError:
        return ""


def _python_package_identity(
    source_root: str, package_root: Path | None = None
) -> dict[str, Any]:
    root = package_root or Path(resolved_path(__file__)).parents[1]
    if not root.is_dir():
        return {"available": False}
    extensions = frozenset({".py", ".pyi", ".json"})
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in extensions
        and "__pycache__" not in path.parts
    )
    digest = hashlib.sha256()
    hashed_bytes = 0
    for path in files:
        logical = path.relative_to(root).as_posix()
        try:
            size = path.stat().st_size
            with open(path, "rb") as stream:
                digest.update(logical.encode("utf-8"))
                digest.update(b"\0")
                digest.update(str(size).encode("ascii"))
                digest.update(b"\0")
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
                digest.update(b"\0")
        except OSError:
            return {"available": False, "error": f"failed to hash {logical}"}
        hashed_bytes += size
    return {
        "available": True,
        "path": _relative(source_root, str(root)),
        "file_count": len(files),
        "size_bytes": hashed_bytes,
        "sha256": digest.hexdigest(),
        "extensions": sorted(extensions),
    }


def _git_identity(source_root: str) -> dict[str, Any]:
    revision = _run_git(source_root, "rev-parse", "HEAD")
    if revision is None:
        return {"available": False}
    branch = _run_git(source_root, "rev-parse", "--abbrev-ref", "HEAD") or ""
    status = _run_git(source_root, "status", "--porcelain", "--untracked-files=no")
    lines = status.splitlines() if status is not None else []
    return {
        "available": True,
        "revision": revision,
        "branch": branch,
        "tracked_worktree_dirty": bool(lines),
        "tracked_change_count": len(lines),
    }


def _run_git(source_root: str, *args: str) -> str | None:
    if not source_root:
        return None
    try:
        completed = subprocess.run(
            ["git", "-C", source_root, *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2.0,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout.strip() if completed.returncode == 0 else None


def _cmake_identity(
    source_root: str, policy: dict[str, Any], build_profile: str
) -> dict[str, Any]:
    default_preset = "debug" if build_profile == "debug_feedback" else "release"
    configured = str(policy.get("cmake_configure_preset", "") or "").strip()
    build = str(policy.get("cmake_build_preset", "") or "").strip()
    cache_path = (
        os.path.join(source_root, "out", "build", "CMakeCache.txt")
        if source_root
        else ""
    )
    build_type = ""
    if cache_path and os.path.isfile(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8", errors="replace") as stream:
                for line in stream:
                    if line.startswith("CMAKE_BUILD_TYPE:"):
                        build_type = line.split("=", 1)[1].strip()
                        break
        except OSError:
            pass
    build_preset = build or default_preset
    configuration, presets_path = _build_preset_configuration(
        source_root, build_preset
    )
    return {
        "configure_preset": configured or default_preset,
        "configure_preset_source": "session_policy" if configured else "build_profile_inference",
        "build_preset": build_preset,
        "build_preset_source": "session_policy" if build else "build_profile_inference",
        "build_configuration": configuration,
        "build_configuration_source": "CMakePresets.json" if configuration else "",
        "presets_path": presets_path,
        "cache_path": _relative(source_root, cache_path) if cache_path else "",
        "cache_configured_build_type": build_type,
    }


def _build_preset_configuration(
    source_root: str, build_preset: str
) -> tuple[str, str]:
    path = os.path.join(source_root, "CMakePresets.json") if source_root else ""
    if not path or not os.path.isfile(path):
        return "", ""
    try:
        with open(path, "r", encoding="utf-8") as stream:
            document = json.load(stream)
    except (OSError, json.JSONDecodeError):
        return "", _relative(source_root, path)
    for preset in document.get("buildPresets") or []:
        if isinstance(preset, dict) and str(preset.get("name", "")) == build_preset:
            return str(preset.get("configuration", "") or ""), _relative(
                source_root, path
            )
    return "", _relative(source_root, path)


def _native_artifact_identity(source_root: str) -> dict[str, Any]:
    native_dir = Path(resolved_path(__file__)).parents[1] / "lib"
    candidates = sorted(
        path
        for path in native_dir.glob("_Infernux.*")
        if path.suffix.lower() in {".pyd", ".so", ".dylib"}
    )
    if not candidates:
        return {"available": False}
    artifact = candidates[0]
    try:
        size = artifact.stat().st_size
    except OSError:
        return {"available": False}
    digest = hashlib.sha256()
    try:
        with open(artifact, "rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return {"available": False}
    return {
        "available": True,
        "path": _relative(source_root, str(artifact)),
        "size_bytes": size,
        "sha256": digest.hexdigest(),
    }


def _relative(root: str, path: str) -> str:
    if not path:
        return ""
    try:
        return relative_path(path, root, allow_root=True) if root else path
    except ValueError:
        return path


__all__ = ["capture_build_identity"]
