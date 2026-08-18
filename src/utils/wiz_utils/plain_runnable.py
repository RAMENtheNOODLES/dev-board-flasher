import threading

from PySide6.QtCore import QRunnable


class PlainRunnable(QRunnable):
	"""Base class for a cancellable :class:`QRunnable` run on a :class:`QThreadPool`.

	Subclasses implement :meth:`run` and should periodically check (or block
	on) ``self.stop_event`` so callers can ask the task to wind down by
	calling ``stop_event.set()`` instead of killing the thread outright.
	"""

	def __init__(self, task_id: str, stop_event: threading.Event):
		super().__init__()
		self.task_id = task_id
		self.stop_event = stop_event

	def run(self):
		raise NotImplementedError