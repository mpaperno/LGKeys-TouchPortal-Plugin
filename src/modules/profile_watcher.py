'''
ProfileWatcher is a file system change monitor for detecting modifications
in a single directory. On Windows it uses Win32 API to wait for events,
otherwise it falls back to periodic scanning.
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

import os
import sys
from threading import Timer, Thread, Event
from logging import getLogger
import modules.utils as utils

__all__ = ['watch_profiles', 'WatcherThread']


def watch_profiles(path, stop_event, interval = 2.0, ext = ".xml"):

	def files_to_timestamp():
		ret = {}
		with os.scandir(path) as it:
			for entry in it:
				if entry.is_file and entry.name.endswith(ext):
					ret[entry.path] = entry.stat().st_mtime_ns
		return ret

	log = utils.Logger(getLogger(__name__))
	usewin32 = sys.platform == "win32"
	if usewin32:
		try:
			import win32file
			import win32event
			import win32con
			iInterval = int(interval * 1000)
			change_handle = win32file.FindFirstChangeNotification(
				path, False, win32con.FILE_NOTIFY_CHANGE_FILE_NAME | win32con.FILE_NOTIFY_CHANGE_LAST_WRITE
			)
		except Exception as e:
			log.err(f"Win32 error, reverting to polling mode. Error: {repr(e)}")
			usewin32 = False

	log.dbg(f"Watching {path} [interval: {interval:.02f}s, Win32: {usewin32}]")

	before = files_to_timestamp()
	try:
		while not stop_event.is_set():
			if usewin32:
				wait_result = win32event.WaitForSingleObject(change_handle, iInterval)
				if wait_result != win32con.WAIT_OBJECT_0:
					continue
			elif stop_event.wait(timeout=interval):
				break

			after = files_to_timestamp()
			added = [f for f in after.keys() if not f in before.keys()]
			removed = []
			modified = []
			# modified = {}
			for (f, m) in before.items():
				if not f in after.keys():
					removed.append(f)
				elif (os.stat(f).st_mtime_ns - m) > 50000000:  # ignore <= 50ms deltas
					modified.append(f)
			if added or modified or removed:
				# log.dbg('Modified: {}'.format(', '.join(modified)))
				# log.dbg('Removed: {}'.format(', '.join(removed)))
				yield (added, modified, removed)

			before = after
			if usewin32:
				win32file.FindNextChangeNotification(change_handle)
		#
	except Exception as e:
		log.err(f"Exception in file system watcher, exiting: {repr(e)}")
	else:
		log.dbg("File watcher got IRQ, stopping")
	finally:
		if usewin32:
			win32file.FindCloseChangeNotification(change_handle)


class WatcherThread(Thread):
	def __init__(self, path, mod_callback, interval = 2.0, ext = ".xml"):
		super(WatcherThread, self).__init__(daemon=True)
		self.stop_event = Event()
		self.path = path
		self.mod_callback = mod_callback
		self.interval = interval
		self.filter_ext = ext

	def run(self):
		watch = watch_profiles(
			self.path,
			self.stop_event,
			self.interval,
			self.filter_ext
		)
		for result in watch:
			# delay 5ms otherwise files may still be unreadable
			Timer(0.005, self.mod_callback, (result[0], result[1], result[2])).start()

	def join(self, timeout=None):
		self.stop_event.set()
		super().join(timeout)
