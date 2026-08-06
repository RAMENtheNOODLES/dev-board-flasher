from enum import Enum, unique

@unique
class BoardType(Enum):
	UNKNOWN = 0
	ARDUINO = 1
	ESPIDF = 2