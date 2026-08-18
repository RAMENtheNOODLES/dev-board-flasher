import keyring
import pytest
from keyring.errors import PasswordDeleteError


@pytest.fixture(autouse=True)
def isolated_keyring(monkeypatch):
	"""Redirects keyring.get_password/set_password/delete_password to an in-memory store.

	``stored_settings.py`` and ``github_token.py`` both pin a real OS keyring
	backend (``WinVaultKeyring``) at import time on win32, so re-swapping the
	backend from a fixture wouldn't undo that. Patching the call sites those
	modules actually use sidesteps the real OS credential store regardless of
	which backend ended up pinned, and keeps tests from leaving secrets behind
	in the real Windows credential manager.
	"""
	store: dict[tuple[str, str], str] = {}

	def fake_get_password(service_name, username):
		return store.get((service_name, username))

	def fake_set_password(service_name, username, password):
		store[(service_name, username)] = password

	def fake_delete_password(service_name, username):
		if (service_name, username) not in store:
			raise PasswordDeleteError("Password not found")
		del store[(service_name, username)]

	monkeypatch.setattr(keyring, "get_password", fake_get_password)
	monkeypatch.setattr(keyring, "set_password", fake_set_password)
	monkeypatch.setattr(keyring, "delete_password", fake_delete_password)


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
	"""Redirects StoredSettings' and CacheHelper's on-disk locations to tmp_path.

	Both ``StoredSettings.get_settings_path()`` (the settings INI file plus
	the encrypted/TTL-limited diskcache) and ``CacheHelper.get_cache_path()``
	(the board config cache) resolve through ``QStandardPaths`` to real
	per-user directories. Opt-in (not autouse) since only tests that actually
	read/write settings or caches need it; sharing one tmp_path for both is
	safe since they write different filenames.
	"""
	from utils.wiz_utils.cache_helper import CacheHelper
	from utils.wiz_utils.stored_settings import StoredSettings

	monkeypatch.setattr(StoredSettings, "get_settings_path", staticmethod(lambda: str(tmp_path)))
	monkeypatch.setattr(CacheHelper, "get_cache_path", staticmethod(lambda: str(tmp_path)))
	return tmp_path
