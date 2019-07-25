#!/usr/env python3

"""

Mike's Backup Diff

A simple script to help compare changes between a backup destination directory, and its source

Copyright 2019 Mike Peralta; All rights reserved

Released under the GNU GENERAL PUBLIC LICENSE v3 (See LICENSE file for more)

"""


#
import datetime
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
		
	def run(self):
		
		self.consume_arguments()
		self.calculate_comparison_items()
		self.do_comparison()
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
		
		source_path_items = self.consume_dir(self.__source_path)
		source_path_items = self.strip_root_dir(self.__source_path, source_path_items)
		
		self.__source_path_items = source_path_items
	
	def consume_backup_path(self):
		
		if self.__backup_path is None:
			raise Exception("Please provide a backup destination path")
		if not os.path.isdir(self.__backup_path):
			raise Exception("Backup destination path isn't a valid directory")
		
		backup_path_items = self.consume_dir(self.__backup_path)
		backup_path_items = self.strip_root_dir(self.__backup_path, backup_path_items)
		
		self.__backup_path_items = backup_path_items
	
	@staticmethod
	def consume_dir(dir_path):
		
		#
		paths = set()
		
		#
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
		
		return paths
	
	def do_comparison(self):
		
		entries = []
		
		# Compare everything in the source path
		for item in self.__source_path_items:
			
			entry = self.calculate_difference_entry(item)
			if entry:
				entries.append(entry)
		
		# Compare only things in the backup path that weren't
		# in the source
		backup_items_not_in_source = self.__backup_path_items - self.__source_path_items
		for item in backup_items_not_in_source:
			
			entry = self.calculate_difference_entry(item)
			if entry:
				entries.append(entry)
		
		self.__difference_entries = entries
	
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
		path_stripped = path[ len(root_dir) + 1 : ]
		# print(path, "===>", path_stripped)
		
		return path_stripped
	
	#
	def calculate_difference_entry(self, comparison_item):
		
		entry = DifferenceEntry(comparison_item)
		
		path_source = os.path.join(self.__source_path, comparison_item)
		path_backup = os.path.join(self.__backup_path, comparison_item)
		
		# In source but not backup
		if os.path.exists(path_source) and not os.path.exists(path_backup):
			entry.set_is_missing_from_backup()
			
		# In backup but not source
		elif os.path.exists(path_backup) and not os.path.exists(path_source):
			entry.set_is_missing_from_source()
		
		# Type mismatch
		elif os.path.isdir(path_source) and os.path.isfile(path_backup):
			entry.set_is_type_mismatch("Source is a directory, but backup is a file")
		elif os.path.isfile(path_source) and os.path.isdir(path_backup):
			entry.set_is_type_mismatch("Source is a file, but backup is a directory")
		
		# Compare props
		else:
			
			print("Received item:", comparison_item)
			print("Comparing props with:", path_source)
			print("Comparing props with:", path_backup)
			
			path_source_mtime = int(os.path.getmtime(path_source))
			path_backup_mtime = int(os.path.getmtime(path_backup))
			
			path_source_size = os.path.getsize(path_source)
			path_backup_size = os.path.getsize(path_backup)
			
			# Source modification time is newer
			if path_source_mtime > path_backup_mtime:
				entry.set_source_is_newer(path_source_mtime, path_backup_mtime)
			# Backup modification time is newer
			elif path_backup_mtime > path_source_mtime:
				entry.set_backup_is_newer(path_source_mtime, path_backup_mtime)
			
			# Different file sizes
			elif os.path.isfile(path_source) \
				and os.path.isfile(path_backup) \
				and (path_source_size != path_backup_size):
				entry.set_different_sizes(path_source_size, path_backup_size)
			
			# No difference
			else:
				entry = None
		
		return entry
	
	def print_report(self):
	
		for entry in self.__difference_entries:
			print(entry)
			print("")


#
class DifferenceEntry:
	
	def __init__(self, item):
		
		self.__item = None
		self.__type = None
		self.__message = None
		
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
	
	def set_is_type_mismatch(self, message):
		
		self.__type = "type_mismatch"
		self.__message = message
	
	def set_is_missing_from_source(self):
		
		self.__type = "missing_in_source"
		self.__message = "Item is in backup but not in source"
	
	def set_is_missing_from_backup(self):
		self.__type = "missing_in_backup"
		self.__message = "Item is in source but not in backup"
	
	def set_source_is_newer(self, stamp_source, stamp_backup):
		time_difference = self.friendly_time_difference(stamp_source, stamp_backup)
		self.__type = "source_is_newer"
		self.__message = "Item has been modified more recently in source (" + str(stamp_source) + ")" \
			+ " than in backup (" + str(stamp_backup) + ")" \
			+ "; Difference is " + str(time_difference)
	
	def set_backup_is_newer(self, stamp_source, stamp_backup):
		time_difference = self.friendly_time_difference(stamp_source, stamp_backup)
		self.__type = "backup_is_newer"
		self.__message = "Item has been modified more recently in backup (" + str(stamp_backup) + ")" \
			+ " than in source (" + str(stamp_source) + ")" \
			+ "; Difference is " + str(time_difference)
	
	def set_different_sizes(self, source_item_size, backup_item_size):
		self.__type = "different_sizes"
		self.__message = \
			"Source has a file size of " + str(source_item_size) \
			+ ", but backup has a file size of " + str(backup_item_size)
	
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
