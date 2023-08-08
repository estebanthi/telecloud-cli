import os


class FileSystemConnector:

    def __init__(self, local_filesystem, remote_filesystem):
        self._local_filesystem = local_filesystem
        self._remote_filesystem = remote_filesystem

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

        self._remote_filesystem.upload(local_paths, remote_paths, tags, regex)
