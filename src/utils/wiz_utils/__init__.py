import ctypes
import io
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import requests
import tomllib
import truststore
from packaging import version

from ..custom_exceptions.remote_config_error import RemoteConfigError
from .cache_helper import CacheHelper
from .can_worker import CanWorker
from .github_token import GithubToken
from .plain_runnable import PlainRunnable
from .stored_settings import StoredSettings
from .usb_worker import USBWorker
from .wiz_logger import WizLogger

# Updater is re-exported for convenience (e.g. `from utils.wiz_utils import
# Updater`), but only actually imported at the bottom of this file - see the
# comment there for why.
__all__ = [
	"CacheHelper", "CanWorker", "GithubToken", "PlainRunnable",
	"StoredSettings", "USBWorker", "Updater", "WizLogger",
]

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

def check_for_updates(force_update: bool = False) -> tuple[bool, str, dict]:
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
			latest_version_str = response.json()["tag_name"].lstrip("v")
			latest_version = version.parse(latest_version_str)

			logger.debug(f"Latest version: {latest_version}")

			if (latest_version > ver) or force_update:
				# Return the raw tag-derived string (not the PEP 440-normalized
				# form) since the release workflow names assets directly from
				# pyproject.toml's version string (e.g. "0.7.0-beta"), which
				# packaging.version normalizes to "0.7.0b0" - using the
				# normalized form here would make find_asset() look for a
				# filename that doesn't exist.
				return (True, latest_version_str, response.json())
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
			for passing to :func:`apply_update` as ``exe_path``.
	"""
	if "__compiled__" in globals():
		# Running as a Nuitka onefile exe
		return _get_onefile_launcher_path() or sys.executable
	else:
		# Running as a plain .py script (dev mode)
		return os.path.abspath(sys.argv[0])

def apply_update(installer_path):
	"""Runs the downloaded installer silently, then relaunches the app once it finishes.

	The installer (built with ``CloseApplications``, see
	``scripts/installer.iss``) uses Windows Restart Manager to force-close
	whatever's still holding ``{app}\\upload_wiz.exe`` open before
	overwriting it. That's *not* necessarily this process, though: for a
	Nuitka onefile build, the file Restart Manager sees running is the
	onefile launcher (parent) process, while this Python code runs in a
	separate child process extracted to a temp directory - so Restart
	Manager's own restart mechanism (``RmRestart``, which only restarts
	processes that called ``RegisterApplicationRestart`` on themselves)
	can't be used to relaunch this app, since we're not the process it
	closes. Instead, this launches a detached helper script - so it
	survives this process's own exit or a forced close by Restart Manager -
	that waits for the installer to finish, then explicitly starts the
	newly-installed exe.

	Args:
		installer_path: Path to the downloaded ``*-setup.exe`` installer.
	"""
	exe_path = get_current_exe_path()

	# Quoting: cmd's "call" isn't used, so a bare invocation of a quoted
	# path blocks the .bat until the installer exits, which is what lets
	# `start` below run only once install (and any Restart-Manager-driven
	# close of the launcher) has actually finished.
	bat = f"""
	@echo off
	"{installer_path}" /SP- /SILENT /NOICONS /FORCECLOSEAPPLICATIONS
	start "" "{exe_path}"
	del "%~f0"
	"""
	bat_path = os.path.join(os.environ["TEMP"], "apply_update.bat")
	with open(bat_path, "w") as f:
		f.write(bat)
	subprocess.Popen(
		["cmd", "/c", bat_path],
		creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
	)

# Imported last: updater.py does `from . import download_update, ...`, which
# requires those names to already exist in this module's namespace.
from .updater import Updater
