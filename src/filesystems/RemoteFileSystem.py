import os
import logging

from src.filesystems.FileSystem import FileSystem
from src.api import Api


class RemoteFileSystem(FileSystem):

    def __init__(self, root='/', api_url='http://localhost:5000'):
        super().__init__(root)
        self._api = Api(api_url)

        self._logger = logging.getLogger('app')
        try:
            self._files_structure = self._api.get_remote_files_structure()
            self._directories_structure = self._api.get_remote_folder_structure()
            self._full_structure = {**self._files_structure, **self._directories_structure}
        except Exception as e:
            self._logger.error(e)
            raise ConnectionError("Connection to the server could not be established")
        self._logger.info("Remote file system initialized")

    def _update(self):
        self._files_structure = self._api.get_remote_files_structure()
        self._directories_structure = self._api.get_remote_folder_structure()
        self._full_structure = {**self._files_structure, **self._directories_structure}

    def listdir(self, path):
        return [self.basename(self.format_path(path_)) for path_ in self._full_structure
                if self.parent(path_) == self.format_path(path)]

    def _create_directory(self, path):
        parent = self.parent(path)
        parent_id = self._directories_structure[parent]
        directory_name = self.basename(path)

        self._api.create_directory(directory_name, parent_id)

    def _remove_directory(self, path):
        directory_id = self._directories_structure[path]
        self._api.delete_directory(directory_id)

    def _move(self, src, dst):
        dst = self.format_path(dst)

        dst_is_file = self.isfile(dst)
        dst_exists = self.exists(dst)

        if not dst_exists:
            src_id = self._full_structure[src]
            dst_basename = self.basename(dst)
            self._api.rename(src_id, dst_basename)

        elif not dst_is_file:
            src_id = self._full_structure[src]
            dst_id = self._directories_structure[dst]
            self._api.move(src_id, dst_id)


        self.update()

    def _remove_file(self, path):
        file_id = self._files_structure[path]
        self._api.rm(file_id)

    def isfile(self, path):
        path = self.format_path(path)
        return path in self._files_structure

    def isdir(self, path):
        path = self.format_path(path)
        return path in self._directories_structure

    def parent(self, path):
        path = self.format_path(path)
        return os.path.dirname(path)

    def exists(self, path):
        path = self.format_path(path)
        return path in self._files_structure or path in self._directories_structure

    def basename(self, path):
        path = self.format_path(path)
        return path.split('/')[-1] if '/' in path else path

    def get_files(self, directories, regex=None, recursive=False, tags=None):
        directories = self.format_paths(directories)

        if recursive:
            directories = self.get_directories(directories, recursive=True) + directories

        directories_ids = [self._directories_structure[directory] for directory in directories]
        files = self._api.get_files_meta(directories=directories_ids, tags=tags)

        files_ = []
        for file in files:
            file_id = file['_id']
            for k, v in self._files_structure.items():
                if v == file_id:
                    files_.append(k)

        if regex:
            files_ = self.filter_entities(files_, regex)

        return files_

    def get_directories(self, directories, regex=None, recursive=False):
        directories = self.format_paths(directories)

        directories_ = []
        for directory in directories:
            if self.exists(directory):
                for dir_ in self._directories_structure:
                    if self.parent(dir_) == directory and dir_ != directory:
                        directories_.append(dir_)

                if recursive:
                    directories_ += self.get_directories([os.path.join(directory, d) for d in directories_], regex, recursive)

        if regex:
            directories_ = self.filter_entities(directories, regex)

        return directories_

    def _tag_path(self, path, tags):
        file_id = self._files_structure[path]
        self._api.add_tags(file_id, tags)

    def _get_tags_path(self, path):
        file_id = self._files_structure[path]
        return self._api.get_tags(file_id)

    def _untag_path(self, path, tags):
        file_id = self._files_structure[path]
        self._api.remove_tags(file_id, tags)

    def _upload_file(self, local_path, remote_path, tags):
        to = self.parent(remote_path)
        to = self._directories_structure[to]

        self._api.upload(local_path, to, tags)

    def _download_file(self, remote_path, local_path):
        to = self.parent(local_path)
        id_ = self._files_structure[remote_path]

        self._api.download(id_, to)