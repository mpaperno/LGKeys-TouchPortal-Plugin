#!/usr/bin/env python3
'''
This utility modifies Logitech Gaming Software
"game" profiles to insert a special Lua script
which is used for integration with the LGKeys TouchPortal Plugin.
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
from shutil import copy2
from pathlib import Path
from argparse import ArgumentParser
from datetime import datetime

GK_DEFAULT_LGS_PROFILE_PATH = os.getenv('LOCALAPPDATA', "") + r"\Logitech\Logitech Gaming Software\profiles"
GK_PROF_NAME_RE = rxcompile('<profile .+name="([^"]*)"')
try:
	scrpt_path = str(Path(__file__).parent / "lgkeys-integration.lua")
	with open(scrpt_path, "r") as script_file:
		GK_LGSI_SCRIPT = script_file.read()
except:
	sys.exit("Could not find Lua integration script at: " + scrpt_path)

g_backup_path = ""
g_only_named = []

def add_script(path, fn):
	print(f"Processing: {fn}")
	full_path = os.path.join(path, fn)
	with open(full_path, "r") as prof_file:
		prof = prof_file.read()
	prof_name = GK_PROF_NAME_RE.search(prof)
	if not prof_name:
		print("WARNING: Could not find a profile name in this file, skipping.")
		return
	prof_name = prof_name.group(1)
	print(f"Profile name: {prof_name}")
	if g_only_named and prof_name not in g_only_named:
		print("SKIPPING")
		return
	tag_beg = prof.index("<script>")
	tag_end = prof.index("</script>", tag_beg) if tag_beg > -1 else -1
	if tag_beg < 0 or tag_end < 8:
		print("WARNING: Could not find proper <script> tag in file, skipping.")
		return
	key = prof[(tag_beg+8):tag_end]
	script = GK_LGSI_SCRIPT.replace("PROFILE_NAME", fn.split(".")[0])
	prof = prof.replace(key, script)
	# print(key+"\n", prof)
	if g_backup_path:
		print(f"Backing up {fn} to {g_backup_path}")
		copy2(full_path, g_backup_path)
	with open(full_path, "w") as prof_file:
		prof_file.write(prof)
	print("UPDATED profile " + prof_name)


def update_profiles(path):
	print(f"Loading profiles from {path}\n")
	with os.scandir(path) as it:
		for entry in it:
			if entry.is_file and entry.name.endswith(".xml"):
				add_script(path, entry.name)
				print("")


def main():
	global g_backup_path, g_only_named
	backup_default = "backup." + datetime.now().strftime("%Y%m%d%H%M%S")

	# handle CLI arguments
	parser = ArgumentParser()
	parser.add_argument("-p", metavar="<path>",
	                    help=f"Full path of game profiles directory (default is: '{GK_DEFAULT_LGS_PROFILE_PATH}')",
	                    default=GK_DEFAULT_LGS_PROFILE_PATH)
	parser.add_argument("-b", metavar="<path>",
	                    help=f"Full path for backup directory (default is: '<profiles_path>\\{backup_default}')")
	parser.add_argument("--nobak", action='store_true',
	                    help="Do NOT create profile backups.")
	parser.add_argument("--names", metavar='"<profile name>"', nargs="+", default=g_only_named,
	                    help="A list of one or more named profiles to modify, instead of all profiles. Put each name in quotes. "
											'For example: --names "Default Profile" "My Game"')

	opts = parser.parse_args()
	del parser

	if not os.path.exists(opts.p):
		raise ValueError(f"ERROR: Game profiles path {opts.p} not found.")

	print("")
	is_all = "some" if opts.names else "all"
	print(f"This program will add a custom Lua script to {is_all} LGS game profiles found in:")
	print(opts.p + "\n")
	if opts.names:
		g_only_named = opts.names
		print("Only the following profile(s) (if found) will be changed:\n" + repr(g_only_named) + "\n")
	print("WARNING:  !! Any existing scripts WILL BE DELETED !!\n")
	if not opts.nobak:
		g_backup_path = opts.b if opts.b else os.path.join(opts.p, backup_default)
		print("A backup of all modified profiles will be saved to:")
		print(g_backup_path + "\n")
		if os.path.exists(g_backup_path):
			print("WARNING: Using an existing backup folder. Any current backups in this folder may be overwritten!\n")
	else:
		print("WARNING: You have chosen NOT to make a backup!\n")

	print("Please make sure that both the Logitech Gaming Software and the LGKeys TouchPortal plugin are stopped. "
		"If LGS is not stopped, any profile changes made by this program will be lost.\n")
	confirm = input("Do you wish to continue? [y/N]: ").lower()
	if confirm: confirm = confirm[0]
	if not confirm == "y":
		print("Aborted, no changes will be made.")
		return 0

	print("\nStarting...")
	if not opts.nobak and not os.path.exists(g_backup_path):
		print("Creating backup folder: " + g_backup_path)
		os.mkdir(g_backup_path)

	update_profiles(opts.p,)
	print("")
	print("Finished updating profiles. You may now restart LGS and use the LGKeys plugin with integration enabled.")


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

