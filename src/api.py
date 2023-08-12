import requests
import mimetypes
import os
from tqdm import tqdm



class Api:

    def __init__(self, api_url):
        self.api_url = api_url

        try:
            self.test_connection()
        except requests.exceptions.ConnectionError:
            raise ConnectionError("Connection to the server could not be established")

    def test_connection(self):
        response = requests.get(f"{self.api_url}")
        return response.status_code == 200

    def get_remote_folder_structure(self):
        response = requests.get(f"{self.api_url}/structure/directories")
        return response.json()

    def get_remote_files_structure(self):
        response = requests.get(f"{self.api_url}/structure/files")
        return response.json()

    def get_files_meta(self, tags, directories):
        query = {"tags": tags, "directories": directories}
        url = self._format_url(f"{self.api_url}/files/meta", query)
        res = requests.get(url)
        files = res.json() if res.status_code == 200 else []
        return files

    def get_directories(self):
        res = requests.get(f"{self.api_url}/directories/meta")
        directories = res.json() if res.status_code == 200 else []
        return directories

    def create_directory(self, directory_name, parent_id):
        res = requests.post(f"{self.api_url}/directories", data={"name": directory_name, "parent": parent_id})
        return res.status_code == 200

    def delete_directory(self, directory_id):
        res = requests.delete(f"{self.api_url}/directories/{directory_id}?recursive=true")
        return res.status_code == 200

    def add_tags(self, file_id, tags):
        res = requests.post(f"{self.api_url}/files/{file_id}/meta/tags", data={"tags": tags})
        return res.status_code == 200

    def get_tags(self, file_id):
        res = requests.get(f"{self.api_url}/files/{file_id}/meta")
        json = res.json()
        return json["tags"] if res.status_code == 200 and "tags" in json else []

    def remove_tags(self, file_id, tags):
        res = requests.patch(f"{self.api_url}/files/{file_id}/meta/tags", data={"tags": tags})
        return res.status_code == 200

    def rename(self, id_, new):
        res = requests.get(f"{self.api_url}/files/{id_}/meta")
        if res.status_code == 200:
            res = requests.patch(f"{self.api_url}/files/{id_}/meta", data={"name": new})
            return res.status_code == 200

        res = requests.get(f"{self.api_url}/directories/{id_}/meta")
        if res.status_code == 200:
            res = requests.patch(f"{self.api_url}/directories/{id_}/meta", data={"name": new})
            return res.status_code == 200

        return False

    def move(self, id_, new_parent_id):
        res = requests.get(f"{self.api_url}/files/{id_}/meta")
        if res.status_code == 200:
            res = requests.patch(f"{self.api_url}/files/{id_}/meta", data={"directory": new_parent_id})
            return res.status_code == 200

        res = requests.get(f"{self.api_url}/directories/{id_}/meta")
        if res.status_code == 200:
            res = requests.patch(f"{self.api_url}/directories/{id_}/meta", data={"parent": new_parent_id})
            return res.status_code == 200

    def upload(self, file, directory_id, tags):
        file_path = file
        file_size = os.path.getsize(file_path)
        file_type = mimetypes.guess_type(file_path)[0]
        post_data = {"data": [{'size': file_size, 'tags': tags, 'directory': directory_id}]}
        if file_type:
            post_data["data"][0]['type'] = file_type
        files = [('files', open(file_path, 'rb'))]

        response = requests.post(
                f'{self.api_url}/files',
                data=post_data,
                files=files,
        )

        return response.status_code == 200


    def download(self, file_id, to):
        response = requests.get(f'{self.api_url}/files/{file_id}', stream=True)
        if response.status_code == 200:
            attachment_filename = response.headers['Content-Disposition'].split('filename=')[1]
            with open(os.path.join(to, attachment_filename), 'wb') as f:
                with tqdm(total=int(response.headers['Content-Length']), unit='B', unit_scale=True, desc='Downloading', ncols=80) as pbar:
                    for chunk in response.iter_content(chunk_size=1024):
                        f.write(chunk)
                        pbar.update(len(chunk))
            return True
        return False

    def rm(self, id_):
        response = requests.delete(f'{self.api_url}/files/{id_}')
        if response.status_code != 200:
            response = requests.delete(f'{self.api_url}/directories/{id_}')
        return response.status_code == 200

    def _format_url(self, url, query):
        if query:
            url += "?"
            for key, value in query.items():
                if value:
                    if type(value) == list:
                        for v in value:
                            url += f"{key}={v}&"
                    else:
                        url += f"{key}={value}&"
            url = url[:-1]
        return url