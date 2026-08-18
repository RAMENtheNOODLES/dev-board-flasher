import hashlib
import hmac
import json
import logging
import os
from enum import Enum, unique
from typing import Any

from PySide6.QtCore import QStandardPaths

from .stored_settings import StoredSettings

_HASHING_METHOD = "sha256"

@unique
class CacheHelper(Enum):
	"""Named on-disk JSON caches, each integrity-checked against a stored hash.

	Each member's value is the cache file's name under
	:meth:`get_cache_path`. Every write records a SHA-256 hash of the file's
	contents (in ``StoredSettings.STORED_CACHE_HASHES``, itself encrypted via
	:meth:`StoredSettings.secure_set`); every read recomputes the hash and
	refuses to load the file if it doesn't match, so a cache file edited or
	replaced outside the app (accidentally or maliciously) is treated as
	untrusted and quietly discarded rather than loaded as-is.
	"""

	BOARD_CACHE = "board_config.cache"

	def get(self, default_value: Any = None) -> Any:
		"""Loads this cache's stored value, verifying it against its recorded hash.

		Args:
			default_value (Any, optional): Value to return, and to write as
				the new cache contents, if no cache file exists yet.
				Defaults to ``None``.

		Returns:
			Any: The cached value, or ``default_value`` if the cache file is
				missing, has no recorded hash, fails the hash check, or
				can't be decoded as JSON.
		"""
		logger = logging.getLogger(__name__)
		cache_path = CacheHelper.get_cache_path()
		out = os.path.join(cache_path, self.value)

		logger.debug(f"Retrieving cache ({self.name} [{self.value}]) at loc: {out}")

		if not os.path.isfile(out):
			self.update(default_value)
			return default_value

		with open(out, "rb") as file:
			stored_caches: dict[str, str] = StoredSettings.STORED_CACHE_HASHES.secure_get({})
			if self.name not in stored_caches:
				logger.warning(f"No stored hash found for cache ({self.name}), refusing to load untrusted cache file...")
				return default_value

			file_hash = hashlib.file_digest(file, _HASHING_METHOD).hexdigest()

			if not hmac.compare_digest(file_hash, stored_caches[self.name]):
				logger.warning("Cached Hash does not match actual... Something changed the cache externally...")
				return default_value

			# file_digest reads through to EOF, so rewind before decoding.
			file.seek(0)
			try:
				return json.loads(file.read().decode("utf-8"))
			except (json.JSONDecodeError, UnicodeDecodeError) as e:
				logger.warning(f"Failed to decode cache ({self.name}): {e}")
				return default_value

	def update(self, value: Any):
		"""Writes ``value`` as this cache's new contents and records its hash.

		Args:
			value (Any): The JSON-serializable value to persist. Values that
				``json.dumps`` can't natively serialize (e.g. TOML
				dates/times) are stringified via ``default=str``.
		"""
		logger = logging.getLogger(__name__)
		cache_path = CacheHelper.get_cache_path()
		cache_file = os.path.join(cache_path, self.value)

		logger.debug(f"Retrieving cache ({self.name} [{self.value}]) at loc: {cache_file}")

		with open(cache_file, "wb") as file:
			# default=str guards against TOML values (e.g. dates/times) that
			# tomllib parses into types json can't natively serialize.
			file.write(json.dumps(value, default=str).encode("utf-8"))

		# Create new hash
		with open(cache_file, "rb") as file:
			new_hash = hashlib.file_digest(file, _HASHING_METHOD)
			cache: dict[str, str] = StoredSettings.STORED_CACHE_HASHES.secure_get({})
			cache[self.name] = new_hash.hexdigest()
			StoredSettings.STORED_CACHE_HASHES.secure_set(cache, 1800)

	@staticmethod
	def get_cache_path() -> str:
		"""Returns the app's cache directory, creating it if it doesn't exist yet."""
		out = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation)
		os.makedirs(out, exist_ok=True)
		return out

	@staticmethod
	def invalidate_cache():
		"""Clears the recorded cache hashes, so every cache is treated as untrusted and rebuilt on next use."""
		StoredSettings.STORED_CACHE_HASHES.secure_set({}, 0)
	