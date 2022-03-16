import os
import slack
import time
import schedule

class Monitor():

    def __init__(self):
        self.monitor()

    def fileadded(self, details, folderName: str):
        file_name = list(details)[0][0]
        parent_id = list(details)[0][1]
        file_id = list(details)[0][2]
        ext = list(details)[0][3]
        viewLink = list(details)[0][4]

        f = self.file_added_attachment

        try:
            downloadLink = eval(list(details)[0][5])
            if len(downloadLink) > 1:
                l = []
                for ext, link in downloadLink.items():
                    download_as = ext.split('/')[-1]
                    additional_downloadLinks = {
                        "name": f"download_{ext}", "text": f'Download as {download_as}', "type": "button", "value": f"value_{ext}", "url": link}
                    l.append(additional_downloadLinks)
                    f[0]['actions'].append(additional_downloadLinks)
        except:
            downloadLink = list(details)[0][5]
            download_as = ext.split('/')[-1]
            additional_downloadLinks = {"name": f"download_{ext}", "text": f'Download as {download_as}',
                                        "type": "button", "value": f"value_{ext}", "url": downloadLink}
            f[0]['actions'].append(additional_downloadLinks)

        message = self.file_added_msg + \
            f"\nFILE NAME: {file_name} \nFILE TYPE: {ext} \n"
        f[0]['actions'][0]['url'] = viewLink

        channel_name = self.slack_drive_info[folderName]
        channel_id = self.getChannelID(channelName=channel_name)
        dataentryID = self.getChannelID(channelName='_data_entry')

        response = self.client.chat_postMessage(
            channel=channel_name, text=message, attachments=f)
        self.writeCSV(fileName='messages', row=[
                    file_name, ext, file_id, parent_id, response['ts'], folderName, channel_name, channel_id, message, f])
        time.sleep(1)
        response = self.client.chat_postMessage(
            channel='_data_entry', text=message, attachments=f)
        self.writeCSV(fileName='messages', row=[
                    file_name, ext, file_id, parent_id, response['ts'], folderName, '_data_entry', dataentryID, message, f])

        return

    def fileDeteted(self, details, folderName: str):
        file_name = list(details)[0][0]
        ext = list(details)[0][3]
        message = self.file_deleted_msg + \
            f"\nFILE NAME: {file_name} \nFILE TYPE: {ext}"
        channel_id = self.slack_drive_info[folderName]
        self.client.chat_postMessage(channel=channel_id, text=message)

    def monitor(self):
        import users
        parent_directory = users.parent_directory
        for user in users.users:
            SLACK_TOKEN = users.SLACK_TOKENS[user]
            os.chdir(parent_directory + f'\\{user}')

            import gdrive
            import config
            from utils import utils
            import folder_dict as fd

            print('imported')

            self.name = getattr(config, 'file_deleted_msg')
            self.slack_drive_info = getattr(config, 'slack_drive_info')
            self.file_added_msg = getattr(config, 'file_added_msg')
            self.file_added_attachment = getattr(config, 'file_added_attachment')
            self.folder2monitor = getattr(config, 'folder2monitor')
            self.drive_id_info = getattr(config, 'drive_id_info')

            self.writeCSV = getattr(utils, 'writeCSV')
            self.getChannelID = getattr(utils, 'getChannelID')

            def monitorFolder(folder: str):
                new_fileList = fd.FolderDict().generate_tree(folder)
                status, added, deleted = fd.FolderDict().compare_and_update(folder, new_fileList)
                parent_id = self.drive_id_info[folder]
                # TODO : Implement proper preprocessing before sending it to slack
                return status, added, deleted, parent_id

            def driveMonitor():
                for folder in self.folder2monitor:
                    status, added, deleted, parent_id = monitorFolder(folder)
                    changed_files = len(status)
                    for file in status:
                        if 'Added' in file.keys():
                            self.fileadded(file['Added'], folderName=folder)
                        if 'Deleted' in file.keys():
                            self.fileDeteted(file['Deleted'], folderName=folder)
                return


            self.client = slack.WebClient(token=SLACK_TOKEN)
            self.drive = gdrive.Drive().get_authenticated()
            driveMonitor()

m = Monitor()

# if __name__ == '__main__':
#     schedule.every(5).minutes.do(monitor)
#     while True:
#         schedule.run_pending()
#         time.sleep(1)