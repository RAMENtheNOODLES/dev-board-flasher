

class RemoteConfigError(Exception):
	"""Raised when a remote board/flasher config file can't be retrieved.

	Args:
		message (str): Human-readable description of what went wrong
			(bad URL, missing/invalid token, HTTP failure, etc).
	"""
