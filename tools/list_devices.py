#!/usr/bin/env python3
'''
This utility looks through a directory of Logitech Gaming Software
"game" profiles, then extracts and lists the names of each device type found within.
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
import os
from re import compile as rxcompile
from argparse import ArgumentParser

if sys.platform == "win32":
	GK_DEFAULT_LGS_PROFILE_PATH = os.getenv('LOCALAPPDATA', "") + r"\Logitech\Logitech Gaming Software\profiles"
elif sys.platform == "darwin":
	GK_DEFAULT_LGS_PROFILE_PATH = os.path.expanduser("~/Library/Application Support/Logitech/profiles")
else:
	sys.exit(f"Unsupported/unknown platform: {sys.platform}")

GK_PROF_NAME_RE = rxcompile('<profile .+name="([^"]*)"')
GK_DEV_TYPE_RE = rxcompile('<assignments .*devicecategory="Logitech.Gaming.([^"]+)"')

def parse_profile(path):
	with open(path, "r") as prof_file:
		prof = prof_file.read()
	prof_name = GK_PROF_NAME_RE.search(prof)
	if not prof_name:
		return None, []
	prof_name = prof_name.group(1)
	devs = []
	for m in GK_DEV_TYPE_RE.finditer(prof):
		devs.append(m.group(1))
	return prof_name, devs

def check_profiles(path, list_all=False):
	print(f"Loading profiles from {path}")
	all_devs = []
	with os.scandir(path) as it:
		for entry in it:
			if entry.is_file and entry.name.endswith(".xml"):
				print("Processing: " + entry.name)
				name, devs = parse_profile(os.path.join(path, entry.name))
				if not name:
					print("WARNING: Could not find a profile name in " + entry.name)
					continue
				print("Profile name: " + name)
				if not devs:
					print("WARNING: No devices found!\n")
					continue
				for dev in devs:
					print("    " + dev)
					if dev not in all_devs:
						all_devs.append(dev)
				print("")
	return all_devs


def main():
	# handle CLI arguments
	parser = ArgumentParser()
	parser.add_argument("-p", metavar="<path>",
	                    help=f"Full path of game profiles directory (default is: '{GK_DEFAULT_LGS_PROFILE_PATH}')",
	                    default=GK_DEFAULT_LGS_PROFILE_PATH)
	opts = parser.parse_args()
	del parser

	if not os.path.exists(opts.p):
		raise ValueError(f"ERROR: Game profiles path {opts.p} not found.")

	all_devs = check_profiles(opts.p)

	print("")
	if all_devs:
		print("Unique device type(s) found:\n")
		for dev in all_devs:
			print(dev)
	else:
		print("No device names were found!")


if __name__ == "__main__":
	try:
		main()
		ret = 0
	except Exception as e:
		from traceback import format_exc
		print(format_exc())
		ret = -1
	finally:
		print("")
		input("Press Enter to exit... :-)")
	sys.exit(ret)
