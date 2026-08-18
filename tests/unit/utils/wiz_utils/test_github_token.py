import pytest

from utils.custom_exceptions import RemoteConfigError
from utils.wiz_utils.github_token import GithubToken


@pytest.mark.parametrize(
	"url,expected",
	[
		(
			"https://github.com/owner/repo/blob/main/config/boards/esp32.toml",
			("owner", "repo", "main", "config/boards/esp32.toml"),
		),
		(
			"https://github.com/owner/repo/blob/feature/my-branch/path/to/file.toml",
			("owner", "repo", "feature", "my-branch/path/to/file.toml"),
		),
		(
			"https://raw.githubusercontent.com/owner/repo/main/config/boards/esp32.toml",
			("owner", "repo", "main", "config/boards/esp32.toml"),
		),
		(
			"https://raw.githubusercontent.com/owner/repo/refs/heads/develop/config/boards/esp32.toml",
			("owner", "repo", "develop", "config/boards/esp32.toml"),
		),
		(
			"https://raw.githubusercontent.com/owner/repo/refs/tags/v1.2.3/config/boards/esp32.toml",
			("owner", "repo", "v1.2.3", "config/boards/esp32.toml"),
		),
	],
)
def test_parse_github_url_accepts_known_formats(url, expected):
	assert GithubToken.parse_github_url(url) == expected


def test_parse_github_url_strips_query_string():
	# Private-repo "raw" links carry a short-lived signed "?token=..." param
	# for anonymous access, which is irrelevant once authenticating via a
	# PAT, and would otherwise get swallowed into the captured path.
	url = "https://raw.githubusercontent.com/owner/repo/main/file.toml?token=abc123"

	assert GithubToken.parse_github_url(url) == ("owner", "repo", "main", "file.toml")


@pytest.mark.parametrize(
	"url",
	[
		"https://example.com/owner/repo/blob/main/file.toml",
		"https://github.com/owner/repo/tree/main/config",
		"not a url at all",
		"",
	],
)
def test_parse_github_url_rejects_unrecognized_formats(url):
	with pytest.raises(RemoteConfigError):
		GithubToken.parse_github_url(url)
