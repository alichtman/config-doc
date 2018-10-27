import os
import sys
import json
from utils import home_prefix
from printing import *


def get_config_path():
	return home_prefix(".shallow-backup")


def get_config():
	"""
	Returns the config.
	:return: dictionary for config
	"""
	with open(get_config_path()) as f:
		config = json.load(f)
	return config


def write_config(config):
	"""
	Write to config file
	"""
	with open(get_config_path(), 'w') as f:
		json.dump(config, f, indent=4)


def get_default_config():
	"""
	Returns a default configuration.
	"""
	return {
		"backup_path": "~/shallow-backup",
		"dotfiles"   : [
			".bashrc",
			".bash_profile",
			".gitconfig",
			".profile",
			".pypirc",
			".shallow-backup",
			".vimrc",
			".zshrc"
		],
		"dotfolders" : [
			".ssh",
			".vim"
		],
		"default-gitignore"  : [
			"dotfiles/.ssh",
			"packages/",
			"dotfiles/.pypirc",
		],
		"config_path_to_dest_map": {
			"Library/Application Support/Sublime Text 2/Packages/User/": "sublime_2",
			"Library/Application Support/Sublime Text 3/Packages/User/": "sublime_3",
			"Library/Preferences/IntelliJIdea2018.2/"                  : "intellijidea_2018.2",
			"Library/Preferences/PyCharm2018.2/"                       : "pycharm_2018.2",
			"Library/Preferences/CLion2018.2/"                         : "clion_2018.2",
			"Library/Preferences/PhpStorm2018.2"                       : "phpstorm_2018.2",
			".atom/"                                                   : "atom",
		},
		"plist_path_to_dest_map" : {
			"Library/Preferences/com.apple.Terminal.plist": "plist/com.apple.Terminal.plist",
		},
	}


def safe_create_config():
	"""
	Creates config file if it doesn't exist already.
	"""
	backup_config_path = get_config_path()
	if not os.path.exists(backup_config_path):
		print_bright_blue("Creating config file at {}".format(backup_config_path))
		backup_config = get_default_config()
		write_config(backup_config)


# TODO: Rethink these methods.
def add_to_config(section, path):
	"""
	Adds the path under the correct section in the config file.
	FIRST ARG: [dot, config, other]
	SECOND ARG: path, relative to home directory for dotfiles, absolute for configs
	"""
	full_path = home_prefix(path)
	if not os.path.exists(full_path):
		print_bright_red("ERR: {} doesn't exist.".format(full_path))
		sys.exit(1)

	if section == "dot":
		# Make sure dotfile starts with a period
		if path[0] != ".":
			print_bright_red("ERR: Not a dotfile.")
			sys.exit(1)

		if not os.path.isdir(full_path):
			section = "dotfiles"
			print(Fore.BLUE + Style.BRIGHT + "Adding {} to dotfile backup.".format(full_path) + Style.RESET_ALL)
		else:
			section = "dotfolders"
			if path[-1] != "/":
				full_path += "/"
				path += "/"
			print(Fore.BLUE + Style.BRIGHT + "Adding {} to dotfolder backup.".format(full_path) + Style.RESET_ALL)

	# TODO: Add config section once configs backup prefs are moved to the config file
	elif section == "config":
		print(Fore.RED + Style.BRIGHT + "ERR: Option not currently supported." + Style.RESET_ALL)
		sys.exit(1)
	elif section == "other":
		print(Fore.RED + Style.BRIGHT + "ERR: Option not currently supported." + Style.RESET_ALL)
		sys.exit(1)

	config = get_config()
	file_set = set(config[section])
	file_set.update([path])
	config[section] = list(file_set)
	write_config(config)


def rm_from_config(path):
	"""
	Removes the path from a section in the config file. Exits if the path doesn't exist.
	Path, relative to home directory for dotfiles, absolute for configs
	"""
	flag = False
	config = get_config()
	for section, items in config.items():
		if path in items:
			print(Fore.BLUE + Style.BRIGHT + "Removing {} from backup...".format(path) + Style.RESET_ALL)
			items.remove(path)
			config[section] = items
			flag = True

	if not flag:
		print(Fore.RED + Style.BRIGHT + "ERR: Not currently backing that path up..." + Style.RESET_ALL)
	else:
		write_config(config)


def show_config():
	"""
	Print the config. Colorize section titles and indent contents.
	"""
	print_section_header("SHALLOW BACKUP CONFIG", Fore.RED)
	config = get_config()
	for section, contents in config.items():
		# Hide gitignore config
		if section == "default-gitignore":
			continue
		# Print backup path on same line
		elif section == "backup_path":
			print(Fore.RED + Style.BRIGHT + "Backup Path: " + Style.RESET_ALL + contents)
		elif section == "config_path_to_dest_map":
			print(Fore.RED + Style.BRIGHT + "Configs to Backup Path Mapping: " + Style.RESET_ALL)
			for path, dest in contents.items():
				print("    {} -> {}".format(path, dest))
		elif section == "plist_path_to_dest_map":
			print(Fore.RED + Style.BRIGHT + "Plist to Backup Path Mapping: " + Style.RESET_ALL)
			for path, dest in contents.items():
				print("    {} -> {}".format(path, dest))
		# Print section header and then contents indented.
		else:
			print(Fore.RED + Style.BRIGHT + "\n{}: ".format(section.capitalize()) + Style.RESET_ALL)
			for item in contents:
				print("    {}".format(item))

	print()
