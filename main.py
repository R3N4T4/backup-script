#!/usr/bin/python -tt


"""
Rena Puchbauer, 09/2018

Purpose of script:
As soon as a file is saved on the Desktop,the file should be renamed to the current date+original filename,
so foo.pdf should would be renamed to 2018-08-24-03:46:12_foo.pdf and then moved to a local backup folder. After the
file was moved to the Backup folder, it will be uploaded to Google drive and upon completion, deleted from the Desktop.
"""

from __future__ import print_function
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from googleapiclient.http import MediaFileUpload
import os
import datetime
import hashlib
import mimetypes
import json
import requests
import shutil

def send_slack_notification(message):
    """
    gets called whenever an error (failed backup) occurs:
    Incoming Webhooks:
    add webhook URL as environment variable: export SLACK_WEBHOOK_URL='your webhook url'
    """
    webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
    print("webhook URL:", webhook_url)
    slack_data = {'text': message}

    response = requests.post(
        webhook_url, data=json.dumps(slack_data),
        headers={'Content-Type': 'application/json'}
    )
    if response.status_code != 200:
        raise ValueError(
            'Request to slack returned an error %s, the response is:\n%s'
            % (response.status_code, response.text))


def newfiles_check(source_dir, backup_dir, logifempty=True):
    """
    Check if there are any files on Desktop. If no files exist, write timestamp +'no files today' to logfile and
    sleep for 1 hour. If file exists, call filename_check() function.
    """
    filenames_list = os.listdir(source_dir)
    print(filenames_list)
    source_files = []

    if not filenames_list and logifempty:
        with open('Logs.txt', 'a') as f:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            message = timestamp + ": No files to back up. \n"
            f.writelines(message)
            send_slack_notification(message)
        return
    else:
        for fname in os.listdir(source_dir):
            if os.path.isfile(os.path.join(source_dir, fname)):
                source_files.append(fname)
            else:
                newdir = os.path.join(source_dir, fname)
                new_backup_dir = os.path.join(backup_dir, fname)
                os.makedirs(new_backup_dir)
                newfiles_check(newdir, new_backup_dir, False)
        print("format_filename call with: {} \n {} \n {}".format(source_dir,backup_dir,source_files))
        format_filename(source_dir, backup_dir, source_files)


def format_filename(dir, backup_dir, filenames_list):
    """
    Rename each file to timestamp+filename and check if filename exists in Backup folder.
    If filename already exists, add "_1" to new file and check if this exists, if that filename exists, increase last digit
    by 1 until filename is unique. Call local_backup() function
    """
    backup_files = sorted(os.listdir(backup_dir))
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H_")

    for filename in filenames_list:
        newfilename = timestamp + filename
        if newfilename in backup_files:
            unique_name = unique_filename(filename, timestamp, backup_files)
            os.rename(os.path.join(dir, filename), os.path.join(dir, unique_name))
        else:
            os.rename(os.path.join(dir, filename), os.path.join(dir, newfilename))
    local_backup(dir, os.listdir(dir), backup_dir)


def unique_filename(filename, timestamp, backup_files, i=1):
    newfilename = timestamp + str(i) + "_" + filename
    if newfilename in backup_files:
        return unique_filename(filename, timestamp, backup_files, i + 1)
    else:
        return newfilename


def local_backup(source_dir, source_files, backup_dir):
    """
    Copy all files from Desktop to Backup folder.
    In case copyjob fails, write timpestamp + filename + 'copy to backup folder failed' to logfile, open logfile and stop
    script.
    """
    print("source_dir:", source_dir)
    print("backup dir", backup_dir)

    new_backup_list = []

    for file in source_files:
        print("file -local backup", file)
        if os.path.isfile(os.path.join(source_dir, file)):
            hash_in_sourcedir = hash_sum(source_dir, file)
            print("Hash in sourcedir: ", hash_in_sourcedir)
            cmd = "cp " + os.path.join(source_dir, file) + " " + backup_dir + "/" + file
            print(cmd)
            os.system(cmd)
            hash_in_backupdir = hash_sum(backup_dir, file)
            print("Hash in backupdir: ", hash_in_backupdir)
            if hash_in_sourcedir == hash_in_backupdir:
                pass
            else:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H_")
                message = timestamp + " Backup from Desktop to Backup folder failed for file: {}\n" + file
                with open('Logs.txt', 'a') as f:
                    f.writelines(message)
                    send_slack_notification(message)
                    exit()
        else:
            pass

    for files in os.listdir(backup_dir):
        if os.path.isfile(os.path.join(backup_dir, files)):
            new_backup_list.append(files)
        else:
            pass

    gdrive_upload(new_backup_list, backup_dir)


def hash_sum(dir, file):
    hasher = hashlib.md5()
    absolute_path = os.path.join(dir, file)
    with open(absolute_path, 'rb') as f:
        buffer = f.read()
        hasher.update(buffer)
    return hasher.hexdigest()


def gdrive_upload(backup_files, backup_dir):
    """
    Upload all files from backup folder to Google drive.
    """
    print("gdrive called")
    # Setup the Drive v3 API
    try:
        SCOPES = 'https://www.googleapis.com/auth/drive'
        store = file.Storage('token.json')
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
            creds = tools.run_flow(flow, store)
        service = build('drive', 'v3', http=creds.authorize(Http()))


        for backup in backup_files:
            print("file to backup",backup)
            file_metadata = {'name': backup}
            mimetype1 = mimetypes.guess_type(backup)
            if mimetype1[0] == None:
                mimetype2 = 'text/plain'
                with open('Logs.txt', 'a') as f:
                    f.write(datetime.datetime.now().strftime("%Y-%m-%d-%H_") + "File without mimetype: {} \n".format(
                        backup))
                    print("File without format: {}".format(backup))
                    message = "File without format: " + backup
                    send_slack_notification(message)
            else:
                mimetype2 = mimetype1[0]
            file_to_upload = os.path.join(backup_dir,backup_files[0])
            service.files().create(body=file_metadata, media_body=MediaFileUpload(file_to_upload, mimetype2),
                                   fields='id').execute()
    except BaseException as e:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H_")
        message = timestamp + " Google Drive upload failed for file: " + backup
        send_slack_notification(message)
        print(e)

def cleanup(source_dir):
    print("CLEANUP CALLED FOR SOURCE DIR: ", source_dir)
    try:
        shutil.rmtree(source_dir)
    except BaseException as e:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H_")
        message = timestamp + " File deletion failed "
        send_slack_notification(message)
        print(e)

def main():
    #Replace source_dir and backup_dir with your own directories:
    source_dir = "/Users/rena/Desktop/Testdir"
    backup_dir = "/Users/rena/Documents/Backups/2018"
    newfiles_check(source_dir, backup_dir)
    #cleanup(source_dir)


if __name__ == '__main__':
    main()
