from .wiz_logger import WizLogger

import tomllib, requests, subprocess, sys, os, ctypes
from pathlib import Path
import logging
import truststore

# Verify TLS certs against the OS trust store (e.g. Windows) instead of only
# certifi's public bundle, so requests still works behind a corporate
# TLS-inspecting proxy that signs traffic with an internal root CA.
truststore.inject_into_ssl()

def get_config_path() -> Path:
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

def check_for_updates() -> tuple[bool, str, dict]:
	logger = logging.getLogger(__name__)
	with open(get_config_path(), "rb") as f:
		config = tomllib.load(f)
		ver = config["project"]["version"]
		repo = config["project"]["urls"]["Repository"]
		owner_repo = repo.rstrip("/").removeprefix("https://github.com/")
		api_url = f"https://api.github.com/repos/{owner_repo}/releases/latest"
		try:
			response = requests.get(api_url, timeout=5)
			response.raise_for_status()
			latest_version = response.json()["tag_name"]
			latest_version = latest_version.lstrip("v")

			logger.debug(f"Latest version: {latest_version}")

			if (ver != latest_version):
				return (True, latest_version, response.json())
			else:
				return (False, "", {})
		except (requests.RequestException, ValueError, KeyError) as e:
			logger.error(f"Update check failed: {e}")
			return (False, "", {})

def find_asset(release: dict, asset_name: str) -> dict | None:
	for asset in release.get("assets", []):
		if asset["name"] == asset_name:
			return asset
	return None

def download_update(url: str, dest_path: str, on_progress=None) -> None:
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
    if "__compiled__" in globals():
        # Running as a Nuitka onefile exe
        return _get_onefile_launcher_path() or sys.executable
    else:
        # Running as a plain .py script (dev mode)
        return os.path.abspath(sys.argv[0])

# Imported last: updater.py does `from . import download_update, ...`, which
# requires those names to already exist in this module's namespace.
from .updater import Updater
