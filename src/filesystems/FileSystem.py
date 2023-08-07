import re
from abc import ABC, abstractmethod
import os


class FileSystem(ABC):

    def __init__(self, root):
        self._root = root
        self._current = root

    @property
    def root(self):
        return self._root

    @property
    def current(self):
        return self._current

    @current.setter
    def current(self, path):
        self._current = path

    @abstractmethod
    def listdir(self, path):
        pass

    @abstractmethod
    def basename(self, path):
        pass

    @abstractmethod
    def isfile(self, path):
        pass

    @abstractmethod
    def isdir(self, path):
        pass

    @abstractmethod
    def children(self, path, files=True, directories=True, n=0):
        pass

    def parent(self, path):
        return os.path.dirname(path)

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

    @abstractmethod
    def exists(self, path):
        pass

    def filter(self, paths, regex):
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