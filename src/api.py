import requests
import src.utils as utils


class Api:

    def __init__(self, api_url):
        self.api_url = api_url

    def get_remote_folder_structure(self):
        response = requests.get(f"{self.api_url}/structure/directories")
        return response.json()

    def get_remote_files_structure(self):
        response = requests.get(f"{self.api_url}/structure/files")
        return response.json()

    def get_files_meta(self, tags, directories):
        query = {"tags": tags, "directories": directories}
        url = utils.format_url(f"{self.api_url}/files/meta", query)
        res = requests.get(url)
        files = res.json() if res.status_code == 200 else []
        return files

    def get_directories(self):
        res = requests.get(f"{self.api_url}/directories/meta")
        directories = res.json() if res.status_code == 200 else []
        return directories