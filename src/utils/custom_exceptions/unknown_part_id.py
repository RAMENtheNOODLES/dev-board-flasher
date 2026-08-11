

class UnknownPartID(Exception):
	"""Raised when an unknown part id is inputted.

	Args:
		board_part_id (str): The unrecognized part ID name that was looked
			up.
	"""