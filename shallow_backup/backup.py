import os
from shlex import quote
from colorama import Fore
import multiprocessing as mp
from pathlib import Path
from shutil import copyfile
from .utils import *
from .printing import *
from .compatibility import *
from .config import get_config


def backup_dotfiles(backup_dest_path, dry_run=False, home_path=os.path.expanduser("~"), skip=False):
	"""
	Create `dotfiles` dir and makes copies of dotfiles and dotfolders.
	Assumes that dotfiles are stored in the home directory.
	:param skip: Boolean flag to skip prompting for overwrite. Used for scripting.
	:param backup_dest_path: Destination path for dotfiles. Like, ~/shallow-backup/dotfiles. Used in tests.
	:param home_path: Path where dotfiles will be found. $HOME by default.
	:param dry_run: Flag for determining if debug info should be shown or copying should occur.
	"""
	print_section_header("DOTFILES", Fore.BLUE)
	if not dry_run:
		overwrite_dir_prompt_if_needed(backup_dest_path, skip)

	# get dotfolders and dotfiles
	config = get_config()["dotfiles"]

	# Aggregate pairs of [(Installed dotfile path, backup dest path)] in a list to be sorted into
	# dotfiles and dotfolders later
	dot_path_pairs = []
	for dotfile_path_from_config, options in config.items():
		# Evaluate condition, if specified. Skip if the command doesn't return true.
		condition_success = evaluate_condition(condition=options["backup_condition"],
											   backup_or_reinstall="backup",
											   dotfile_path=dotfile_path_from_config)
		if not condition_success:
			continue

		# If a file path in the config starts with /, it's a full path like /etc/ssh/
		if dotfile_path_from_config.startswith("/"):
			installed_dotfile_path = dotfile_path_from_config
			installed_dotfile_path = quote(':' + installed_dotfile_path[1:])
			backup_dotfile_path = quote(os.path.join(backup_dest_path, installed_dotfile_path))
			dot_path_pairs.append((dotfile_path_from_config, backup_dotfile_path))

		else:  # Dotfile living in $HOME
			installed_dotfile_path = quote(os.path.join(home_path, dotfile_path_from_config))
			backup_dotfile_path = quote(os.path.join(backup_dest_path, dotfile_path_from_config))
			dot_path_pairs.append((installed_dotfile_path, backup_dotfile_path))

	# Separate dotfiles and dotfolders
	dotfolders_mp_in = []
	dotfiles_mp_in = []
	for path_pair in dot_path_pairs:
		installed_path = path_pair[0]
		if os.path.isdir(installed_path):
			dotfolders_mp_in.append(path_pair)
		else:
			dotfiles_mp_in.append(path_pair)

	# Print source -> dest and skip the copying step
	if dry_run:
		print_yellow_bold("Dotfiles:")
		for source, dest in dotfiles_mp_in:
			print_dry_run_copy_info(source, dest)

		print_yellow_bold("\nDotfolders:")
		for source, dest in dotfolders_mp_in:
			print_dry_run_copy_info(source, dest)

		return

	# Fix https://github.com/alichtman/shallow-backup/issues/230
	for dest_path in [path_pair[1] for path_pair in dotfiles_mp_in + dotfolders_mp_in]:
		print(f"Creating: {os.path.split(dest_path)[0]}")
		safe_mkdir(os.path.split(dest_path)[0])

	with mp.Pool(mp.cpu_count()):
		print_blue_bold("Backing up dotfolders...")
		for x in dotfolders_mp_in:
			p = mp.Process(target=copy_dir_if_valid, args=(x[0], x[1],))
			p.start()
			p.join()

		print_blue_bold("Backing up dotfiles...")
		for x in dotfiles_mp_in:
			p = mp.Process(target=copyfile, args=(x[0], x[1],))
			p.start()
			p.join()


def backup_configs(backup_path, dry_run: bool = False, skip=False):
	"""
	Creates `configs` directory and places config backups there.
	Configs are application settings, generally. .plist files count.
	In the config file, the value of the configs dictionary is the dest
	path relative to the configs/ directory.
	"""
	print_section_header("CONFIGS", Fore.BLUE)
	# Don't clear any directories if this is a dry run
	if not dry_run:
		overwrite_dir_prompt_if_needed(backup_path, skip)
	config = get_config()

	print_blue_bold("Backing up configs...")

	# backup config files + dirs in backup_path/<target>/
	for config_path, target in config["config_mapping"].items():
		dest = os.path.join(backup_path, target)

		if dry_run:
			print_dry_run_copy_info(config_path, dest)
			continue

		quoted_dest = quote(dest)
		if os.path.isdir(config_path):
			copytree(config_path, quoted_dest, symlinks=True)
		elif os.path.isfile(config_path):
			parent_dir = Path(dest).parent
			safe_mkdir(parent_dir)
			copyfile(config_path, quoted_dest)


def backup_packages(backup_path, dry_run: bool = False, skip=False):
	"""
	Creates `packages` directory and places install list text files there.
	"""
	def run_cmd_if_no_dry_run(command, dest, dry_run) -> int:
		if dry_run:
			print_dry_run_copy_info(f"$ {command}", dest)
			# Return -1 for any processes depending on chained successful commands (npm)
			return -1
		else:
			return run_cmd_write_stdout(command, dest)

	print_section_header("PACKAGES", Fore.BLUE)
	if not dry_run:
		overwrite_dir_prompt_if_needed(backup_path, skip)

	for mgr in ["brew", "brew cask"]:
		# deal with package managers that have spaces in them.
		print_pkg_mgr_backup(mgr)
		command = f"{mgr} list"
		dest = f"{backup_path}/{mgr.replace(' ', '-')}_list.txt"
		run_cmd_if_no_dry_run(command, dest, dry_run)

	# ruby
	print_pkg_mgr_backup("gem")
	command = r"gem list | tail -n+1 | sed -E 's/\((default: )?(.*)\)/--version \2/'"
	dest = f"{backup_path}/gem_list.txt"
	run_cmd_if_no_dry_run(command, dest, dry_run)

	# cargo
	print_pkg_mgr_backup("cargo")
	command = r"cargo install --list | grep '^\w.*:$' | sed -E 's/ v(.*):$/ --version \1/'"
	dest = f"{backup_path}/cargo_list.txt"
	run_cmd_if_no_dry_run(command, dest, dry_run)

	# pip
	print_pkg_mgr_backup("pip")
	command = "pip list --format=freeze"
	dest = f"{backup_path}/pip_list.txt"
	run_cmd_if_no_dry_run(command, dest, dry_run)

	# pip3
	print_pkg_mgr_backup("pip3")
	command = "pip3 list --format=freeze"
	dest = f"{backup_path}/pip3_list.txt"
	run_cmd_if_no_dry_run(command, dest, dry_run)

	# npm
	print_pkg_mgr_backup("npm")
	command = "npm ls --global --parseable=true --depth=0"
	temp_file_path = f"{backup_path}/npm_temp_list.txt"
	# If command is successful, go to the next parsing step.
	npm_backup_cmd_success = run_cmd_if_no_dry_run(command, temp_file_path, dry_run) == 0
	if npm_backup_cmd_success:
		npm_dest_file = f"{backup_path}/npm_list.txt"
		# Parse npm output
		with open(temp_file_path, mode="r+") as temp_file:
			# Skip first line of file
			temp_file.seek(1)
			with open(npm_dest_file, mode="w+") as dest:
				for line in temp_file:
					dest.write(line.split("/")[-1])
		os.remove(temp_file_path)

	# atom package manager
	print_pkg_mgr_backup("Atom")
	command = "apm list --installed --bare"
	dest = f"{backup_path}/apm_list.txt"
	run_cmd_if_no_dry_run(command, dest, dry_run)

	# vscode extensions
	print_pkg_mgr_backup("VSCode")
	command = "code --list-extensions --show-versions"
	dest = f"{backup_path}/vscode_list.txt"
	run_cmd_if_no_dry_run(command, dest, dry_run)

	# macports
	print_pkg_mgr_backup("macports")
	command = "port installed requested"
	dest = f"{backup_path}/macports_list.txt"
	run_cmd_if_no_dry_run(command, dest, dry_run)

	# system installs
	print_pkg_mgr_backup("System Applications")
	applications_path = get_applications_dir()
	command = "ls {}".format(applications_path)
	dest = f"{backup_path}/system_apps_list.txt"
	run_cmd_if_no_dry_run(command, dest, dry_run)


def backup_fonts(backup_path: str, dry_run: bool = False, skip: bool = False):
	"""Copies all .ttf and .otf files in the  to backup/fonts/
	"""
	print_section_header("FONTS", Fore.BLUE)
	if not dry_run:
		overwrite_dir_prompt_if_needed(backup_path, skip)
	print_blue("Copying '.otf' and '.ttf' fonts...")
	fonts_path = get_fonts_dir()
	if os.path.isdir(fonts_path):
		fonts = [quote(os.path.join(fonts_path, font)) for font in os.listdir(fonts_path) if
				 font.endswith(".otf") or font.endswith(".ttf")]

		for font in fonts:
			dest = os.path.join(backup_path, font.split("/")[-1])
			if os.path.exists(font):
				if dry_run:
					print_dry_run_copy_info(font, dest)
				else:
					copyfile(font, dest)
	else:
		print_red('Skipping fonts backup. No fonts directory found.')


def backup_all(dotfiles_path, packages_path, fonts_path, configs_path, dry_run=False, skip=False):
	"""Complete backup procedure."""
	backup_dotfiles(dotfiles_path, dry_run=dry_run, skip=skip)
	backup_packages(packages_path, dry_run=dry_run, skip=skip)
	backup_fonts(fonts_path, dry_run=dry_run, skip=skip)
	backup_configs(configs_path, dry_run=dry_run, skip=skip)
