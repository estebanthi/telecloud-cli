import os
import logging


class FileSystemConnector:

    def __init__(self, local_filesystem, remote_filesystem):
        self._local_filesystem = local_filesystem
        self._remote_filesystem = remote_filesystem
        self._logger = logging.getLogger('app')

    def upload(self, files, directories, to, tags, regex, recursive):
        files_from_dirs = self._local_filesystem.get_files(directories=directories, regex=regex, recursive=recursive)
        paths_from_dirs = []
        for file in files_from_dirs:
            parent = None
            for directory in directories:
                if directory in file:
                    parent = self._local_filesystem.format_path(directory)
                    break
            if parent:
                path = self._local_filesystem.relative(file, parent)
                paths_from_dirs.append(os.path.join(self._local_filesystem.basename(parent), path))

        paths_from_dirs = [os.path.join(to, path) for path in paths_from_dirs]

        files_from_files = self._local_filesystem.filter(files, regex=regex)
        paths_from_files = [self._local_filesystem.basename(file) for file in files_from_files]
        paths_from_files = [os.path.join(to, path) for path in paths_from_files]

        local_paths = files_from_dirs + files_from_files
        remote_paths = paths_from_dirs + paths_from_files

        for index, path in enumerate(remote_paths):
            if self._remote_filesystem.exists(path):
                local_paths.pop(index)
                remote_paths.pop(index)
                self._logger.info(f"{path} already exists in remote - Skipped uploading")

        self._remote_filesystem.upload(local_paths, remote_paths, tags)

    def download(self, files, directories, to, tags, regex, recursive):
        files_from_dirs = self._remote_filesystem.get_files(directories=directories, regex=regex, recursive=recursive, tags=tags) if directories else []
        paths_from_dirs = []
        for file in files_from_dirs:
            parent = None
            for directory in directories:
                if directory in file:
                    parent = self._remote_filesystem.format_path(directory)
                    break
            if parent:
                path = self._remote_filesystem.relative(file, parent)
                paths_from_dirs.append(os.path.join(self._remote_filesystem.basename(parent), path))

        paths_from_dirs = [os.path.join(to, path) for path in paths_from_dirs]

        files_from_files = self._remote_filesystem.filter(files, regex=regex)
        paths_from_files = [self._remote_filesystem.basename(file) for file in files_from_files]
        paths_from_files = [os.path.join(to, path) for path in paths_from_files]

        remote_paths = files_from_dirs + files_from_files
        local_paths = paths_from_dirs + paths_from_files

        for index, path in enumerate(local_paths):
            if self._local_filesystem.exists(path):
                remote_paths.pop(index)
                local_paths.pop(index)
                self._logger.info(f"{path} already exists in local - Skipped downloading")

        self._remote_filesystem.download(remote_paths, local_paths)
