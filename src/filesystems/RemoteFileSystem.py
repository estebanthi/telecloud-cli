import os

from src.filesystems.FileSystem import FileSystem
from src.api import Api


class RemoteFileSystem(FileSystem):

    def __init__(self, root='/', api_url='http://localhost:5000'):
        super().__init__(root)
        self._api = Api(api_url)

        self._files_structure = self._api.get_remote_files_structure()
        self._directories_structure = self._api.get_remote_folder_structure()
        self._full_structure = {**self._files_structure, **self._directories_structure}

    def update_structure(self):
        self._files_structure = self._api.get_remote_files_structure()
        self._directories_structure = self._api.get_remote_folder_structure()
        self._full_structure = {**self._files_structure, **self._directories_structure}

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

    def exists(self, path):
        path = self.format_path(path)
        return path in self._files_structure or path in self._directories_structure

    def listdir(self, path):
        return [self.basename(self.format_path(path)) for path in self._full_structure if self.parent(path) == self.format_path(path)]

    def basename(self, path):
        path = self.format_path(path)
        return path.split('/')[-1] if '/' in path else path

    def isfile(self, path):
        path = self.format_path(path)
        return path in self._files_structure

    def isdir(self, path):
        path = self.format_path(path)
        return path in self._directories_structure

    def parent(self, path):
        path = self.format_path(path)
        return os.path.dirname(path)

    def children(self, path, files=True, directories=True, n=float('inf')):
        path = self.format_path(path)

        children = []
        if files:
            children += [os.path.join(path, f) for f in self._files_structure if self.parent(f) == path]
        if directories:
            children += [os.path.join(path, d) for d in self._directories_structure if self.parent(d) == path]
        if n > 0:
            for child in children:
                children += self.children(child, files, directories, n-1)
        return children

    def mkdir(self, path):
        path = self.format_path(path)

        parent = self.parent(path)

        if not self.isdir(parent):
            self.mkdir(parent)

        parent_id = self._directories_structure[parent]
        directory_name = self.basename(path)

        self._api.create_directory(directory_name, parent_id)
        self.update_structure()

    def rmdir(self, path):
        path = self.format_path(path)

        directory_id = self._directories_structure[path]
        self._api.delete_directory(directory_id)
        self.update_structure()

    def remove(self, path):
        path = self.format_path(path)

        file_id = self._files_structure[path]
        self._api.rm(file_id)
        self.update_structure()

    def mv(self, src, dst):
        src = self.format_path(src)
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


        self.update_structure()

    def tag(self, files, directories, tags, regex, recursive):
        files = self.format_paths(files)
        directories = self.format_paths(directories)

        if directories:
            files += self.get_files(directories, regex=regex, recursive=recursive)

        files = self.filter(files, regex)

        files_ids = [self._files_structure[file] for file in files]
        for file_id in files_ids:
            self._api.add_tags(file_id, tags)

    def untag(self, files, directories, tags, regex, recursive):
        files = self.format_paths(files)
        directories = self.format_paths(directories)

        if directories:
            files += self.get_files(directories, regex=regex, recursive=recursive)

        files = self.filter(files, regex)

        files_ids = [self._files_structure[file] for file in files]
        for file_id in files_ids:
            self._api.remove_tags(file_id, tags)

    def upload(self, local_paths, remote_paths, tags, regex):
        files = self.format_paths(remote_paths)

        for path in files:
            parent = self.parent(path)
            if not self.isdir(parent):
                self.mkdir(parent)

        for index, file in enumerate(remote_paths):
            to = self.parent(file)
            to = self._directories_structure[to]
            self._api.upload(local_paths[index], to, tags)

        self.update_structure()