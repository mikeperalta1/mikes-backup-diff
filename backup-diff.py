#!/usr/bin/env python3

"""

Mike's Backup Diff

A simple script to help compare changes between a backup destination directory, and its source

Copyright 2019 Mike Peralta; All rights reserved

Released under the GNU GENERAL PUBLIC LICENSE v3 (See LICENSE file for more)

"""


#
import datetime
import functools
import humanfriendly
import os
import re
import subprocess
import sys


#
class BackupDiff:
	
	def __init__(self):
		
		self.__source_path = None
		self.__source_ssh_host = None
		self.__source_ssh_user = None
		
		self.__backup_path = None
		self.__backup_ssh_host = None
		self.__backup_ssh_user = None
		
		self.__ssh_key = None
		
		self.__source_path_items = None
		self.__backup_path_items = None
		
		self.__difference_entries = None
		self.__do_clean_difference_entries = True
		
		self.__force_rsync = False
		
	def run(self):
		
		self.consume_arguments()
		
		self.calculate_difference_entries()
		
		if self.__do_clean_difference_entries:
			self.clean_difference_entries()
		
		self.print_report()
	
	@staticmethod
	def current_time():
		
		now = datetime.datetime.now()
		now_s = now.strftime("%b-%d-%Y %I:%M%p")
		return str(now_s)
	
	def log(self, s, o=None):
		
		to_log = self.make_log_prefix() + str(s)
		if o is not None:
			to_log += " " + str(o)
		
		print(to_log)
	
	def make_log_prefix(self):
		
		now = self.current_time()
		
		prefix = "[" + now + "][Mike's Backup Diff] "
		
		return prefix
	
	def consume_arguments(self):
		
		i = 0
		while i + 1 < len(sys.argv):
			
			i += 1
			
			arg = sys.argv[i]
			# print("I:", i, "; arg:", arg)
			
			if arg == "--source-path":
				i, one_path = self.consume_argument_companion(i)
				self.__source_path = os.path.abspath(one_path)
				self.log("Found source path argument:", self.__source_path)
			
			elif arg == "--source-remote-host":
				i, host = self.consume_argument_companion(i)
				self.__source_ssh_host = host
				self.log("Will use source remote host: " + str(self.__source_ssh_host))
			
			elif arg == "--source-remote-user":
				i, user = self.consume_argument_companion(i)
				self.__source_ssh_user = user
				self.log("Will use source remote user: " + str(self.__source_ssh_user))
			
			elif arg == "--backup-path":
				i, one_path = self.consume_argument_companion(i)
				self.__backup_path = os.path.abspath(one_path)
				self.log("Found backup destination path argument:", self.__backup_path)
			
			elif arg == "--backup-remote-host":
				i, host = self.consume_argument_companion(i)
				self.__backup_ssh_host = host
				self.log("Will use backup remote host: " + str(self.__backup_ssh_host))
			
			elif arg == "--backup-remote-user":
				i, user = self.consume_argument_companion(i)
				self.__backup_ssh_user = user
				self.log("Will use backup remote user: " + str(self.__backup_ssh_user))
			
			elif arg == "--ssh-key":
				i, key = self.consume_argument_companion(i)
				self.__ssh_key = key
				self.log("Will use ssh key: " + str(self.__ssh_key))
			
			elif arg == "--use-rsync" or arg == "--rsync":
				self.__force_rsync = True
				self.log("Forcing comparison with rsync tool")
			
			elif arg == "--no-clean":
				self.__do_clean_difference_entries = False
				self.log("Won't clean Difference entries")
			
			else:
				self.log("The heck are you doing?")
				self.log("Unsupported argument: " + arg)
				self.log("i is: " + str(i))
				raise Exception("THE HECK")
	
	@staticmethod
	def consume_argument_companion(arg_index):
		
		companion_index = arg_index + 1
		if companion_index >= len(sys.argv):
			raise Exception("Expected argument after", sys.argv[arg_index])
		
		return_index = companion_index
		
		return return_index, sys.argv[companion_index]
	
	def calculate_comparison_items(self):
		
		self.consume_source_path()
		self.consume_backup_path()
	
	def consume_source_path(self):
	
		if self.__source_path is None:
			raise Exception("Please provide a source path")
		if not os.path.isdir(self.__source_path):
			raise Exception("Source path isn't a valid directory")
		
		self.log("Consuming source path: " + str(self.__source_path))
		
		source_path_items = self.consume_dir(self.__source_path)
		source_path_items = self.strip_root_dir(self.__source_path, source_path_items)
		
		self.log("Done consuming source path items: " + str(len(source_path_items)))
		
		self.__source_path_items = source_path_items
	
	def should_use_rsync(self):
		
		if self.__force_rsync:
			return True
		
		if self.__source_ssh_host or self.__source_ssh_user:
			return True
		
		if self.__backup_ssh_host or self.__backup_ssh_user:
			return True
		
		if self.__ssh_key:
			return True
		
		return False
	
	def consume_backup_path(self):
		
		if self.__backup_path is None:
			raise Exception("Please provide a backup destination path")
		if not os.path.isdir(self.__backup_path):
			raise Exception("Backup destination path isn't a valid directory")
		
		self.log("Consuming backup path: " + str(self.__backup_path))
		
		backup_path_items = self.consume_dir(self.__backup_path)
		backup_path_items = self.strip_root_dir(self.__backup_path, backup_path_items)
		
		self.log("Done consuming backup path items: " + str(len(backup_path_items)))
		
		self.__backup_path_items = backup_path_items
	
	def consume_dir(self, dir_path):
		
		#
		paths = set()
		
		#
		self.log("")
		for root, dirs, filenames in os.walk(dir_path):
			
			paths.add(root)
			
			for d in dirs:
				path = os.path.join(root, d)
				paths.add(path)
				# print(path)
			
			for f in filenames:
				path = os.path.join(root, f)
				paths.add(path)
				# print(path)
			
			self.print_progress_message("Consuming paths ... " + str(len(paths)))
		
		return paths
	
	def calculate_difference_entries(self):
	
		if self.should_use_rsync():
			self.calculate_difference_entries_with_rsync()
		else:
			self.calculate_difference_entries_directly()
	
	def calculate_difference_entries_with_rsync(self):
		
		entries = []
		
		stdout_lines, stderr_lines, return_code = self.execute_rsync()
		
		# print("STDOUT LINES:")
		# print(stdout_lines)
		
		# print("STDERR LINES:")
		# print(stderr_lines)
		
		#
		self.log("Calculating difference entries ...")
		
		# Regex patterns
		pattern_regular = re.compile("""^(?P<line>(?P<flags>[^\s]{11})(?P<item>.*))$""")
		pattern_message = re.compile("""^(?P<line>\*(?P<message>[\w]+)(?P<item>.*))$""")
		
		# Iterate over each stdout line
		for line in stdout_lines:
			
			# Try to match regular expressions
			match_regular = pattern_regular.match(line)
			match_message = pattern_message.match(line)
			
			# Regular line (Flags and Path)
			if match_regular:
				
				flags = match_regular.group("flags")
				change_type_character = flags[0]
				item_type = flags[1]
				
				# Determine which attributes are different
				attributes_part = flags[2:]
				different_checksum = "c" in attributes_part
				different_size = "s" in attributes_part
				different_modification_time = "t" in attributes_part
				different_permissions = "p" in attributes_part
				different_owner = "o" in attributes_part
				different_group = "g" in attributes_part
				different_acl = "a" in attributes_part
				different_extended_attributes = "x" in attributes_part
				#
				different_any_attribute = (
					different_checksum
					or different_size
					or different_modification_time
					or different_permissions
					or different_owner
					or different_group
					or different_acl
					or different_extended_attributes
				)
				
				item = match_regular.group("item").strip()
				
				entry = DifferenceEntry(item)
				
				# File folder, whatever
				if item_type == "d":
					entry.set_is_dir()
				elif item_type == "f":
					entry.set_is_file()
				
				# Different attributes
				# (before 'missing' stuff, because attribute syncs show up as xfers)
				if different_checksum:
					entry.set_is_different_checksum()
				elif different_size:
					entry.set_is_different_sizes()
				elif different_modification_time:
					entry.set_is_different_modification_times()
				elif different_permissions:
					entry.set_is_different_permissions()
				elif different_owner:
					entry.set_is_different_owner()
				elif different_group:
					entry.set_is_different_group()
				elif different_acl:
					entry.set_is_different_acl()
				elif different_extended_attributes:
					entry.set_is_different_extended_attributes()
				elif different_any_attribute:
					entry.set_is_different_attributes()
				
				# Missing from backup
				elif change_type_character == "<":
					entry.set_is_missing_from_backup()
				# Missing from ... backup? (confusing symbolstuffs)
				elif change_type_character == ">":
					entry.set_is_missing_from_backup()
				
				# Local change is occurring
				elif change_type_character == "c":
					entry.set_is_missing_from_backup()
				
				# Item is a hard link
				elif change_type_character == "h":
					entry.set_is_unknown("Rsync says this is a hard link")
				
				# "no change / transfer (could still be changing attributes)"
				elif change_type_character == ".":
					entry.set_is_unknown("Rsync says no change, but could be changing attributes")
				
				#
				entries.append(entry)
			
			# Message line
			elif match_message:
			
				message = match_message.group("message").strip()
				item = match_message.group("item").strip()
				
				entry = DifferenceEntry(item)
				
				if message == "deleting":
					entry.set_is_missing_from_source()
					entry.set_is_dir(item[-1] == "/")
					entry.set_is_file(not item[-1] == "/")
				
				else:
					self.log("IS UNKNOWN MESSAGE:" + message)
					entry.set_is_unknown("Unhandled message: " + message)
				
				entries.append(entry)
			
			# Unsupported type of line
			else:
				
				#
				self.log("Don't know how to parse this line: " + line)
			
		self.log("Finished calculating difference entries")
		
		self.__difference_entries = entries
	
	def execute_rsync(self):
		
		#
		args = list()
		
		# Rsync
		args.append("rsync")
		
		# Dry run!!
		args.append("--dry-run")
		
		# Produces the main output we'll parse
		args.append("--itemize-changes")
		
		# Rsh command
		rsh_command = self.make_rsync_rsh_argument(self.__ssh_key)
		if rsh_command:
			args.append(rsh_command)
		
		# Main sync flags
		args.append("--archive")
		args.append("--delete")
		
		# Source path
		args.append(self.make_rsync_path(self.__source_ssh_host, self.__source_ssh_user, self.__source_path))
		
		# Backup path
		args.append(self.make_rsync_path(self.__backup_ssh_host, self.__backup_ssh_user, self.__backup_path))
		
		#
		self.log("Executing rsync")
		# self.log("Executing rsync with the following arguments:")
		# self.log(str(args))
		# self.log(" ".join(args))
		
		# Start the subprocess
		process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		
		# Live output of stdout
		print()
		stdout_lines = []
		for line in iter(process.stdout.readline, b''):
			line = line.decode().strip()
			stdout_lines.append(line)
			# print(line)
			self.print_progress_message("Captured " + str(len(stdout_lines)) + " lines from Rsync")
		
		# Grab all the stderr lines
		stderr_lines = []
		for line in iter(process.stderr.readline, b''):
			line = line.decode().strip()
			stderr_lines.append(line)
		
		# Make sure it's completely finished
		process.communicate()
		
		self.log("Rsync has finished executing")
		
		# Accept Success (0), and Partial Transfer Codes (23 and 24)
		if process.returncode not in [0, 23, 24]:
			raise Exception("Failed to execute Rsync; Exited with code " + str(process.returncode))
		
		return stdout_lines, stderr_lines, process.returncode
	
	@staticmethod
	def make_rsync_path(ssh_host, ssh_user, path):
		
		rsync_path = ""
		
		if (not ssh_host) and ssh_user:
			raise Exception("ssh_user provided (" + str(ssh_user) + ") without ssh_host")
		
		if ssh_user:
			rsync_path += ssh_user + "@"
		
		if ssh_host:
			rsync_path += ssh_host + ":" + path
		else:
			rsync_path += path
		
		# Absolute path doesn't have trailing slash, which works well for rsync here
		rsync_path += "/"
		
		return rsync_path
	
	@staticmethod
	def make_rsync_rsh_argument(ssh_key):
	
		if not ssh_key:
			return None
		
		if not os.path.isfile(ssh_key):
			raise Exception("SSH key does not exist: " + str(ssh_key))
		
		return "--rsh=ssh -i " + ssh_key
	
	def calculate_difference_entries_directly(self):
		
		self.calculate_comparison_items()
		
		entries = []
		
		# Compare everything in the source path
		self.log("")
		i = 1
		for item in self.__source_path_items:
			
			self.print_progress_message(
				"Looking for differences from source to backup ... "
				+ str(i) + " of " + str(len(self.__source_path_items))
			)
			
			entry = self.calculate_difference_entry(item)
			if entry:
				entries.append(entry)
			
			i += 1
		
		# Compare only things in the backup path that weren't
		# in the source
		self.log("")
		i = 1
		backup_items_not_in_source = self.__backup_path_items - self.__source_path_items
		for item in backup_items_not_in_source:
			
			self.print_progress_message(
				"Looking for differences from backup to source ... "
				+ str(i) + " of " + str(len(backup_items_not_in_source))
			)
			
			entry = self.calculate_difference_entry(item)
			if entry:
				entries.append(entry)
			
			i += 1
		
		self.__difference_entries = entries
	
	def clean_difference_entries(self, entries: list=None):
		
		if entries is None:
			entries = self.__difference_entries
		
		self.log("Cleaning " + str(len(entries)) + " difference entries")
		
		# Build a temp list of all known difference entries
		temp_entries = []
		for entry in entries:
			temp_entries.append(entry)
		# print("Temp entries count:", len(temp_entries))
		
		# Loop through entries, attempting to clean for one at a time,
		# until no cleaning has been done
		print()
		clean_iterations = 0
		while True:
			
			clean_iterations += 1
			
			most_shallow_entry = None
			
			# Locate the most shallow entry
			for entry in temp_entries:
				
				if entry.get_is_missing_from_source() or entry.get_is_missing_from_backup():
					
					# print("Found entry of type 'missing'")
					# print(entry)
					
					item = entry.get_item()
					if entry.get_is_dir():
						# print("Found entry dir:", item)
						if most_shallow_entry is None or len(item) < len(most_shallow_entry.get_item()):
							most_shallow_entry = entry
							# print("Found shallow entry:")
							# print(entry)
			
			# Finish if we haven't found anything
			if not most_shallow_entry:
				self.print_progress_message(
					"Cleaning difference entries; "
					+ str(clean_iterations) + " iterations; "
					+ str(len(temp_entries)) + " total"
				)
				break
			
			# Remove this entry from the temp list, and clean with it as root
			temp_entries.remove(most_shallow_entry)
			self.clean_child_difference_entries(temp_entries, most_shallow_entry)
			self.clean_child_difference_entries(entries, most_shallow_entry)
			
			self.log(
				"Cleaning difference entries; "
				+ str(clean_iterations) + " iterations; "
				+ str(len(temp_entries)) + " total"
			)
			
		self.__difference_entries = entries
	
	def clean_child_difference_entries(self, entries: list, root_entry):
		
		if entries is None:
			entries = self.__difference_entries
		
		# print("Enter clean_child_difference_entries")
		# print(root_entry)
		
		root_entry_item = root_entry.get_item()
		# print("Cleaning child entries for root entry")
		# print(root_entry)
		# print()
		# print()
		
		entries_to_delete = []
		
		# Check every other entry as a possible child of the root
		print("")
		child_iteration = 0
		for child_entry in entries:
			
			child_iteration += 1
			
			self.print_progress_message("Looking for child entry to clean " + str(child_iteration))
			
			if child_entry != root_entry:
				
				child_entry_item = child_entry.get_item()
				
				# Entry must be longer than the shallow entry
				if len(child_entry_item) >= len(root_entry_item):
					
					# Entry must begin with the shallow entry (ie shallow must be a root path of deeper)
					if child_entry_item.find(root_entry_item) == 0:
						
						# We can purge the deeper entry
						entries_to_delete.append(child_entry)
						# print("Deleting unneeded child entry:")
						# print("> Root:", root_entry_item)
						# print("> Child:", child_entry_item)
						# print()
						# print()
		
		# Handle entries to delete
		print("")
		delete_iteration = 0
		for entry in entries_to_delete:
			
			delete_iteration += 1
			
			self.print_progress_message(
				"Deleting child entry "
				+ str(delete_iteration) + " / " + str(len(entries_to_delete))
			)
			
			entries.remove(entry)
		
		return len(entries_to_delete) > 0
	
	def strip_root_dir(self, root_dir, paths: set):
		
		if isinstance(paths, str):
			return self.strip_root_dir_from_string(root_dir, paths)
		
		paths_stripped = set()
		
		for path in paths:
			
			paths_stripped.add(self.strip_root_dir_from_string(root_dir, path))
		
		return paths_stripped
	
	@staticmethod
	def strip_root_dir_from_string(root_dir, path):
		
		#
		pos = path.find(root_dir)
		if pos == -1:
			raise Exception("Couldn't find root dir in path", str(root_dir), str(path))
		
		#
		if pos > 0:
			raise Exception("Root dir wasn't found at the beginning of path", str(root_dir), str(path))
		
		#
		path_stripped = path[len(root_dir) + 1:]
		# print(path, "===>", path_stripped)
		
		return path_stripped
	
	#
	def calculate_difference_entry(self, comparison_item):
		
		entry = DifferenceEntry(comparison_item)
		
		path_source = os.path.join(self.__source_path, comparison_item)
		path_source_exists = False
		path_source_is_dir = None
		path_source_mtime = None
		try:
			path_source_is_dir = os.path.isdir(path_source)
			path_source_mtime = int(os.path.getmtime(path_source))
			path_source_exists = True
		except FileNotFoundError:
			pass
		
		path_backup = os.path.join(self.__backup_path, comparison_item)
		path_backup_exists = False
		path_backup_is_dir = None
		path_backup_mtime = None
		try:
			path_backup_is_dir = os.path.isdir(path_backup)
			path_backup_mtime = int(os.path.getmtime(path_backup))
			path_backup_exists = True
		except FileNotFoundError:
			pass
		
		# In source but not backup
		if path_source_exists and not path_backup_exists:
			if path_source_is_dir is not None:
				entry.set_is_dir(path_source_is_dir)
			entry.set_is_missing_from_backup()
			
		# In backup but not source
		elif path_backup_exists and not path_source_exists:
			entry.set_is_dir(path_backup_is_dir)
			entry.set_is_missing_from_source()
		
		# In neither
		# Possible if a bad symlink is present
		elif not path_source_exists and not path_backup_exists:
			entry.set_is_missing_from_both()
		
		# Type mismatch
		elif os.path.isdir(path_source) and os.path.isfile(path_backup):
			entry.set_is_type_mismatch("Source is a directory, but backup is a file")
		elif os.path.isfile(path_source) and os.path.isdir(path_backup):
			entry.set_is_type_mismatch("Source is a file, but backup is a directory")
		
		# Compare props
		else:
			
			# print("Received item:", comparison_item)
			# print("Comparing props with:", path_source)
			# print("Comparing props with:", path_backup)
			
			path_source_size = os.path.getsize(path_source)
			path_backup_size = os.path.getsize(path_backup)
			
			entry.set_is_dir(os.path.isdir(path_source))
			
			# Different file sizes
			if os.path.isfile(path_source) \
				and os.path.isfile(path_backup) \
				and (path_source_size != path_backup_size):
				entry.set_is_different_sizes(path_source_size, path_backup_size)
			
			# Source modification time is newer
			elif path_source_mtime > path_backup_mtime:
				entry.set_source_is_newer(path_source_mtime, path_backup_mtime)
			# Backup modification time is newer
			elif path_backup_mtime > path_source_mtime:
				entry.set_backup_is_newer(path_source_mtime, path_backup_mtime)
			
			# No difference
			else:
				entry = None
		
		return entry
	
	@staticmethod
	def sort_difference_entries(entries):
		
		entries.sort(
			key=functools.cmp_to_key(
				lambda entry_a, entry_b: BackupDiff.sort_difference_entries_key_callback(entry_a, entry_b)
			)
		)
	
	@staticmethod
	def sort_difference_entries_key_callback(entry_a, entry_b):
		
		if entry_a.get_is_dir() and not entry_b.get_is_dir():
			return -1
		if not entry_a.get_is_dir() and entry_b.get_is_dir():
			return 1
		
		item_a = entry_a.get_item()
		item_b = entry_b.get_item()
		
		if item_a > item_b:
			return -1
		elif item_b > item_b:
			return 1
		
		return 0
	
	def generate_report(self):
		
		# Start report structure
		report = {
			"missing_from_source": {
				"label": "Items missing from the source",
				"entries": []
			},
			"missing_from_backup": {
				"label": "Items missing from the backup",
				"entries": []
			},
			"missing_from_both": {
				"label": "Items missing from both source and backup (bad link?)",
				"entries": []
			},
			"newer_source": {
				"label": "Items newer in the source",
				"entries": []
			},
			"newer_backup": {
				"label": "Items newer in the backup",
				"entries": []
			},
			"type_mismatch": {
				"label": "Directory/File type mismatch",
				"entries": []
			},
			"size_difference": {
				"label": "Items with different file sizes",
				"entries": []
			},
			"different_attributes": {
				"label": "Items with different attributes",
				"entries": []
			},
			"unknown": {
				"label": "Differences of an unknown type",
				"entries": []
			}
		}
		
		# Find entries missing from source
		for entry in self.__difference_entries:
			if entry.get_is_missing_from_source():
				report["missing_from_source"]["entries"].append(entry)
		
		# Find entries missing from backup
		for entry in self.__difference_entries:
			if entry.get_is_missing_from_backup():
				report["missing_from_backup"]["entries"].append(entry)
		
		# Find entries missing from both
		for entry in self.__difference_entries:
			if entry.get_is_missing_from_both():
				report["missing_from_both"]["entries"].append(entry)
		
		# Find directory/file type mismatches
		for entry in self.__difference_entries:
			if entry.get_is_type_mismatch():
				report["type_mismatch"]["entries"].append(entry)
				
		# Find newer in source
		for entry in self.__difference_entries:
			if entry.get_source_is_newer():
				report["newer_source"]["entries"].append(entry)
				
		# Find newer in backup
		for entry in self.__difference_entries:
			if entry.get_backup_is_newer():
				report["newer_backup"]["entries"].append(entry)
		
		# Different file sizes
		for entry in self.__difference_entries:
			if entry.get_is_different_sizes():
				report["size_difference"]["entries"].append(entry)
				
		# Different attributes
		for entry in self.__difference_entries:
			if entry.get_is_different_attributes():
				report["different_attributes"]["entries"].append(entry)
		
		# Differences of an unknown nature
		for entry in self.__difference_entries:
			if entry.get_is_unknown():
				report["unknown"]["entries"].append(entry)
		
		# Sort all entries
		for section_key in report:
			self.sort_difference_entries(report[section_key]["entries"])
		
		return report
	
	def print_progress_message(self, s):
		
		sys.stdout.write("\033[F")  # back to previous line
		sys.stdout.write("\033[K")  # clear line
		
		to_print = self.make_log_prefix() + s
		
		print(to_print)
	
	@staticmethod
	def print_report_heading(s, hooded: bool=False):
		
		star_count = 5
		stars = "*" * star_count
		
		title = stars + " " + s + " " + stars
		
		print("")
		if hooded:
			print("*" * len(title))
		print(title)
		
	def print_report(self):
		
		report = self.generate_report()
		section_order = [
			"type_mismatch",
			"missing_from_both",
			"missing_from_source", "newer_source",
			"missing_from_backup", "newer_backup",
			"size_difference",
			"different_attributes",
			"unknown"
		]
		
		#
		print()
		self.print_report_heading("Mike's Backup Diff Report", True)
		print("Source:", self.__source_path)
		print("Backup:", self.__backup_path)
		
		# Print each non-empty report section
		found_anything = False
		for section_key in section_order:
			if len(report[section_key]["entries"]):
				found_anything = True
				print("")
				self.print_report_heading(report[section_key]["label"])
				for entry in report[section_key]["entries"]:
					
					if entry.get_is_dir():
						prefix = "Directory: "
					elif entry.get_is_file():
						prefix = "File: "
					else:
						prefix = ""
					
					message = entry.get_message()
					if message:
						suffix = " (" + message + ")"
					else:
						suffix = ""
					
					print(prefix + entry.get_item() + suffix)
		
		# Lil debebuggin'
		for section_key in report:
			if section_key not in section_order:
				raise Exception("Report key " + section_key + " wasn't found in the section_order ... whoopsies")
		
		if not found_anything:
			print()
			print("Everything seems to match !")


#
class DifferenceEntry:
	
	def __init__(self, item):
		
		self.__item = None
		self.__item_is_file = None
		self.__item_is_dir = None
		self.__type = None
		self.__message = None
		
		self.CONST_TYPE_TYPE_MISMATCH = "type_mismatch"
		self.CONST_TYPE_MISSING_IN_SOURCE = "missing_in_source"
		self.CONST_TYPE_MISSING_IN_BACKUP = "missing_in_backup"
		self.CONST_TYPE_MISSING_IN_BOTH = "missing_in_both"
		self.CONST_TYPE_SOURCE_IS_NEWER = "source_is_newer"
		self.CONST_TYPE_BACKUP_IS_NEWER = "backup_is_newer"
		self.CONST_TYPE_DIFFERENT_SIZES = "different_sizes"
		self.CONST_TYPE_DIFFERENT_ATTRIBUTES = "different_attributes"
		self.CONST_TYPE_UNKNOWN = "unknown"
		
		self.set_is_unknown("DEFAULT MESSAGE")
		
		if item:
			self.set_item(item)
	
	def __str__(self):
	
		s = ""
		
		s += "--- DifferenceEntry ---"
		s += "\nItem: " + str(self.__item)
		s += "\nType: " + self.__type
		s += "\nMessage: " + str(self.__message)
		
		return s
	
	def set_item(self, i):
		
		self.__item = i
	
	def get_item(self):
		
		return self.__item
	
	def set_message(self, m):
		self.__message = m
	
	def get_message(self):
		return self.__message
	
	def set_is_dir(self, is_dir: bool=True):
		
		if is_dir:
			self.__item_is_dir = True
			self.__item_is_file = False
		else:
			self.__item_is_dir = False
			self.__item_is_file = True
	
	def get_is_dir(self):
		
		return self.__item_is_dir
	
	def set_is_file(self, is_file: bool=True):
		
		self.set_is_dir(not is_file)
	
	def get_is_file(self):
		
		return self.__item_is_file
	
	def set_is_type_mismatch(self, message):
		
		self.__type = self.CONST_TYPE_TYPE_MISMATCH
		self.__message = message
	
	def get_is_type_mismatch(self):
		return self.__type == self.CONST_TYPE_TYPE_MISMATCH
	
	def set_is_missing_from_source(self):
		
		self.__type = self.CONST_TYPE_MISSING_IN_SOURCE
		self.__message = None
	
	def get_is_missing_from_source(self):
		return self.__type == self.CONST_TYPE_MISSING_IN_SOURCE
	
	def set_is_missing_from_backup(self):
		self.__type = self.CONST_TYPE_MISSING_IN_BACKUP
		self.__message = None
	
	def get_is_missing_from_backup(self):
		return self.__type == self.CONST_TYPE_MISSING_IN_BACKUP
	
	def set_is_missing_from_both(self):
		self.__type = self.CONST_TYPE_MISSING_IN_BOTH
		self.__message = "Item isn't in source or backup (bad link?)"
	
	def get_is_missing_from_both(self):
		return self.__type == self.CONST_TYPE_MISSING_IN_BOTH
	
	def set_source_is_newer(self, stamp_source, stamp_backup):
		time_difference = self.friendly_time_difference(stamp_source, stamp_backup)
		self.__type = self.CONST_TYPE_SOURCE_IS_NEWER
		self.__message = "Item has been modified more recently in source (" + str(stamp_source) + ")" \
			+ " than in backup (" + str(stamp_backup) + ")" \
			+ "; Difference is " + str(time_difference)
	
	def get_source_is_newer(self):
		return self.__type == self.CONST_TYPE_SOURCE_IS_NEWER
	
	def set_backup_is_newer(self, stamp_source, stamp_backup):
		time_difference = self.friendly_time_difference(stamp_source, stamp_backup)
		self.__type = self.CONST_TYPE_BACKUP_IS_NEWER
		self.__message = "Item has been modified more recently in backup (" + str(stamp_backup) + ")" \
			+ " than in source (" + str(stamp_source) + ")" \
			+ "; Difference is " + str(time_difference)
	
	def get_backup_is_newer(self):
		return self.__type == self.CONST_TYPE_BACKUP_IS_NEWER
	
	def set_is_different_sizes(self, source_item_size=None, backup_item_size=None):
		self.__type = self.CONST_TYPE_DIFFERENT_SIZES
		
		if source_item_size and backup_item_size:
			self.__message = \
				"Source has a file size of " + str(source_item_size) \
				+ ", but backup has a file size of " + str(backup_item_size)
		else:
			self.__message = None
	
	def get_is_different_sizes(self):
		return self.__type == self.CONST_TYPE_DIFFERENT_SIZES
	
	def set_is_different_attributes(self, message=None):
		self.__type = self.CONST_TYPE_DIFFERENT_ATTRIBUTES
		self.__message = message
	
	def get_is_different_attributes(self):
		return self.__type == self.CONST_TYPE_DIFFERENT_ATTRIBUTES
	
	def set_is_different_checksum(self):
		self.set_is_different_attributes("Different checksums")
	
	def set_is_different_modification_times(self):
		self.set_is_different_attributes("Different modification times")
	
	def set_is_different_permissions(self):
		self.set_is_different_attributes("Different permissions")
	
	def set_is_different_owner(self):
		self.set_is_different_attributes("Different owners")
	
	def set_is_different_group(self):
		self.set_is_different_attributes("Different groups")
	
	def set_is_different_acl(self):
		self.set_is_different_attributes("Different ACLs")
	
	def set_is_different_extended_attributes(self):
		self.set_is_different_attributes("Different extended attributes")
	
	def set_is_unknown(self, message):
		self.__type = self.CONST_TYPE_UNKNOWN
		self.__message = message
	
	def get_is_unknown(self):
		return self.__type == self.CONST_TYPE_UNKNOWN
	
	@staticmethod
	def friendly_time_difference(stamp1, stamp2):
		delta = abs(stamp1 - stamp2)
		friendly = humanfriendly.format_timespan(delta)
		return friendly


#
def main():

	bd = BackupDiff()
	bd.run()


#
if __name__ == "__main__":
	main()
