from enum import Enum, unique

@unique
class BoardPartID(Enum):
	UNDEF = 0
	ATMEGA328P = 1