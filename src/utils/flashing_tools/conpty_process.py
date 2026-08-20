from __future__ import annotations

import ctypes
import logging
import subprocess
import threading
from ctypes import wintypes

from PySide6.QtCore import QObject, Signal

_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

_PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE = 0x00020016
_EXTENDED_STARTUPINFO_PRESENT = 0x00080000
_INFINITE = 0xFFFFFFFF


class _COORD(ctypes.Structure):
	_fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]


class _STARTUPINFOW(ctypes.Structure):
	_fields_ = [
		("cb", wintypes.DWORD),
		("lpReserved", wintypes.LPWSTR),
		("lpDesktop", wintypes.LPWSTR),
		("lpTitle", wintypes.LPWSTR),
		("dwX", wintypes.DWORD),
		("dwY", wintypes.DWORD),
		("dwXSize", wintypes.DWORD),
		("dwYSize", wintypes.DWORD),
		("dwXCountChars", wintypes.DWORD),
		("dwYCountChars", wintypes.DWORD),
		("dwFillAttribute", wintypes.DWORD),
		("dwFlags", wintypes.DWORD),
		("wShowWindow", wintypes.WORD),
		("cbReserved2", wintypes.WORD),
		("lpReserved2", ctypes.c_void_p),
		("hStdInput", wintypes.HANDLE),
		("hStdOutput", wintypes.HANDLE),
		("hStdError", wintypes.HANDLE),
	]


class _STARTUPINFOEXW(ctypes.Structure):
	_fields_ = [
		("StartupInfo", _STARTUPINFOW),
		("lpAttributeList", ctypes.c_void_p),
	]


class _PROCESS_INFORMATION(ctypes.Structure):
	_fields_ = [
		("hProcess", wintypes.HANDLE),
		("hThread", wintypes.HANDLE),
		("dwProcessId", wintypes.DWORD),
		("dwThreadId", wintypes.DWORD),
	]


_kernel32.CreatePipe.argtypes = [
	ctypes.POINTER(wintypes.HANDLE), ctypes.POINTER(wintypes.HANDLE), ctypes.c_void_p, wintypes.DWORD,
]
_kernel32.CreatePipe.restype = wintypes.BOOL

_kernel32.CreatePseudoConsole.argtypes = [
	_COORD, wintypes.HANDLE, wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p),
]
_kernel32.CreatePseudoConsole.restype = ctypes.c_long

_kernel32.ClosePseudoConsole.argtypes = [ctypes.c_void_p]
_kernel32.ClosePseudoConsole.restype = None

_kernel32.InitializeProcThreadAttributeList.argtypes = [
	ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.c_size_t),
]
_kernel32.InitializeProcThreadAttributeList.restype = wintypes.BOOL

_kernel32.UpdateProcThreadAttribute.argtypes = [
	ctypes.c_void_p, wintypes.DWORD, ctypes.c_size_t, ctypes.c_void_p,
	ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p,
]
_kernel32.UpdateProcThreadAttribute.restype = wintypes.BOOL

_kernel32.DeleteProcThreadAttributeList.argtypes = [ctypes.c_void_p]
_kernel32.DeleteProcThreadAttributeList.restype = None

_kernel32.CreateProcessW.argtypes = [
	wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
	wintypes.BOOL, wintypes.DWORD, ctypes.c_void_p, wintypes.LPCWSTR,
	ctypes.POINTER(_STARTUPINFOEXW), ctypes.POINTER(_PROCESS_INFORMATION),
]
_kernel32.CreateProcessW.restype = wintypes.BOOL

_kernel32.ReadFile.argtypes = [
	wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p,
]
_kernel32.ReadFile.restype = wintypes.BOOL

_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
_kernel32.CloseHandle.restype = wintypes.BOOL

_kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
_kernel32.GetExitCodeProcess.restype = wintypes.BOOL

_kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
_kernel32.TerminateProcess.restype = wintypes.BOOL

_kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
_kernel32.WaitForSingleObject.restype = wintypes.DWORD


class _StdOutBuffer:
	"""Stand-in for ``QByteArray``'s ``.data()``.

	Lets :meth:`ConPtyProcess.readAllStandardOutput` be swapped in for
	``QProcess.readAllStandardOutput`` without changing
	``BaseFlashingTool.read_terminal_stream``, which calls
	``self.process.readAllStandardOutput().data()``.
	"""

	__slots__ = ("_buf",)

	def __init__(self, buf: bytes) -> None:
		self._buf = buf

	def data(self) -> bytes:
		return self._buf


class ConPtyProcess(QObject):
	"""Runs a child process attached to a real Windows console (ConPTY).

	Some CLI tools call Win32 console APIs directly (``WriteConsole``,
	``SetConsoleCursorPosition``, colored ``SetConsoleTextAttribute``
	output) to draw progress bars or status text. Those calls silently
	no-op when stdout/stderr are plain anonymous pipes -- which is what
	``QProcess`` hands a child by default -- so such tools produce no
	captured output at all, even though the same binary logs fine when run
	in a real terminal window. Attaching the child to a pseudo console
	instead gives it a real console handle, so those calls behave as they
	do interactively.

	Exposes the same ``readyReadStandardOutput``/``finished`` signals and
	``readAllStandardOutput()`` shape as ``QProcess`` so
	:class:`BaseFlashingTool` can treat either backend identically (see
	``read_terminal_stream``/``process_finished``). Selected per tool via
	the ``use_pty`` config flag (see :class:`BaseFlashingTool`).
	"""

	readyReadStandardOutput = Signal()
	finished = Signal(int, int)

	def __init__(self, parent: QObject | None = None) -> None:
		super().__init__(parent)
		self.logger = logging.getLogger(__name__)
		self._buffer = bytearray()
		self._lock = threading.Lock()
		self._hpc: ctypes.c_void_p | None = None
		self._process_handle: wintypes.HANDLE | None = None
		self._pipe_in_write: wintypes.HANDLE | None = None
		self._pipe_out_read: wintypes.HANDLE | None = None
		self._reader_thread: threading.Thread | None = None

	def start(self, program: str, args: list[str]) -> None:
		"""Launches ``program`` with ``args`` attached to a fresh pseudo console.

		Args:
			program (str): Path to the executable, or a bare name resolved
				via PATH.
			args (list[str]): Command-line arguments to pass.
		"""
		self._cleanup()
		self._buffer.clear()

		cmdline = subprocess.list2cmdline([program, *args])
		self.logger.debug(f"Starting ConPTY process: {cmdline}")
		self._spawn(cmdline)

	def readAllStandardOutput(self) -> _StdOutBuffer:
		with self._lock:
			data = bytes(self._buffer)
			self._buffer.clear()
		return _StdOutBuffer(data)

	def _spawn(self, cmdline: str) -> None:
		# One pipe pair for the pty's input side (unused -- the tools this
		# backend targets are one-shot flashing commands, not interactive),
		# one for its output side (child writes via console, we read).
		pty_in_read = wintypes.HANDLE()
		pty_in_write = wintypes.HANDLE()
		pty_out_read = wintypes.HANDLE()
		pty_out_write = wintypes.HANDLE()

		if not _kernel32.CreatePipe(ctypes.byref(pty_in_read), ctypes.byref(pty_in_write), None, 0):
			raise ctypes.WinError(ctypes.get_last_error())
		if not _kernel32.CreatePipe(ctypes.byref(pty_out_read), ctypes.byref(pty_out_write), None, 0):
			raise ctypes.WinError(ctypes.get_last_error())

		hpc = ctypes.c_void_p()
		hr = _kernel32.CreatePseudoConsole(_COORD(120, 32), pty_in_read, pty_out_write, 0, ctypes.byref(hpc))
		if hr != 0:
			raise ctypes.WinError(hr)

		# The pseudo console owns its ends of the pipes now.
		_kernel32.CloseHandle(pty_in_read)
		_kernel32.CloseHandle(pty_out_write)

		attr_size = ctypes.c_size_t(0)
		_kernel32.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(attr_size))
		attr_list = (ctypes.c_char * attr_size.value)()
		if not _kernel32.InitializeProcThreadAttributeList(ctypes.byref(attr_list), 1, 0, ctypes.byref(attr_size)):
			raise ctypes.WinError(ctypes.get_last_error())

		if not _kernel32.UpdateProcThreadAttribute(
			ctypes.byref(attr_list), 0, _PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE,
			hpc, ctypes.sizeof(ctypes.c_void_p), None, None,
		):
			raise ctypes.WinError(ctypes.get_last_error())

		startup_info = _STARTUPINFOEXW()
		startup_info.StartupInfo.cb = ctypes.sizeof(_STARTUPINFOEXW)
		startup_info.lpAttributeList = ctypes.cast(attr_list, ctypes.c_void_p)

		process_info = _PROCESS_INFORMATION()
		cmdline_buf = ctypes.create_unicode_buffer(cmdline)

		ok = _kernel32.CreateProcessW(
			None, cmdline_buf, None, None, False,
			_EXTENDED_STARTUPINFO_PRESENT, None, None,
			ctypes.byref(startup_info), ctypes.byref(process_info),
		)
		_kernel32.DeleteProcThreadAttributeList(ctypes.byref(attr_list))
		if not ok:
			raise ctypes.WinError(ctypes.get_last_error())

		_kernel32.CloseHandle(process_info.hThread)

		self._hpc = hpc
		self._process_handle = process_info.hProcess
		self._pipe_in_write = pty_in_write
		self._pipe_out_read = pty_out_read

		self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
		self._reader_thread.start()

	def kill(self) -> None:
		"""Forcibly terminates the running process, if any.

		For tools that finish their real work but then hang on a blocking
		prompt (e.g. "press enter to exit") rather than exiting on their
		own -- see :attr:`BaseFlashingTool.stop_on`. Closing the pty's
		output-read handle out from under the reader thread's blocked
		``ReadFile`` call makes that call fail and return, so
		:meth:`_read_loop` still runs its normal cleanup/finished path
		afterward instead of hanging forever.

		Deliberately leaves ``_process_handle`` open here rather than
		closing it along with the other handles: :meth:`_read_loop` still
		needs it after the read loop unblocks, to read back the exit code
		via ``GetExitCodeProcess`` (closing it early would make that call a
		no-op against a null handle, always reporting exit code 0 --
		i.e. success -- regardless of what actually happened). Note the
		exit code read back is whatever's passed to ``TerminateProcess``
		below, not whatever the tool itself would have eventually returned:
		a process that's still blocked on a prompt hasn't called
		``ExitProcess`` yet, so Windows has no "real" exit code to report
		until it does.
		"""
		with self._lock:
			if self._process_handle:
				_kernel32.TerminateProcess(self._process_handle, 1)
			if self._hpc is not None:
				_kernel32.ClosePseudoConsole(self._hpc)
				self._hpc = None
			if self._pipe_out_read:
				_kernel32.CloseHandle(self._pipe_out_read)
				self._pipe_out_read = None

	def _read_loop(self) -> None:
		chunk = ctypes.create_string_buffer(4096)
		bytes_read = wintypes.DWORD()

		while True:
			pipe_out_read = self._pipe_out_read
			if not pipe_out_read:
				break
			ok = _kernel32.ReadFile(pipe_out_read, chunk, len(chunk), ctypes.byref(bytes_read), None)
			if not ok or bytes_read.value == 0:
				break
			with self._lock:
				self._buffer.extend(chunk.raw[: bytes_read.value])
			self.readyReadStandardOutput.emit()

		process_handle = self._process_handle
		exit_code = wintypes.DWORD()
		if process_handle:
			_kernel32.WaitForSingleObject(process_handle, _INFINITE)
			_kernel32.GetExitCodeProcess(process_handle, ctypes.byref(exit_code))

		self._cleanup()
		self.finished.emit(exit_code.value, 0)

	def _cleanup(self) -> None:
		with self._lock:
			self._close_handles_locked()

	def _close_handles_locked(self) -> None:
		"""Closes any open handles. Caller must hold ``self._lock``."""
		if self._hpc is not None:
			_kernel32.ClosePseudoConsole(self._hpc)
			self._hpc = None
		for attr in ("_process_handle", "_pipe_in_write", "_pipe_out_read"):
			handle = getattr(self, attr)
			if handle:
				_kernel32.CloseHandle(handle)
				setattr(self, attr, None)
