*** warning: there be dragons in here. ***

extra dependencies:
- sever vs. client have different python lib dependencies
- python image library
- python-magic
- whatever else is missing when you try to run it e.g. pathlib2, requests...

notes:
- gpl2 license, please.
- lets you back up files to a central place.
- uses md5 hash to deduplicate.
- builds html files to let you browse the backups.
- browse shows all originating places of files.

examples:
start on server 192.168.123.42
sudo ./pybadkd.py &
will run on default port of 6969.
run client to push files:
client ~/Stufftobackup 192.168.123.42
will push over to default port of 6969.


