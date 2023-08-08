import cmd
import argparse
from termcolor import colored
import os
import re
import shutil

from src.modes import MODES
from src.api import Api
from src.filesystems import LocalFileSystem, RemoteFileSystem, FileSystemConnector


class Interpreter(cmd.Cmd):

    def __init__(self, api_url, default_mode=MODES.LOCAL):
        cmd.Cmd.__init__(self)
        self.remote_filesystem = None
        self.local_filesystem = None
        self.mode = None
        self.api = None
        self.configure(api_url, default_mode)

    def configure(self, api_url, default_mode=MODES.LOCAL):
        self.api = Api(api_url)

        self.mode = default_mode

        self.local_filesystem = LocalFileSystem()
        self.remote_filesystem = RemoteFileSystem()

        self.prompt = self.get_prompt()

    def get_prompt(self):
        selected_color = 'yellow'
        return f"[ {colored(self.local_filesystem.current, selected_color) if self.mode == MODES.LOCAL else self.local_filesystem.current} || {colored(self.remote_filesystem.current, selected_color) if self.mode == MODES.REMOTE else self.remote_filesystem.current} ]$ "

    def update_prompt(self):
        self.prompt = self.get_prompt()

    def update_prompt_decorator(func):
        def wrapper(self, args):
            func(self, args)
            self.update_prompt()
        return wrapper

    def get_filesystem(self):
        return self.local_filesystem if self.mode == MODES.LOCAL else self.remote_filesystem

    def run(self):
        self.cmdloop("\n--- Telecloud CLI - Type help or ? to list commands. ---\n")

    def do_exit(self, args):
        return -1

    @update_prompt_decorator
    def do_sw(self, args):
        self.mode = MODES.REMOTE if self.mode == MODES.LOCAL else MODES.LOCAL

    def help_sw(self):
        print("Switch between local and remote mode.")

    def validate_path(self, path, filesystem=None, should_exist=True):
        filesystem = filesystem or self.get_filesystem()

        if should_exist and not filesystem.exists(path):
            print(f"Path {path} does not exist.")
            return False
        elif not should_exist and filesystem.exists(path):
            print(f"Path {path} already exists.")
            return False
        return True

    def validate_paths(self, paths, filesystem=None, should_exist=True):
        for path in paths:
            if not self.validate_path(path, filesystem, should_exist):
                return False
        return True

    def validate_directory(self, path, filesystem=None, should_exist=True):
        filesystem = filesystem or self.get_filesystem()

        if not self.validate_path(path, filesystem, should_exist):
            return False

        if not filesystem.isdir(path):
            print(f"Path {path} is not a directory.")
            return False
        return True

    def validate_directories(self, paths, filesystem=None, should_exist=True):
        for path in paths:
            if not self.validate_directory(path, filesystem, should_exist):
                return False
        return True

    def validate_file(self, path, filesystem=None, should_exist=True):
        filesystem = filesystem or self.get_filesystem()

        if not self.validate_path(path, filesystem, should_exist):
            return False

        if not filesystem.isfile(path):
            print(f"Path {path} is not a file.")
            return False
        return True

    def validate_files(self, paths, filesystem=None, should_exist=True):
        for path in paths:
            if not self.validate_file(path, filesystem, should_exist):
                return False
        return True

    def do_ls(self, args):
        parser = argparse.ArgumentParser()
        parser.add_argument('directories', type=str, nargs='*')
        parser.add_argument('-t', "--tags", type=str, nargs='+', required=False)
        parser.add_argument('-re', "--regex", type=str, required=False)
        parser.add_argument('-r', '--recursive', action='store_true', required=False)
        args = parser.parse_args(args.split())

        if self.validate_ls(args):
            self.ls(args)

    def validate_ls(self, args):
        filesystem = self.get_filesystem()
        directories = args.directories or [filesystem.current]

        if not self.validate_directories(directories, filesystem):
            return False

        if args.tags and self.mode == MODES.LOCAL:
            print("Tags are only available in remote mode.")
            return False

        return True

    def help_ls(self):
        print("List files and directories.")
        print("Usage: ls [directories] [-t tags] [-re regex] [-r]")
        print("Options:")
        print("  -t, --tags [tags]    Filter by tags.")
        print("  -re, --regex [regex] Filter by regex.")
        print("  -r, --recursive      List recursively.")

    def ls(self, args):
        filesystem = self.get_filesystem()

        tags = args.tags or []
        directories = args.directories or [filesystem.current]
        regex = args.regex or None
        recursive = args.recursive or False

        files = filesystem.get_files(directories, regex, recursive, tags)
        directories_ = filesystem.get_directories(directories, regex, recursive)

        filenames = [filesystem.basename(file) for file in files]
        directory_names = [filesystem.basename(directory) for directory in directories_]

        for filename in filenames:
            self.print_file(filename)

        if not args.tags:
            for directory_name in directory_names:
                self.print_directory(directory_name)

    def print_file(self, file):
        print(file)

    def print_directory(self, directory):
        print(colored(directory, 'blue'))

    @update_prompt_decorator
    def do_cd(self, directory):
        if self.validate_cd(directory):
            self.cd(directory)

    def help_cd(self):
        print("Change directory.")
        print("Usage: cd DIRECTORY")

    def validate_cd(self, directory):
        filesystem = self.get_filesystem()
        return self.validate_directory(directory, filesystem, should_exist=True)

    def cd(self, directory):
        filesystem = self.get_filesystem()
        filesystem.current = directory

    def do_mkdir(self, directory):
        if self.validate_mkdir(directory):
            self.mkdir(directory)

    def help_mkdir(self):
        print("Create directory.")
        print("Usage: mkdir DIRECTORY")

    def validate_mkdir(self, directory):
        return self.validate_path(directory, should_exist=False)

    def mkdir(self, directory):
        filesystem = self.get_filesystem()
        filesystem.mkdir(directory)

    def do_rmdir(self, directory):
        if self.validate_rmdir(directory):
            self.rmdir(directory)

    def help_rmdir(self):
        print("Remove directory.")
        print("Usage: rmdir DIRECTORY")

    def validate_rmdir(self, directory):
        filesystem = self.get_filesystem()

        if not filesystem.isempty(directory):
            print(f"Directory {directory} is not empty.")
            return False

        return self.validate_directory(directory, filesystem, should_exist=True)

    def rmdir(self, directory):
        filesystem = self.get_filesystem()
        filesystem.rmdir(directory)


    def do_rm(self, args):
        parser = argparse.ArgumentParser()
        parser.add_argument('files', nargs='+', help='Files to be removed.')
        parser.add_argument('-r', '--recursive', action='store_true', help='Remove recursively.')
        parser.add_argument('-re', '--regex', help='Regex to filter files.')
        args = parser.parse_args(args.split())

        if self.validate_rm(args):
            self.rm(args)

    def help_rm(self):
        print("Remove files.")
        print("Usage: rm FILES [-r] [-re regex]")
        print("Options:")
        print("  -r, --recursive      Remove recursively.")
        print("  -re, --regex [regex] Filter by regex.")

    def validate_rm(self, args):
        filesystem = self.get_filesystem()
        files = args.files
        recursive = args.recursive

        if recursive and not self.validate_paths(files, filesystem, should_exist=True):
            return False
        elif not recursive and not self.validate_files(files, filesystem, should_exist=True):
            return False

        return True

    def rm(self, args):
        filesystem = self.get_filesystem()
        files = args.files
        recursive = args.recursive
        regex = args.regex

        filesystem.rm(files, recursive, regex)

    def do_mv(self, args):
        parser = argparse.ArgumentParser()
        parser.add_argument('old', help='Old file path.')
        parser.add_argument('new', help='New file path.')
        args = parser.parse_args(args.split())

        if self.validate_mv(args):
            self.mv(args)

    def help_mv(self):
        print("Move a file.")
        print("Usage: mv OLD NEW")

    def validate_mv(self, args):
        filesystem = self.get_filesystem()
        old = args.old
        new = args.new

        old_is_file = filesystem.isfile(old)
        new_is_file = filesystem.isfile(new)

        if not self.validate_path(old, filesystem, should_exist=True):
            return False

        if old_is_file and new_is_file:
            print(f"Cannot move a file to another file.")
            return False

        if not old_is_file and new_is_file:
            print(f"Cannot move a directory to a file.")
            return False

        if not new_is_file:
            basename = filesystem.basename(old)
            new = filesystem.join(new, basename)
            if not self.validate_path(new, filesystem, should_exist=False):
                return False

        return True

    def mv(self, args):
        filesystem = self.get_filesystem()
        old = args.old
        new = args.new

        filesystem.mv(old, new)

    def do_tag(self, args):
        parser = argparse.ArgumentParser()
        parser.add_argument('tags', nargs='+', help='Tags to be added to the file.', default=[])
        parser.add_argument('-re', '--regex', help='Regex to filter files.')
        parser.add_argument('-r', '--recursive', action='store_true', help='Tag recursively.')
        parser.add_argument('-d', '--directories', nargs='+', help='Directories to tag.', default=[])
        parser.add_argument('-f', '--files', nargs='+', help='Files to tag.', default=[])
        args = parser.parse_args(args.split())

        if self.validate_tag(args):
            self.tag(args)

    def help_tag(self):
        print("Add tags to files.")
        print("Usage: tag TAGS [-re regex] [-d directories] [-f files]")
        print("Options:")
        print("  -re, --regex [regex] Filter by regex.")
        print("  -r, --recursive      Tag recursively.")
        print("  -d, --directories    Directories to tag.")
        print("  -f, --files          Files to tag.")

    def validate_tag(self, args):
        files = args.files or []
        directories = args.directories or []

        if self.mode == MODES.LOCAL:
            print("Cannot tag files in local mode.")
            return False

        return self.validate_files(files, should_exist=True) and self.validate_directories(directories, should_exist=True)


    def tag(self, args):
        filesystem = self.get_filesystem()

        files = args.files if args.files else []
        directories = args.directories if args.directories else []
        tags = args.tags
        regex = args.regex
        recursive = args.recursive

        filesystem.tag(files, directories, tags, regex, recursive)

    def do_untag(self, args):
        parser = argparse.ArgumentParser()
        parser.add_argument('tags', nargs='+', help='Tags to be removed from the file.', default=[])
        parser.add_argument('-re', '--regex', help='Regex to filter files.')
        parser.add_argument('-r', '--recursive', action='store_true', help='Untag recursively.')
        parser.add_argument('-d', '--directories', nargs='+', help='Directories to untag.', default=[])
        parser.add_argument('-f', '--files', nargs='+', help='Files to untag.', default=[])
        args = parser.parse_args(args.split())

        if self.validate_untag(args):
            self.untag(args)

    def help_untag(self):
        print("Remove tags from files.")
        print("Usage: untag TAGS [-re regex] [-d directories] [-f files]")
        print("Options:")
        print("  -re, --regex [regex] Filter by regex.")
        print("  -r, --recursive      Untag recursively.")
        print("  -d, --directories    Directories to untag.")
        print("  -f, --files          Files to untag.")

    def validate_untag(self, args):
        files = args.files or []
        directories = args.directories or []

        if self.mode == MODES.LOCAL:
            print("Cannot untag files in local mode.")
            return False

        return self.validate_files(files, should_exist=True) and self.validate_directories(directories, should_exist=True)

    def untag(self, args):
        filesystem = self.get_filesystem()

        files = args.files if args.files else []
        directories = args.directories if args.directories else []
        tags = args.tags
        regex = args.regex
        recursive = args.recursive

        filesystem.untag(files, directories, tags, regex, recursive)

    def do_upload(self, args):
        parser = argparse.ArgumentParser()
        parser.add_argument('files', nargs='*', help='Files to be uploaded.')
        parser.add_argument('-to', '--to', help='Directory to upload the files to.')
        parser.add_argument('-d', '--directories', nargs='+', help='Directories to be uploaded.', default=[])
        parser.add_argument('-r', '--recursive', action='store_true', help='Upload recursively.')
        parser.add_argument('-t', '--tags', nargs='+', help='Tags to be added to the files.', default=[])
        parser.add_argument('-re', '--regex', help='Regex to filter files.')
        args = parser.parse_args(args.split())

        if self.validate_upload(args):
            self.upload(args)

    def help_upload(self):
        print("Upload files to the remote server.")
        print("Usage: upload [-to directory] [-d directories] [-r] [-t tags] [-re regex] [files]")
        print("Options:")
        print("  -to, --to [directory] Directory to upload the files to.")
        print("  -d, --directories      Directories to be uploaded.")
        print("  -r, --recursive        Upload recursively.")
        print("  -t, --tags             Tags to be added to the files.")
        print("  -re, --regex [regex]   Filter by regex.")

    def validate_upload(self, args):
        files = args.files or []
        directories = args.directories or []
        to = args.to or self.remote_filesystem.current

        if not self.validate_files(files, should_exist=True, filesystem=self.local_filesystem):
            return False

        if not self.validate_directories(directories, should_exist=True, filesystem=self.local_filesystem):
            return False

        if not self.remote_filesystem.exists(to):
            print("Directory '{}' does not exist.".format(args.to))
            return False

        for file in files:
            if self.remote_filesystem.exists(os.path.join(to, os.path.basename(file))):
                print("File '{}' already exists.".format(file))
                return False

        return True

    def upload(self, args):
        directories = args.directories if args.directories else []
        files = args.files if args.files else []
        to = args.to or self.remote_filesystem.current
        tags = args.tags
        regex = args.regex
        recursive = args.recursive

        filesystem_connector = FileSystemConnector(self.local_filesystem, self.remote_filesystem)
        filesystem_connector.upload(files, directories, to, tags, regex, recursive)

    def do_download(self, args):
        parser = argparse.ArgumentParser()
        parser.add_argument('files', nargs='*', help='Files to be downloaded.')
        parser.add_argument('-to', '--to', help='Directory to download the files to.')
        parser.add_argument('-d', '--directories', nargs='+', help='Directories to be downloaded.', default=[])
        parser.add_argument('-r', '--regex', help='Regex to filter files.')
        args = parser.parse_args(args.split())

        if self.validate_download(args):
            self.download(args)

    def help_download(self):
        print("Download files.")
        print("Usage: download [OPTIONS] FILES")
        print("Note: FILES are the files to be downloaded.")
        print("Options:")
        print("  -d, --directories TEXT  Directories to be downloaded.")
        print("  -r, --regex TEXT        Regex to filter files.")

    def validate_download(self, args):
        if args.directories:
            args.directories = utils.format_paths(self.remote_dir, args.directories)
            for directory in args.directories:
                if not utils.path_exists(directory, MODES.REMOTE, self.remote_folder_structure):
                    print(f"Directory {directory} does not exist.")
                    return False
        if args.files:
            args.files = utils.format_paths(self.remote_dir, args.files)
            for file in args.files:
                if not utils.path_exists(file, MODES.REMOTE, self.remote_files_structure):
                    print(f"File {file} does not exist.")
                    return False
                if utils.path_exists(file, MODES.LOCAL, self.remote_files_structure):
                    print(f"File {file} already exists in the local.")
                    return False
        if args.to:
            args.to = utils.format_path(self.local_dir, args.to)
            if not utils.path_exists(args.to, MODES.LOCAL, self.remote_folder_structure):
                print(f"Directory {args.to} does not exist in the local.")
                return False
        return True

    def download(self, args):
        directories = args.directories if args.directories else []
        files = args.files if args.files else []
        to = args.to if args.to else self.local_dir
        regex = args.regex

        directories = utils.format_paths(self.remote_dir, directories)
        files = utils.format_paths(self.remote_dir, files)

        for directory in directories:
            files_to_download = [file for file in self.remote_files_structure if file.startswith(directory)]
            files.extend(files_to_download)

        if regex:
            files = [file for file in files if re.search(regex, file[0])]

        files = [self.remote_files_structure[file] for file in files]
        for file in files:
            self.api.download(file, to)
