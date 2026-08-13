import sys
import re
from urllib.parse import urlsplit, urlunsplit
import keyring
from keyring.errors import PasswordDeleteError
import requests
import requests_cache
from datetime import timedelta

from ..custom_exceptions import RemoteConfigError

import logging

_SERVICE_NAME = "dev-board-flasher"
_USERNAME = "github_pat"

_SESSION = requests_cache.CachedSession(
	"github_token",
	cache_control=True,
	expire_after=timedelta(minutes=10),
	match_headers=['Accept', 'Content-Type']
)

if sys.platform == "win32":
	# keyring normally picks a backend via importlib.metadata entry point
	# discovery, which the Nuitka onefile build doesn't preserve unless
	# distribution metadata is explicitly bundled. Pinning the backend
	# directly sidesteps that so it behaves the same in source and
	# compiled builds.
	from keyring.backends.Windows import WinVaultKeyring
	keyring.set_keyring(WinVaultKeyring())


class GithubToken:
	"""Stores/retrieves the GitHub PAT and fetches files from GitHub with it.

	The token is kept in the OS credential store (via ``keyring``) rather
	than ``QSettings``/the registry, since it's a secret rather than a
	plain app setting.
	"""

	_BLOB_URL_RE = re.compile(
		r"^https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/blob/(?P<ref>[^/]+)/(?P<path>.+)$"
	)
	# GitHub generates raw URLs with the ref spelled out as
	# "refs/heads/{branch}/" or "refs/tags/{tag}/" (to stay unambiguous when
	# the branch name itself contains a "/"), but still accepts the older,
	# shorter "{branch-or-sha}/" form for refs without slashes.
	_RAW_URL_RE = re.compile(
		r"^https://raw\.githubusercontent\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/"
		r"(?:refs/(?:heads|tags)/(?P<ref_prefixed>.+?)|(?P<ref_plain>[^/]+))/(?P<path>.+)$"
	)

	@staticmethod
	def get_token() -> str | None:
		"""Retrieves the stored GitHub personal access token, if any.

		Returns:
			str | None: The token, or ``None`` if nothing has been saved yet.
		"""
		return keyring.get_password(_SERVICE_NAME, _USERNAME)

	@staticmethod
	def set_token(token: str) -> None:
		"""Persists a GitHub personal access token in the OS credential store.

		Args:
			token (str): The personal access token to store.
		"""
		keyring.set_password(_SERVICE_NAME, _USERNAME, token)

	@staticmethod
	def clear_token() -> None:
		"""Removes the stored GitHub personal access token, if any."""
		try:
			keyring.delete_password(_SERVICE_NAME, _USERNAME)
		except PasswordDeleteError:
			pass

	@staticmethod
	def parse_github_url(url: str) -> tuple[str, str, str, str]:
		"""Parses a GitHub file URL into its API components.

		Accepts either a normal "blob" URL (as seen when browsing a repo,
		e.g. ``https://github.com/{owner}/{repo}/blob/{ref}/{path}``) or a
		``raw.githubusercontent.com`` URL.

		Args:
			url (str): The GitHub file URL to parse.

		Returns:
			tuple[str, str, str, str]: ``(owner, repo, ref, path)``.

		Raises:
			RemoteConfigError: If ``url`` doesn't match either known format.
		"""
		# GitHub's private-repo "raw" links carry a short-lived signed
		# "?token=..." query param for anonymous access. It's irrelevant
		# once we're authenticating via the PAT, but left in place it would
		# get swallowed into the path capture group below.
		scheme, netloc, path, _, _ = urlsplit(url)
		url = urlunsplit((scheme, netloc, path, "", ""))

		match = GithubToken._BLOB_URL_RE.match(url)
		if match is not None:
			return match["owner"], match["repo"], match["ref"], match["path"]

		match = GithubToken._RAW_URL_RE.match(url)
		if match is not None:
			ref = match["ref_prefixed"] or match["ref_plain"]
			return match["owner"], match["repo"], ref, match["path"]

		raise RemoteConfigError(f"Unrecognized GitHub file URL: {url!r}")

	@staticmethod
	def fetch_file(url: str, timeout: float = 10) -> bytes:
		"""Downloads a file from a (possibly private) GitHub repo.

		Uses the GitHub Contents API rather than requesting
		``raw.githubusercontent.com`` directly, since the Contents API
		works uniformly for public and private repos and gives clear
		HTTP status codes to branch on.

		Args:
			url (str): A GitHub "blob" or raw file URL, as accepted by
				:meth:`parse_github_url`.
			timeout (float, optional): Request timeout in seconds.
				Defaults to 10.

		Returns:
			bytes: The raw file contents.

		Raises:
			RemoteConfigError: If the URL can't be parsed, no token is
				stored, or the request fails (auth, missing file, network).
		"""
		logger = logging.getLogger(__name__)

		owner, repo, ref, path = GithubToken.parse_github_url(url)

		token = GithubToken.get_token()
		if not token:
			raise RemoteConfigError("No GitHub token is configured; set one before fetching private files.")

		api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
		headers = {
			"Accept": "application/vnd.github.raw",
			"Authorization": f"Bearer {token}",
			"X-GitHub-Api-Version": "2022-11-28",
		}

		logger.debug(f"Fetching remote config file: {api_url} (ref={ref})")

		try:
			response = _SESSION.get(api_url, headers=headers, params={"ref": ref}, timeout=timeout)
			response.raise_for_status()
		except requests.RequestException as e:
			# GitHub's API error responses are JSON with a "message" field
			# explaining the actual cause (bad scope, SSO not authorized,
			# fine-grained token not granted repo access, etc), which
			# str(e) alone doesn't include.
			detail = ""
			if e.response is not None:
				try:
					detail = f" — {e.response.json()['message']}"
				except (ValueError, KeyError):
					pass
			raise RemoteConfigError(f"Failed to fetch {url!r}: {e}{detail}") from e

		return response.content
