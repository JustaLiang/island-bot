import os

file_id = '1vrpKwPtLfwqW4gqLDrbtyC76SDi7hhFJ9VpruYsYNMw'
request = drive_service.files().export_media(fileId=file_id,
                                             mimeType='application/pdf')
fh = io.BytesIO()
downloader = MediaIoBaseDownload(fh, request)
done = False
while done is False:
    status, done = downloader.next_chunk()
    print "Download %d%%." % int(status.progress() * 100)