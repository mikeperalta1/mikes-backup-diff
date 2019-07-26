# Mike's Backup Diff

This is a tool to help show differences between a source folder, and its mirrored backup folder. It will show you which directories and files are missing or different between the two folder.

This can be very useful to detect files which may have been *accidentally deleted* from your source folder, so you can replace them from your backup before running another mirror.

## Requirements 

* Python 3

* Python library *humanfriendly*

    ``` sudo pip3 install humanfriendly ```

## How to Execute

Invoking the python3 interpreter directly is preferred:

```python3 /path/to/backup-diff.py```

But you can possibly also execute it directly, if your *env* program is setup for Python 3:

```/path/to/backup-diff.py```

## Command Line Arguments

You must at minimum specify the source and the backup directories. Following is a list of currently accepted command line arguments:

### --source-path < path >

Specifies the path to your source directory

### --backup-path < path >

Specifies the path to your backup directory

### --no-clean

Don't make any attempt to clean the generated report of redundant entries. This might be useful if you think the report isn't accurate.

#### Example Call With Arguments

Here's an example of how you might invoke the script:

```python3 /path/to/backup-diff.py --source-path "/my/source/directory/path" --backup-path "/my/backups/main-backup" ```


