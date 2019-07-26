#!/usr/env python3

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
import sys


#
class BackupDiff:
	
	def __init__(self):
		
		self.__source_path = None
		self.__backup_path = None
		
		self.__source_path_items = None
		self.__backup_path_items = None
		
		self.__difference_entries = None
		self.__do_clean_difference_entries = True
		
	def run(self):
		
		self.consume_arguments()
		self.calculate_comparison_items()
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
		
		now = self.current_time()
		
		to_log = "[" + now + "][Mike's Backup Diff] " + str(s)
		if o is not None:
			to_log += " " + str(o)
		
		print(to_log)
	
	def consume_arguments(self):
		
		for i in range(1, len(sys.argv)):
			
			arg = sys.argv[i]
			
			if arg == "--source-path":
				i, one_path = self.consume_argument_companion(i)
				self.__source_path = os.path.abspath(one_path)
				self.log("Found source path argument:", self.__source_path)
			
			elif arg == "--backup-path":
				i, one_path = self.consume_argument_companion(i)
				self.__backup_path = os.path.abspath(one_path)
				self.log("Found backup destination path argument:", self.__backup_path)
			
			elif arg == "--no-clean":
				self.__do_clean_difference_entries = False
				self.log("Won't clean Difference entries")
	
	@staticmethod
	def consume_argument_companion(arg_index):
		
		companion_index = arg_index + 1
		if companion_index >= len(sys.argv):
			raise Exception("Expected argument after", sys.argv[arg_index])
		
		return companion_index, sys.argv[companion_index]
	
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
		
		self.log("Cleaning difference entries")
		
		# Build a temp list of all known difference entries
		temp_entries = []
		for entry in entries:
			temp_entries.append(entry)
		# print("Temp entries count:", len(temp_entries))
		
		# Loop through entries, attempting to clean for one at a time,
		# until no cleaning has been done
		while True:
			
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
				break
			
			# Remove this entry from the temp list, and clean with it as root
			temp_entries.remove(most_shallow_entry)
			self.clean_child_difference_entries(entries, most_shallow_entry)
	
	def clean_child_difference_entries(self, entries: list, root_entry):
		
		if entries is None:
			entries = self.__difference_entries
		
		# print("Enter clean_child_difference_entries")
		# print(root_entry)
		
		root_entry_item = root_entry.get_item()
		
		entries_to_delete = []
		
		# Check every other entry as a possible child of the root
		for child_entry in entries:
			
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
		
		# Handle entries to delete
		for entry in entries_to_delete:
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
		
		# Sort all entries
		for section_key in report:
			self.sort_difference_entries(report[section_key]["entries"])
		
		return report
	
	@staticmethod
	def print_progress_message(s):
		
		sys.stdout.write("\033[F")  # back to previous line
		sys.stdout.write("\033[K")  # clear line
		print(s)
	
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
			"size_difference"
		]
		
		#
		self.print_report_heading("Mike's Backup Diff Report", True)
		print("Source:", self.__source_path)
		print("Backup:", self.__backup_path)
		
		# Print each non-empty report section
		found_anything = False
		for section_key in section_order:
			if len(report[section_key]["entries"]):
				found_anything = True
				self.print_report_heading(report[section_key]["label"])
				for entry in report[section_key]["entries"]:
					
					if entry.get_is_dir():
						prefix = "Directory: "
					elif entry.get_is_file():
						prefix = "File: "
					else:
						prefix = ""
					
					print(prefix + entry.get_item())
					
				print("")
		
		if not found_anything:
			print("Everything seems to match")


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
		self.__message = "Item is in backup but not in source"
	
	def get_is_missing_from_source(self):
		return self.__type == self.CONST_TYPE_MISSING_IN_SOURCE
	
	def set_is_missing_from_backup(self):
		self.__type = self.CONST_TYPE_MISSING_IN_BACKUP
		self.__message = "Item is in source but not in backup"
	
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
	
	def set_is_different_sizes(self, source_item_size, backup_item_size):
		self.__type = self.CONST_TYPE_DIFFERENT_SIZES
		self.__message = \
			"Source has a file size of " + str(source_item_size) \
			+ ", but backup has a file size of " + str(backup_item_size)
	
	def get_is_different_sizes(self):
		return self.__type == self.CONST_TYPE_DIFFERENT_SIZES
	
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
