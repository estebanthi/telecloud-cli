import requests
import argparse
import os
import tqdm
import shutil


class CommandsController:

    def __init__(self, base_api_url):
        self.base_api_url = base_api_url

    def ls(self, args):
        parser = argparse.ArgumentParser()
        parser.add_argument("--tags")
        parser.add_argument("--types")
        args = parser.parse_args(args.split())

        url = self.get_ls_url(args.tags, args.types)
        response = requests.get(url)
        return response.json()

    def get_ls_url(self, tags, file_types):
        url = self.base_api_url + "/files"
        if tags or file_types:
            url += "?"
            if tags:
                for tag in tags.split(","):
                    url += f"tags={tag}&"
            if file_types:
                for file_type in file_types.split(","):
                    url += f"types={file_type}&"
            if url[-1] == "&":
                url = url[:-1]
        return url

    def upload(self, args):
        parser = argparse.ArgumentParser()
        parser.add_argument("--folder")
        parser.add_argument("--file")
        parser.add_argument("--tags")
        args = parser.parse_args(args.split())

        if args.file:
            return self.upload_file(args.file, args.tags or [])

        if args.folder:
            files = []
            for root, _, file_names in os.walk(args.folder):
                for file_name in file_names:
                    files.append(os.path.join(root, file_name))
            for file in tqdm.tqdm(files):
                res = self.upload_file(file, args.tags or [])
                if res.get('error'):
                    print(res['error'])

    def upload_file(self, file_path, tags):
        print(f"Uploading {file_path}")
        file_size = int(os.path.getsize(file_path))
        file_type = file_path.split('.')[-1]
        post_data = {'type': file_type, 'size': file_size, 'tags': tags}
        files = {'file': open(file_path, 'rb')}
        response = requests.post(self.base_api_url + "/upload", data=post_data, files=files)
        return response.json()

    def download(self, args):
        parser = argparse.ArgumentParser()
        parser.add_argument("--id")
        parser.add_argument("--tags")
        parser.add_argument("--types")
        parser.add_argument("-o", "--output")
        args = parser.parse_args(args.split())
        return self.download_files(args.id, args.tags, args.types, args.output)

    def download_files(self, file_id, tags, file_types, output):
        if file_id:
            return self.download_file(file_id, output)
        else:
            command = ""
            if tags:
                command += f"--tags {tags} "
            if file_types:
                command += f"--types {file_types}"
            files = self.ls(command)
            for file in tqdm.tqdm(files):
                self.download_file(file['_id'], output)

    def download_file(self, file_id, output):
        print(f"Downloading {file_id}")
        file_download = requests.get(f'{self.base_api_url}/download/{file_id}')
        file_name = file_download.headers['Content-Disposition'].split('filename=')[1]
        file_path = os.path.join(output or "./", file_name)
        with open(file_path, 'wb') as f:
            f.write(file_download.content)
        return file_path

    def clear(self, args):
        return requests.get(self.base_api_url + "/clear").json()

    def rm(self, args):
        parser = argparse.ArgumentParser()
        parser.add_argument("--id")
        parser.add_argument("--tags")
        parser.add_argument("--types")
        args = parser.parse_args(args.split())
        return self.rm_files(args.id, args.tags, args.types)

    def rm_files(self, file_id, tags, file_types):
        if file_id:
            return self.rm_file(file_id)
        else:
            command = ""
            if tags:
                command += f"--tags {tags} "
            if file_types:
                command += f"--types {file_types}"
            files = self.ls(command)
            for file in tqdm.tqdm(files):
                self.rm_file(file['_id'])

    def rm_file(self, file_id):
        print(f"Deleting {file_id}")
        requests.delete(f'{self.base_api_url}/files/{file_id}')

    def tag(self, args):
        parser = argparse.ArgumentParser()
        parser.add_argument("--id")
        parser.add_argument("--tags")
        parser.add_argument("--types")
        args = parser.parse_args(args.split())
        return self.tag_files(args.id, args.tags, args.types)

    def tag_files(self, file_id, tags, file_types):
        if file_id:
            return self.tag_file(file_id, tags)
        else:
            command = ""
            if file_types:
                command += f"--types {file_types}"
            files = self.ls(command)
            for file in tqdm.tqdm(files):
                self.tag_file(file['_id'], tags)

    def tag_file(self, file_id, tags):
        print(f"Tagging {file_id}")
        requests.post(f'{self.base_api_url}/files/{file_id}/tags', data={'tags': tags})

    def untag(self, args):
        parser = argparse.ArgumentParser()
        parser.add_argument("--id")
        parser.add_argument("--tags")
        parser.add_argument("--types")
        args = parser.parse_args(args.split())
        return self.untag_files(args.id, args.tags, args.types)

    def untag_files(self, file_id, tags, file_types):
        if file_id:
            return self.untag_file(file_id, tags)
        else:
            command = ""
            if file_types:
                command += f"--types {file_types}"
            files = self.ls(command)
            for file in tqdm.tqdm(files):
                self.untag_file(file['_id'], tags)

    def untag_file(self, file_id, tags):
        print(f"Untagging {file_id}")
        requests.delete(f'{self.base_api_url}/files/{file_id}/tags', data={'tags': tags})

    def tags(self, args):
        return requests.get(self.base_api_url + "/tags").json()