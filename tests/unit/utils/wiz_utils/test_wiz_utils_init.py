import requests

import utils.wiz_utils as wiz_utils
from utils.custom_exceptions import RemoteConfigError
from utils.wiz_utils.github_token import GithubToken


# --- read_toml_file_from_url_or_path -------------------------------------


def test_reads_a_local_file(tmp_path):
	toml_path = tmp_path / "config.toml"
	toml_path.write_text('board_name = "Test"\n', encoding="utf-8")

	assert wiz_utils.read_toml_file_from_url_or_path(str(toml_path)) == {"board_name": "Test"}


def test_uses_the_cache_when_the_path_is_already_present():
	cache = {"some/path.toml": {"cached": True}}

	assert wiz_utils.read_toml_file_from_url_or_path("some/path.toml", cache) == {"cached": True}


def test_populates_the_cache_after_reading_a_local_file(tmp_path):
	toml_path = tmp_path / "config.toml"
	toml_path.write_text('board_name = "Test"\n', encoding="utf-8")
	cache = {}

	wiz_utils.read_toml_file_from_url_or_path(str(toml_path), cache)

	assert cache[str(toml_path)] == {"board_name": "Test"}


def test_fetches_from_github_when_url_contains_github(monkeypatch):
	monkeypatch.setattr(GithubToken, "fetch_file", staticmethod(lambda url: b'board_name = "Remote"\n'))

	url = "https://github.com/owner/repo/blob/main/board.toml"

	assert wiz_utils.read_toml_file_from_url_or_path(url) == {"board_name": "Remote"}


def test_returns_none_when_the_github_fetch_fails(monkeypatch):
	def raise_error(url):
		raise RemoteConfigError("boom")

	monkeypatch.setattr(GithubToken, "fetch_file", staticmethod(raise_error))

	url = "https://github.com/owner/repo/blob/main/board.toml"

	assert wiz_utils.read_toml_file_from_url_or_path(url) is None


# --- get_remote_configs ----------------------------------------------------


def test_get_remote_configs_filters_to_files_declaring_the_given_key(tmp_path):
	board_toml = tmp_path / "board.toml"
	board_toml.write_text('board_name = "Test"\n', encoding="utf-8")
	tool_toml = tmp_path / "tool.toml"
	tool_toml.write_text('tool_name = "Test"\n', encoding="utf-8")

	result = wiz_utils.get_remote_configs([str(board_toml), str(tool_toml)], "board_name")

	assert result == [str(board_toml)]


# --- find_asset --------------------------------------------------------


def test_find_asset_returns_the_matching_asset():
	release = {"assets": [{"name": "app.zip"}, {"name": "app.exe"}]}

	assert wiz_utils.find_asset(release, "app.exe") == {"name": "app.exe"}


def test_find_asset_returns_none_when_not_found():
	assert wiz_utils.find_asset({"assets": [{"name": "app.zip"}]}, "missing.exe") is None


def test_find_asset_handles_a_missing_assets_key():
	assert wiz_utils.find_asset({}, "app.exe") is None


# --- check_for_updates ---------------------------------------------------


def _write_project_toml(tmp_path, version="1.0.0", repo="https://github.com/owner/repo"):
	path = tmp_path / "pyproject.toml"
	path.write_text(
		f'[project]\nversion = "{version}"\n\n[project.urls]\nRepository = "{repo}"\n',
		encoding="utf-8",
	)
	return path


class _FakeResponse:
	def __init__(self, json_data, ok=True):
		self._json_data = json_data
		self._ok = ok

	def raise_for_status(self):
		if not self._ok:
			raise requests.HTTPError("boom")

	def json(self):
		return self._json_data


def test_check_for_updates_returns_true_for_a_newer_release(monkeypatch, tmp_path):
	config_path = _write_project_toml(tmp_path, version="1.0.0")
	monkeypatch.setattr(wiz_utils, "get_config_path", lambda: config_path)
	monkeypatch.setattr(
		wiz_utils.requests, "get", lambda url, timeout: _FakeResponse({"tag_name": "v1.1.0", "assets": []})
	)

	can_update, latest_version, release = wiz_utils.check_for_updates()

	assert can_update is True
	assert latest_version == "1.1.0"
	assert release["tag_name"] == "v1.1.0"


def test_check_for_updates_returns_false_when_already_up_to_date(monkeypatch, tmp_path):
	config_path = _write_project_toml(tmp_path, version="1.1.0")
	monkeypatch.setattr(wiz_utils, "get_config_path", lambda: config_path)
	monkeypatch.setattr(
		wiz_utils.requests, "get", lambda url, timeout: _FakeResponse({"tag_name": "v1.1.0", "assets": []})
	)

	assert wiz_utils.check_for_updates() == (False, "", {})


def test_check_for_updates_returns_false_on_network_failure(monkeypatch, tmp_path):
	config_path = _write_project_toml(tmp_path)
	monkeypatch.setattr(wiz_utils, "get_config_path", lambda: config_path)

	def raise_connection_error(url, timeout):
		raise requests.ConnectionError("no network")

	monkeypatch.setattr(wiz_utils.requests, "get", raise_connection_error)

	assert wiz_utils.check_for_updates() == (False, "", {})


# --- download_update -----------------------------------------------------


class _FakeStreamResponse:
	def __init__(self, chunks, content_length=None):
		self._chunks = chunks
		self.headers = {} if content_length is None else {"content-length": str(content_length)}

	def raise_for_status(self):
		pass

	def iter_content(self, chunk_size):
		return iter(self._chunks)

	def __enter__(self):
		return self

	def __exit__(self, *exc_info):
		return False


def test_download_update_writes_response_content_and_reports_progress(monkeypatch, tmp_path):
	chunks = [b"hello ", b"world"]
	monkeypatch.setattr(
		wiz_utils.requests, "get", lambda url, stream: _FakeStreamResponse(chunks, content_length=11)
	)
	dest = tmp_path / "update.exe"
	progress_calls = []

	wiz_utils.download_update("https://example.com/update.exe", str(dest), on_progress=progress_calls.append)

	assert dest.read_bytes() == b"hello world"
	assert progress_calls == [6 / 11, 1.0]


def test_download_update_without_a_progress_callback_or_content_length(monkeypatch, tmp_path):
	monkeypatch.setattr(wiz_utils.requests, "get", lambda url, stream: _FakeStreamResponse([b"data"]))
	dest = tmp_path / "update.exe"

	wiz_utils.download_update("https://example.com/update.exe", str(dest))

	assert dest.read_bytes() == b"data"
