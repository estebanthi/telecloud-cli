import os
import re
import shutil

from src.filesystems.FileSystem import FileSystem


class LocalFileSystem(FileSystem):

    def __init__(self, root_path=os.path.expanduser("~")):
        super().__init__(root_path)

    def get_files(self, directories, regex=None, recursive=False, tags=None):
        directories = self.format_paths(directories)

        files = []
        for directory in directories:
            list_paths = self.listdir(directory)
            for path in list_paths:
                if self.isfile(os.path.join(directory, path)):
                    files.append(os.path.join(directory, path))

                if recursive and os.path.isdir(os.path.join(directory, path)):
                    files += self.get_files([os.path.join(directory, path)], regex, recursive, tags)

        if regex:
            files = self.filter(files, regex)

        return files

    def get_directories(self, directories, regex=None, recursive=False):
        directories = self.format_paths(directories)

        directories_ = []
        for directory in directories:
            list_paths = self.listdir(directory)
            for path in list_paths:
                if self.isdir(os.path.join(directory, path)):
                    directories_.append(os.path.join(directory, path))

                if recursive and os.path.isdir(os.path.join(directory, path)):
                    directories_ += self.get_directories([os.path.join(directory, path)], regex, recursive)

        if regex:
            directories_ = self.filter(directories_, regex)

        return directories_

    def exists(self, path):
        path = self.format_path(path)
        return os.path.exists(path)

    def listdir(self, path):
        path = self.format_path(path)
        return os.listdir(path)

    def basename(self, path):
        path = self.format_path(path)
        return os.path.basename(path)

    def isfile(self, path):
        path = self.format_path(path)
        return os.path.isfile(path)

    def isdir(self, path):
        path = self.format_path(path)
        return os.path.isdir(path)

    def children(self, path, files=True, directories=True, n=-1):
        path = self.format_path(path)

        if n == -1:
            n = float('inf')

        children = []
        if files:
            if os.path.isdir(path):
                children += [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        if directories:
            if os.path.isdir(path):
                children += [os.path.join(path, d) for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
        if n > 0:
            for child in children:
                children += self.children(child, files, directories, n-1)
        return children

    def mkdir(self, path):
        path = self.format_path(path)
        os.mkdir(path)

    def rmdir(self, path):
        path = self.format_path(path)
        os.rmdir(path)

    def remove(self, path):
        path = self.format_path(path)
        os.remove(path)

    def mv(self, src, dst):
        src = self.format_path(src)
        dst = self.format_path(dst)
        shutil.move(src, dst)