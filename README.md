# Mike's Backup Diff

This is a tool to help show differences between a source folder, and its mirrored backup folder. It will show you which directories and files are missing or different between the two folder.

This can be very useful to detect files which may have been *accidentally deleted* from your source folder, so you can replace them from your backup before running another mirror.

## Requirements 

* Python 3

* Python library *humanfriendly*

    * ``` sudo pip3 install humanfriendly ```

* rsync

    * ```sudo apt install rsync```
    * ```sudo yum install rsync```
    * etc

## How to Execute

Invoking the python3 interpreter directly is preferred:

```python3 /path/to/backup-diff.py```

But you can possibly also execute it directly, if your *env* program is setup for Python 3:

```/path/to/backup-diff.py```

## Command Line Arguments

You must at minimum specify the source and the backup directories. Following is a list of currently accepted command line arguments:

### --source-path < path >

Specifies the path to your source directory

### --source-remote-host < hostname or ip >

Specifies the remote host where your source directory resides

### --source-remote-user < username >

Specifies the user to connect as, when connecting to a remote host with *--source-remote-host*

### --backup-path < path >

Specifies the path to your backup directory

### --backup-remote-host < hostname or ip >

Specifies the remote host where your backup directory resides

### --backup-remote-user < username >

Specifies the user to connect as, when connecting to a remote host with *--backup-remote-host*

### --ssh-key < key path >

Specifies the SSH key to use, when connecting to remote hosts.

When omitted, and also connecting to a remote host, the default key for the current user will be used (probably).

### --use-rsync

Force this tool to use rsync for comparison. If not specified, directories and files will just be compared normally. In the future, the non-rsync mode might be removed.

### --rsync

Same as *--use-rsync*

### --no-clean

Don't make any attempt to clean the generated report of redundant entries. This might be useful if you think the report isn't accurate.

#### Example Call With Arguments

Here's an example of how you might invoke the script with two local directories:

```
python3 /path/to/backup-diff.py --source-path "/my/source/directory/path" --backup-path "/my/backups/main-backup"
```

Here's an example of how you might compare a local directory with a remote backup:

```
python3 /path/to/backup-diff.py --source-path "/my/local/source/directory/path" --backup-path "/path/on/remote/server/backups/main-backup" --backup-remote-host "example.com" --backup-remote-user "me123" --ssh-key "/path/to/my/ssh/key"
```

