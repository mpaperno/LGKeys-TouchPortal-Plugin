'''
Python binding/API for the "LGS Debug Interceptor" library
by Gondwana Software (https://gondwanasoftware.net.au/lgsdi.shtml).
Supported only Windows x64, requires 64-bit Python.
'''

__copyright__ = '''
This file is part of the LGKeys TouchPortal Plugin project
Copyright Maxim Paperno; all rights reserved.

This file may be used under the terms of the GNU
General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

A copy of the GNU General Public License is available at <http://www.gnu.org/licenses/>.
'''

import sys
from logging import getLogger
from time import sleep, monotonic
from pathlib import Path
from ctypes import (CFUNCTYPE, c_int, c_char_p)
try:
	from ctypes import WinDLL
except:
	pass

__all__ = ['LGSDInterface']

DLLPATH = str(Path(__file__).parent / "lib/LGS Debug Interceptor.dll")

MessageCallbackType = CFUNCTYPE(c_int, c_char_p)
StatusCallbackType = CFUNCTYPE(None, c_int)

class LGSDInterface():
	def __init__(self, message_callback=None, filter_msgs:list=None):
		self.lib = None
		if sys.platform != "win32" or sys.maxsize < 2**32:
			raise SystemError("This module only works on Windows x64.")
		try:
			self.lib = WinDLL(DLLPATH)
		except Exception as e:
			raise SystemError(f"Couldn't load {DLLPATH} with error: \n{repr(e)}")

		self.log = getLogger("LGSDI")
		self.is_connected = False
		self.status_resp = 0
		self.filter = filter_msgs
		self._callback = message_callback
		self._messageCallbackPtr = MessageCallbackType(self._messageCallback)
		self._statusCallbackPtr = StatusCallbackType(self._statusCallback)

	def _messageCallback(self, msg):
		self.log.debug(f"Got message: {msg}")
		msg = msg.decode("ascii")
		if msg and self._callback and not self.filter or msg.split(".")[0] in self.filter:
			self._callback(msg)
		return 0

	def _statusCallback(self, stat):
		self.log.debug(f"Got status: {stat:d}")
		self.status_resp = stat

	def connect(self):
		if not self.is_connected:
			self.status_resp = self.lib.LGSDIConnectCallback(True, self._messageCallbackPtr, self._statusCallbackPtr)
			# self._statusCallback(stat)
			self.is_connected = (self.status_resp == 0)

	def disconnect(self):
		if self.is_connected:
			self.status_resp = self.lib.LGSDIDisconnect()
			to = False
			start = monotonic()
			while self.status_resp != 16 and not to:
				sleep(0.01)
				to = (monotonic() - start > 5.0)
			if to:
				raise Warning("Disconnection timed out!")
			self.is_connected = False

	def set_filter(self, filter_msgs:list):
		self.filter = filter_msgs


# for testing interactively
def main():
	def callbackTest(msg):
		print(f"Got message in callback: {msg}")

	from logging import basicConfig
	basicConfig(level=10, stream=sys.stdout)
	lib = LGSDInterface(callbackTest)
	if not lib:
		return -1

	ret = 0
	try:
		lib.connect()

		while 1:
			sleep(1)

	except KeyboardInterrupt:
		pass
	except Exception as e:
		print(f"Caught: {repr(e)}")
		ret = -1
	finally:
		lib.disconnect()

	return ret

if __name__ == "__main__":
  sys.exit(main())
