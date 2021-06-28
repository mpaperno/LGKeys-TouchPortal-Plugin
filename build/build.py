#!/usr/bin/env python3
'''
Assembles a plugin distribution.
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
from zipfile import (ZipFile, ZIP_DEFLATED)
import PyInstaller.__main__
from argparse import ArgumentParser
from shutil import rmtree
from glob import glob

GK_SRC = "../src/"
GK_TOOLS = "../tools/"
GK_ASSTS = "../assets/"

sys.path.insert(1, GK_SRC)
from main import (__version__ as lgk_version, GK_PLUGIN_NAME)

GK_TPP_NAME = "LGKeys.tpp"
GK_MAIN_NAME = "lgkeys"
GK_UPDATER_NAME = "update_profiles"
GK_LISTER_NAME = "list_devices"
GK_INTEGRATION_SCRIPT = GK_TOOLS + "lgkeys-integration.lua"
GK_ICON_FILE_BASE = GK_SRC + "images/icon-24"
GK_DIST_FOLDER = GK_PLUGIN_NAME.replace(" ", "-") + "/"
GK_DIST_TOOLS = GK_DIST_FOLDER + "tools/"
GK_EXE_SFX = ".exe" if sys.platform == "win32" else ""

GK_PACKING_LIST = {
	GK_TPP_NAME : GK_DIST_FOLDER,
	GK_UPDATER_NAME + GK_EXE_SFX : GK_DIST_TOOLS,
	GK_LISTER_NAME + GK_EXE_SFX : GK_DIST_TOOLS,
	GK_ASSTS : GK_DIST_FOLDER,
}
if sys.platform == "win32":
	GK_PACKING_LIST[GK_INTEGRATION_SCRIPT] = GK_DIST_TOOLS

GK_TPP_PACK_LIST = {
	GK_MAIN_NAME + GK_EXE_SFX : "./",
	GK_SRC + "entry.tp" : "./",
	GK_SRC + GK_ICON_FILE_BASE + ".png" : "./images/",
}

GK_OS_WIN = 1
GK_OS_MAC = 2
# common options for PyInstaller
GK_PI_COMMON = [
		'--clean',
		'--console',
		'--onefile',
		'--distpath=./',
		f'--icon={GK_ICON_FILE_BASE}.ico',
]


def zip_dir(zf, path, base_path="./", recurse=True):
	relroot = os.path.abspath(os.path.join(path, os.pardir))
	for root, _, files in os.walk(path):
		zf.write(os.path.join(root, "."))
		for file in files:
			src = os.path.join(root, file)
			if os.path.isfile(src):
				dst = os.path.join(base_path, os.path.relpath(root, relroot), file)
				zf.write(src, dst)
			elif recurse and os.path.isdir(src):
				zip_dir(zf, src, base_path)


def build_main(opsys):
	print(f"Building {GK_MAIN_NAME} (main)")
	pi_run = [
		GK_SRC + "main.py",
		'--name=' + GK_MAIN_NAME,
	]
	if opsys == GK_OS_WIN:
		pi_run.append(
			f'--add-binary={GK_SRC}modules/lib/LGS Debug Interceptor.dll;./modules/lib'
		)
	pi_run.extend(GK_PI_COMMON)
	PyInstaller.__main__.run(pi_run)
	print("")

def build_updater():
	print("Building " + GK_UPDATER_NAME)
	pi_run = [
		GK_TOOLS + GK_UPDATER_NAME + ".py",
		f'--name={GK_UPDATER_NAME}',
		f'--add-data={GK_INTEGRATION_SCRIPT};./'
	]
	pi_run.extend(GK_PI_COMMON)
	PyInstaller.__main__.run(pi_run)
	print("")

def build_lister():
	print("Building " + GK_LISTER_NAME)
	pi_run = [
		GK_TOOLS + GK_LISTER_NAME + ".py",
		'--name=' + GK_LISTER_NAME
	]
	pi_run.extend(GK_PI_COMMON)
	PyInstaller.__main__.run(pi_run)
	print("")

def build_tpp():
	zip_name = GK_TPP_NAME
	print("Creating archive: " + zip_name)
	with ZipFile(zip_name, "w", ZIP_DEFLATED) as zf:
		for src, dest in GK_TPP_PACK_LIST.items():
			zf.write(src, dest + os.path.basename(src))
	print("")

def build_distro(opsys, ver):
	os_name = "windows" if opsys == GK_OS_WIN else "macos"
	zip_name = GK_DIST_FOLDER.rstrip("/") + "_v" + ver + "_" + os_name + ".zip"
	print("Creating archive: "+ zip_name)
	with ZipFile(zip_name, "w", ZIP_DEFLATED) as zf:
		for src, dest in GK_PACKING_LIST.items():
			if os.path.isdir(src):
				zip_dir(zf, src, dest)
			elif os.path.isfile(src):
				zf.write(src, dest + os.path.basename(src))
	print("")

def build_clean():
	print("Cleaning up...")
	files = glob("./*.spec")
	files.extend(glob("./*.exe"))
	files.extend([GK_MAIN_NAME, GK_LISTER_NAME, GK_UPDATER_NAME, GK_TPP_NAME, "./build"])
	for file in files:
		if os.path.exists(file):
			print("removing: " + file)
			if os.path.isfile(file):
				os.remove(file)
			elif os.path.isdir(file):
				rmtree(file)
	print("")


def main():
	if sys.platform == "win32":
		opsys = GK_OS_WIN
	elif sys.platform == "darwin":
		opsys = GK_OS_MAC
	else:
		return "Unsupported OS: " + sys.platform

	parser = ArgumentParser()
	parser.add_argument(
		"targets", metavar='<target>', nargs="*", type=str, default="all",
		help='What to build. "all" (default) means all targets except "clean". ' +
		     "Or, one or more of: [main, updater, lister, plugin, distro, clean]. " +
		     '"clean" removes all build artifacts except the final distro archive (.zip) ' +
		     'and is run last (so "build.py all clean" will build and clean but leave the produced distro).'
	)
	parser.add_argument("-v", metavar='<version>', nargs=1, type=str, default=lgk_version,
	                    help="Override default plugin version. Detected version is: " + lgk_version)

	opts = parser.parse_args()
	del parser

	print("")
	print(f"Building {GK_PLUGIN_NAME} v{opts.v} target(s) {repr(opts.targets)} on {sys.platform}\n")

	build_all = "all" in opts.targets
	if build_all or "main" in opts.targets:
		build_main(opsys)
	if build_all or "lister" in opts.targets:
		build_lister()
	if opsys == GK_OS_WIN and (build_all or "updater" in opts.targets):
		build_updater()
	if build_all or "plugin" in opts.targets:
		build_tpp()
	if build_all or "distro" in opts.targets:
		build_distro(opsys, opts.v)
	if "clean" in opts.targets:
		build_clean()

	return 0

if __name__ == "__main__":
	sys.exit(main())
