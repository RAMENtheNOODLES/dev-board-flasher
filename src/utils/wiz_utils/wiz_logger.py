from typing import Any, ClassVar


class WizLogger:
	"""Holds the app's ``logging.config.dictConfig`` setup.

	Applied once at startup (see ``if __name__ == "__main__"`` in
	``main.py``) via ``logging.config.dictConfig(WizLogger.LOGGING_CONFIG)``.
	Logs at ``DEBUG`` and above to both the console and a rotating
	``upload_wiz.log`` file (10MB per file, 5 backups kept).
	"""

	LOGGING_CONFIG: ClassVar[dict[str, Any]] = {
		"version": 1,
		"disable_existing_loggers": False,
		"formatters": {
			"standard": {
				"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
			},
		},
		"handlers": {
			"console": {
				"class": "logging.StreamHandler",
				"formatter": "standard",
				"level": "DEBUG",
				"stream": "ext://sys.stdout",
			},
			"file": {
				"class": "logging.handlers.RotatingFileHandler",
				"formatter": "standard",
				"level": "DEBUG",
				"filename": "upload_wiz.log",
				"maxBytes": 10485760,  # 10MB per file split
				"backupCount": 5,
			},
		},
		"loggers": {
			"": {  # Configuration for the absolute root logger
				"handlers": ["console", "file"],
				"level": "DEBUG",
			},
		},
	}