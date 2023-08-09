import re
from abc import ABC, abstractmethod
import os
import logging


class FileSystem(ABC):

    def __init__(self, root):
        self._root = root
        self._current = root
        self.logger = logging.getLogger('app')

    @property
    def root(self):
        return self._root

    @property
    def current(self):
        return self._current

    @current.setter
    def current(self, path):
        path = self.format_path(path)
        self._current = path

    def update(self):
        self._update()

    def _update(self):
        pass

    @abstractmethod
    def listdir(self, path):
        pass

    def mkdir(self, path):
        path = self.format_path(path)

        parent = self.parent(path)

        if not self.isdir(parent):
            self.mkdir(parent)

        self.create_directory(path)

        self.update()

    def create_directory(self, path):
        self.logger.info(f"Creating directory {path}")
        self._create_directory(path)

    @abstractmethod
    def _create_directory(self, path):
        pass

    def rmdir(self, path):
        path = self.format_path(path)
        self.remove_directory(path)

        self.update()

    def remove_directory(self, path):
        self.logger.info(f"Removing directory {path}")

        path = self.format_path(path)
        self._remove_directory(path)

    @abstractmethod
    def _remove_directory(self, path):
        pass

    def remove_file(self, path):
        self.logger.info(f"Removing file {path}")
        self._remove_file(path)

    @abstractmethod
    def _remove_file(self, path):
        pass

    def mv(self, src, dst):
        src = self.format_path(src)
        dst = self.format_path(dst)

        self.logger.info(f"Moving {src} to {dst}")
        self._move(src, dst)

    @abstractmethod
    def _move(self, src, dst):
        pass

    def clean(self, path):
        path = self.format_path(path)
        children = self.children(path, files=False, directories=True)
        for child in children:
            if self.isempty(child):
                self.rmdir(child)

        self.update()

    @abstractmethod
    def isfile(self, path):
        pass

    @abstractmethod
    def isdir(self, path):
        pass

    def isempty(self, path):
        path = self.format_path(path)
        return len(self.children(path)) == 0

    def children(self, path, files=True, directories=True, n=float('inf')):
        path = self.format_path(path)

        children = []
        if files:
            if self.isdir(path):
                children += [self.join(path, f) for f in self.listdir(path) if self.isfile(self.join(path, f))]
        if directories:
            if self.isdir(path):
                children += [self.join(path, d) for d in self.listdir(path) if self.isdir(self.join(path, d))]
        if n > 0:
            for child in children:
                children += self.children(child, files, directories, n-1)

        children = list(set(children))
        children.sort(key=lambda child: child.count('/'), reverse=True)
        return children

    def parent(self, path):
        return os.path.dirname(path)

    @abstractmethod
    def exists(self, path):
        pass

    def join(self, *paths):
        return os.path.join(*paths)

    @abstractmethod
    def basename(self, path):
        pass

    def normpath(self, path):
        return os.path.normpath(path)

    def relative(self, path, start):
        return os.path.relpath(path, start)

    @abstractmethod
    def get_files(self, directories, regex=None, recursive=False, tags=None):
        pass

    @abstractmethod
    def get_directories(self, directories, regex=None, recursive=False):
        pass

    def rm(self, paths, recursive=False, regex=None):
        paths = self.format_paths(paths)

        for path in paths:
            if self.isfile(path):
                if regex:
                    if re.match(regex, self.basename(path)):
                        self.remove_file(path)
                else:
                    self.remove_file(path)
            elif self.isdir(path):
                if recursive:
                    for child in self.children(path, files=True, directories=True):
                        if self.isfile(child):
                            if regex:
                                if re.match(regex, self.basename(child)):
                                    self.remove_file(child)
                            else:
                                self.remove_file(child)
                    self.clean(path)
                    if self.isempty(path):
                        self.rmdir(path)

        self.update()

    def filter(self, paths, regex):
        paths = self.format_paths(paths)

        if not regex:
            return paths

        filtered_paths = []
        for path in paths:
            basename = self.basename(path)
            if re.match(regex, basename):
                filtered_paths.append(path)
        return filtered_paths

    def format_path(self, path):
        if path == '.':
            return self.current
        if path == '..':
            return self.parent(self.current)
        if path == '~':
            return self.root
        path = path if path.startswith('/') else os.path.join(self.current, path)
        return self.normpath(path)

    def format_paths(self, paths):
        return [self.format_path(path) for path in paths]

    def tag(self, files, directories, tags, regex, recursive):
        files = self.format_paths(files)
        directories = self.format_paths(directories)

        if directories:
            files += self.get_files(directories, regex=regex, recursive=recursive)

        files = self.filter(files, regex)
        for file in files:
            self.tag_path(file, tags)

    def tag_path(self, path, tags):
        self.logger.info(f"Tagging {path} with {tags}")
        self._tag_path(path, tags)

    def _tag_path(self):
        pass

    def untag(self, files, directories, tags, regex, recursive):
        files = self.format_paths(files)
        directories = self.format_paths(directories)

        if directories:
            files += self.get_files(directories, regex=regex, recursive=recursive)

        files = self.filter(files, regex)
        for file in files:
            self._api.remove_tags(file, tags)

    def untag_path(self, path, tags):
        self.logger.info(f"Removing {tags} from {path}")
        self._untag_path(path, tags)

    def _untag_path(self, path, tags):
        pass


    def upload(self, local_paths, remote_paths, tags):
        files = self.format_paths(remote_paths)

        for path in files:
            parent = self.parent(path)
            if not self.isdir(parent):
                self.mkdir(parent)

        for index, file in enumerate(remote_paths):
            local_path = local_paths[index]
            remote_path = file
            self.upload_file(local_path, remote_path, tags)

        self.update()

    def upload_file(self, local_path, remote_path, tags):
        self.logger.info(f"Uploading {local_path} to {remote_path}")
        self._upload_file(local_path, remote_path, tags)

    def _upload_file(self, local_path, remote_path):
        pass

    def download(self, remote_paths, local_paths):
        files = self.format_paths(remote_paths)

        for path in files:
            parent = self.parent(path)
            if not self.isdir(parent):
                self.mkdir(parent)

        for index, file in enumerate(local_paths):
            remote_path = remote_paths[index]
            local_path = file
            self.download_file(remote_path, local_path)

    def download_file(self, remote_path, local_path):
        self.logger.info(f"Downloading {remote_path} to {local_path}")
        self._download_file(remote_path, local_path)

    def _download_file(self, remote_path, local_path):
        pass
