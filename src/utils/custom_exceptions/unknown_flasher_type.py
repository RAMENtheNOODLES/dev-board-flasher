

class UnknownFlasherType(Exception):
	"""Raised when an unknown flasher is inputted.

	Args:
		flasher_name (str): The unrecognized flasher/tool name or type that
			was looked up.
	"""
	pass