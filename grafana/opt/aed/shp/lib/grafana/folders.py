import json

from helper import Helper


class Folders:

    def __init__(self, org_id):
        self.org_id = org_id
        self.folders = dict()
        self.folder_uids = dict()
        self.helper = Helper(org_id)
        self.load_all()

    def add_folder_to_list(self, folder):
        title = str(folder['title'])
        self.folders[folder['id']] = title

    def load_all(self):
        resp = self.helper.api_get_with_params("search", {'type': 'dash-folder'})
        folders = json.loads(resp.content)
        for folder in folders:
            self.add_folder_to_list(folder)
            self.folder_uids[folder['id']] = folder['uid']
        self.add_folder_to_list({'title': 'General', 'id': 1})

    def get_folders(self):
        return self.folders

    def create_folder(self, folder_name):
        resp = self.helper.api_post_with_data('folders', {'title': folder_name})
        folder = json.loads(resp.content)
        self.add_folder_to_list(folder)
        return folder['id']

    def get_folder_id(self, title):
        try:
            for folder_id, folder_name in list(self.folders.items()):
                if title == folder_name:
                    return folder_id
        except:
            raise Exception("Failed to find folder: " + title)

    def delete_folder(self, folder_id):
        uid = self.folder_uids[folder_id]
        self.helper.api_delete('folders/' + str(uid))
