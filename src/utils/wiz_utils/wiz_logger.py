class WizLogger:
	LOGGING_CONFIG = {
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
				"level": "INFO",
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