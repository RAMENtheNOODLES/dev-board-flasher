import ctypes
import io
import logging
import os
import requests
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import truststore
from packaging import version

from .can_worker import CanWorker
from .github_token import GithubToken
from .plain_runnable import PlainRunnable
from .stored_settings import StoredSettings
from .usb_worker import USBWorker
from .wiz_logger import WizLogger
from .cache_helper import CacheHelper
from ..custom_exceptions.remote_config_error import RemoteConfigError


# Verify TLS certs against the OS trust store (e.g. Windows) instead of only
# certifi's public bundle, so requests still works behind a corporate
# TLS-inspecting proxy that signs traffic with an internal root CA.
truststore.inject_into_ssl()

def get_config_path() -> Path:
	"""Returns the path to the bundled ``pyproject.toml``, used to read the app's version and repo URL.

	Returns:
		Path: Absolute path to ``pyproject.toml``, resolved relative to this
			file's location whether running from source or as a compiled
			Nuitka onefile build.
	"""
	logger = logging.getLogger(__name__)
	# pyproject.toml is bundled as a data file via --include-data-files in
	# pysidedeploy.spec so it's present next to main.py in both source and
	# compiled (Nuitka onefile) runs.
	current_dir = Path(__file__).resolve().parent
	if "__compiled__" in globals():
		# Nuitka onefile build: the extraction root corresponds directly to
		# the "src" directory (no extra "src" nesting level like in source runs).
		config_path = current_dir.parent.parent / "pyproject.toml"
	else:
		config_path =  current_dir.parent.parent.parent / "pyproject.toml"

	logger.debug(f"Retrieved config path: {config_path}")
	return config_path

def read_toml_file_from_url_or_path(path_or_url: str, cache: dict[str, dict[str, Any] | None] | None = None) -> dict[str, Any]|None:
	"""Parses a TOML config from a local path or (github) URL.

	Args:
		path_or_url (str): A local filesystem path, or a GitHub file URL as
			accepted by :meth:`GithubToken.fetch_file`.
		cache (dict[str, dict[str, Any] | None] | None, optional): Shared
			memo of already-resolved configs, keyed by ``path_or_url``. When
			given, board/tool discovery can classify and parse the same
			remote file without re-downloading it. Defaults to ``None``
			(always re-reads).

	Returns:
		dict[str, Any] | None: The parsed TOML, or ``None`` if a remote
			fetch failed.
	"""
	logger = logging.getLogger(__name__)

	if cache is not None and path_or_url in cache:
		return cache[path_or_url]

	if "github" in path_or_url:
		try:
			config_data = tomllib.load(io.BytesIO(GithubToken.fetch_file(path_or_url)))
		except RemoteConfigError:
			logger.exception("Remote Config Error")
			config_data = None
	else:
		with open(path_or_url, "rb") as f:
			config_data = tomllib.load(f)

	if cache is not None:
		cache[path_or_url] = config_data

	return config_data

def get_remote_configs(remote_configs: list[str], check_in_config: str, cache: dict[str, dict[str, Any] | None] | None = None) -> list[str]:
	"""Filters configs (local or remote) down to ones declaring a given key.

	Args:
		remote_configs (list[str]): Local paths and/or GitHub URLs to check.
		check_in_config (str): Top-level TOML key that must be present
			(e.g. ``"board_name"`` or ``"tool_name"``) for a config to be
			included in the result.
		cache (dict[str, dict[str, Any] | None] | None, optional): Shared
			memo passed through to :func:`read_toml_file_from_url_or_path`
			so the same URL isn't fetched once to classify it here and
			again to actually parse it later. Defaults to ``None``.

	Returns:
		list[str]: The subset of ``remote_configs`` whose parsed TOML
			contains ``check_in_config``.
	"""
	out: list[str] = []
	for config in remote_configs:
		config_data = read_toml_file_from_url_or_path(config, cache)
		if config_data is not None and check_in_config in config_data:
			out.append(config)

	return out

def check_for_updates() -> tuple[bool, str, dict]:
	"""Compares the installed version against the latest GitHub release.

	Versions are compared with :func:`packaging.version.parse` (PEP 440),
	not string/tuple equality, so pre-release/local-version segments (e.g.
	``0.6.0-beta``) sort correctly against final releases instead of just
	being treated as "different from" every other version.

	Returns:
		tuple[bool, str, dict]: ``(can_update, latest_version, release)``.
			``can_update`` is ``True`` only if the latest release's version
			is strictly newer than the installed one. ``latest_version`` is
			its normalized (PEP 440) version string. ``release`` is the raw
			GitHub release API response. On any failure to check (network
			error, malformed response, missing config), returns
			``(False, "", {})``.
	"""
	logger = logging.getLogger(__name__)
	logger.info("Getting config and checking for updates")
	with open(get_config_path(), "rb") as f:
		config = tomllib.load(f)
		ver = version.parse(config["project"]["version"])
		repo = config["project"]["urls"]["Repository"]
		owner_repo = repo.rstrip("/").removeprefix("https://github.com/")
		api_url = f"https://api.github.com/repos/{owner_repo}/releases/latest"
		try:
			response = requests.get(api_url, timeout=5)
			response.raise_for_status()
			latest_version = response.json()["tag_name"]
			latest_version = latest_version.lstrip("v")
			latest_version = version.parse(latest_version)

			logger.debug(f"Latest version: {latest_version}")

			if (latest_version > ver):
				return (True, latest_version.public, response.json())
			else:
				return (False, "", {})
		except (requests.RequestException, ValueError, KeyError) as e:
			logger.error(f"Update check failed: {e}")
			return (False, "", {})

def find_asset(release: dict, asset_name: str) -> dict | None:
	"""Finds a named asset in a GitHub release API response.

	Args:
		release (dict): A release object, as returned by
			:func:`check_for_updates` (the raw GitHub releases API response).
		asset_name (str): Exact filename of the asset to find.

	Returns:
		dict | None: The matching asset object, or ``None`` if
			``release["assets"]`` has no asset named ``asset_name``.
	"""
	for asset in release.get("assets", []):
		if asset["name"] == asset_name:
			return asset
	return None

def download_update(url: str, dest_path: str, on_progress=None) -> None:
	"""Streams a file from ``url`` to ``dest_path``, reporting progress as it goes.

	Args:
		url (str): Direct download URL for the file (e.g. a release asset's
			``browser_download_url``).
		dest_path (str): Local path to write the downloaded file to.
		on_progress (Callable[[float], None] | None, optional): Called after
			each chunk with the fraction (0-1) downloaded so far. Only called
			if the response reports a ``content-length``. Defaults to
			``None``.
	"""
	with requests.get(url, stream=True) as resp:
		resp.raise_for_status()
		total = int(resp.headers.get("content-length", 0))
		downloaded = 0
		with open(dest_path, "wb") as f:
			for chunk in resp.iter_content(chunk_size=8192):
				if chunk:
					f.write(chunk)
					downloaded += len(chunk)
					if on_progress and total:
						on_progress(downloaded / total)

def apply_update(new_exe_path, current_exe_path):
	"""Replaces the running exe with a newly downloaded one and relaunches it, then exits this process.

	Since the currently running exe can't overwrite itself directly, this
	writes and launches a detached batch script that waits for the process
	to release its file lock, moves ``new_exe_path`` over ``current_exe_path``,
	relaunches it, then deletes itself. Does not return: exits this process
	immediately after handing off to the script.

	Args:
		new_exe_path: Path to the newly downloaded/extracted executable.
		current_exe_path: Path of the currently running executable to
			overwrite, as returned by :func:`get_current_exe_path`.
	"""
	# The old exe (or its Nuitka onefile launcher) may still hold its file
	# locked for a moment after this process exits, so retry the move
	# instead of assuming one fixed delay is always long enough.
	bat = f"""
	@echo off
	setlocal
	set "attempts=0"

	:retry
	move /y "{new_exe_path}" "{current_exe_path}" >nul 2>&1
	if not exist "{new_exe_path}" goto done

	set /a attempts+=1
	if %attempts% geq 30 goto failed

	timeout /t 1 /nobreak >nul
	goto retry

	:done
	start "" "{current_exe_path}"
	del "%~f0"
	goto :eof

	:failed
	del "%~f0"
	"""
	bat_path = os.path.join(os.environ["TEMP"], "update.bat")
	with open(bat_path, "w") as f:
		f.write(bat)
	subprocess.Popen(
		["cmd", "/c", bat_path],
		creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
	)
	sys.exit(0)

def _get_onefile_launcher_path() -> str | None:
	"""Resolves the real on-disk path of the running Nuitka onefile exe.

	sys.executable points at the temp-extracted child interpreter, not the
	installed binary. Nuitka's onefile bootstrap sets NUITKA_ONEFILE_PARENT
	to the PID of the still-running parent (the actual launched exe) for
	exactly this purpose, so ask Windows for that process's image path.
	"""
	parent_pid = os.environ.get("NUITKA_ONEFILE_PARENT")
	if not parent_pid:
		return None

	PROCESS_QUERY_INFORMATION = 0x0400
	PROCESS_VM_READ = 0x0010

	try:
		h_process = ctypes.windll.kernel32.OpenProcess(
			PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, int(parent_pid)
		)
		if not h_process:
			return None
		try:
			buffer = ctypes.create_unicode_buffer(1024)
			length = ctypes.windll.psapi.GetModuleFileNameExW(h_process, None, buffer, len(buffer))
			return buffer.value if length else None
		finally:
			ctypes.windll.kernel32.CloseHandle(h_process)
	except (ValueError, OSError):
		return None

def get_current_exe_path() -> str:
    """Returns the on-disk path of the currently running executable/script.

    For a Nuitka onefile build, ``sys.executable`` points at the
    temp-extracted child interpreter rather than the installed binary, so
    this resolves the real launcher path via
    :func:`_get_onefile_launcher_path` instead (falling back to
    ``sys.executable`` if that can't be determined). For a plain source run,
    returns the absolute path of the running script.

    Returns:
        str: Path to the currently running executable or script, suitable
            for passing to :func:`apply_update` as ``current_exe_path``.
    """
    if "__compiled__" in globals():
        # Running as a Nuitka onefile exe
        return _get_onefile_launcher_path() or sys.executable
    else:
        # Running as a plain .py script (dev mode)
        return os.path.abspath(sys.argv[0])

# Imported last: updater.py does `from . import download_update, ...`, which
# requires those names to already exist in this module's namespace.
from .updater import Updater
