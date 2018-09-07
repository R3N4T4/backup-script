# File Backup Script

## Prerequisites

- Python 3.7

Install the following pip modules:

- `googleapiclient`
- `oauth2client`

## Implementation steps:

- Check if there are any files on the Desktop, if there are no files, log 'no files today' to logfile
- Rename file to current date + filename and check if this filenmae exists in Backup folder under /Users/rena/Documents/Backups/2018.
- If filename already exists, add "-1" to new file and check if this exists, if that filename also exists, increase last digit by 1 until filename is unique
- Move file to backup folder
- Upload file to google drive/Backups/2018 folder and check if upload was complete
- If upload was complete, delete file from Desktop. In case upload was not complete, write timestamp + filename + 'upload failed' to a logfile and send Rena a text message with link to logfile
