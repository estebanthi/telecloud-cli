import cmd
import argparse
from termcolor import colored
import os
import re
import shutil

from src.modes import MODES
import src.utils as utils
from src.api import Api
from src.filesystems import LocalFileSystem, RemoteFileSystem


class Interpreter(cmd.Cmd):

    def __init__(self, api_url, default_mode=MODES.LOCAL):
        cmd.Cmd.__init__(self)
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
        filesystem = self.get_filesystem()
        parent = filesystem.parent(directory)
        return self.validate_path(directory, filesystem, should_exist=False) and self.validate_path(parent, filesystem, should_exist=True)

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

        if not filesystem.is_empty(directory):
            print(f"Directory {directory} is not empty.")
            return False

        return self.validate_directory(directory, filesystem, should_exist=True)

    def rmdir(self, directory):
        filesystem = self.get_filesystem()
        filesystem.rmdir(directory)

    def do_tag(self, args):
        parser = argparse.ArgumentParser()
        parser.add_argument('tags', nargs='+', help='Tags to be added to the file.', default=[])
        parser.add_argument('-r', '--regex', help='Regex to filter files.')
        parser.add_argument('-d', '--directories', nargs='+', help='Directories to be searched.', default=[])
        parser.add_argument('-f', '--files', nargs='+', help='Files to be searched.', default=[])
        args = parser.parse_args(args.split())

        if self.validate_tags(args):
            self.tag(args)

    def help_tag(self):
        print("Add tags to files.")
        print("Usage: tag [OPTIONS] TAGS")
        print("Note: TAGS are the tags to be added to the file.")
        print("Options:")
        print("  -r, --regex TEXT        Regex to filter files.")
        print("  -d, --directories TEXT  Directories to be searched.")
        print("  -f, --files TEXT        Files to be searched.")

    def validate_tags(self, args):
        if self.mode == MODES.LOCAL:
            print("Cannot tag files in local mode.")
            return False
        if args.directories:
            args.directories = utils.format_paths(self.remote_dir, args.directories)
            for directory in args.directories:
                if not utils.path_exists(directory, self.mode, self.remote_folder_structure):
                    print(f"Directory {directory} does not exist.")
                    return False
        if args.files:
            args.files = utils.format_paths(self.remote_dir, args.files)
            for file in args.files:
                if not utils.path_exists(file, self.mode, self.remote_folder_structure):
                    print(f"File {file} does not exist.")
                    return False
        return True

    def tag(self, args):
        directories = args.directories if args.directories else [self.remote_dir]
        files = args.files if args.files else []
        tags = args.tags
        regex = args.regex

        directories = utils.format_paths(self.remote_dir, directories)
        files = utils.format_paths(self.remote_dir, files)

        for directory in directories:
            files += utils.get_directory_children(self.remote_files_structure, directory)
        files = utils.remove_dupes(files)

        if regex:
            files = [file for file in files if re.search(regex, file)]

        for file in files:
            file_id = self.remote_files_structure[file]
            self.api.add_tags(file_id, tags)


    def do_untag(self, args):
        parser = argparse.ArgumentParser()
        parser.add_argument('tags', nargs='+', help='Tags to be removed from the file.', default=[])
        parser.add_argument('-r', '--regex', help='Regex to filter files.')
        parser.add_argument('-d', '--directories', nargs='+', help='Directories to be searched.', default=[])
        parser.add_argument('-f', '--files', nargs='+', help='Files to be searched.', default=[])
        args = parser.parse_args(args.split())

        if self.validate_untag(args):
            self.untag(args)

    def help_untag(self):
        print("Remove tags from files.")
        print("Usage: untag [OPTIONS] TAGS")
        print("Note: TAGS are the tags to be removed from the file.")
        print("Options:")
        print("  -r, --regex TEXT        Regex to filter files.")
        print("  -d, --directories TEXT  Directories to be searched.")
        print("  -f, --files TEXT        Files to be searched.")

    def validate_untag(self, args):
        if self.mode == MODES.LOCAL:
            print("Cannot untag files in local mode.")
            return False
        if args.directories:
            args.directories = utils.format_paths(self.remote_dir, args.directories)
            for directory in args.directories:
                if not utils.path_exists(directory, self.mode, self.remote_folder_structure):
                    print(f"Directory {directory} does not exist.")
                    return False
        if args.files:
            args.files = utils.format_paths(self.remote_dir, args.files)
            for file in args.files:
                if not utils.path_exists(file, self.mode, self.remote_folder_structure):
                    print(f"File {file} does not exist.")
                    return False
        return True

    def untag(self, args):
        directories = args.directories if args.directories else [self.remote_dir]
        files = args.files if args.files else []
        tags = args.tags
        regex = args.regex

        directories = utils.format_paths(self.remote_dir, directories)
        files = utils.format_paths(self.remote_dir, files)

        for directory in directories:
            files += utils.get_directory_children(self.remote_files_structure, directory)
        files = utils.remove_dupes(files)

        if regex:
            files = [file for file in files if re.search(regex, file)]

        for file in files:
            file_id = self.remote_files_structure[file]
            self.api.remove_tags(file_id, tags)


    def do_mv(self, args):
        parser = argparse.ArgumentParser()
        parser.add_argument('old', help='Old file path.')
        parser.add_argument('new', help='New file path.')
        args = parser.parse_args(args.split())

        old = utils.format_path(self.local_dir if self.mode == MODES.LOCAL else self.remote_dir, args.old)
        new = utils.format_path(self.local_dir if self.mode == MODES.LOCAL else self.remote_dir, args.new)

        if self.validate_mv(old, new):
            self.mv(old, new)

    def help_mv(self):
        print("Move a file.")
        print("Usage: mv OLD NEW")
        print("Note: OLD is the old path and NEW is the new path.")

    def validate_mv(self, old, new):
        structure = self.remote_files_structure | self.remote_folder_structure
        if not utils.path_exists(old, self.mode, structure):
            print(f"{old} does not exist.")
            return False
        if utils.path_exists(new, self.mode, structure):
            print(f"{new} already exists.")
            return False
        return True

    def mv(self, old, new):
        if self.mode == MODES.LOCAL:
            os.rename(old, new)
        else:
            structure = self.remote_files_structure | self.remote_folder_structure
            id_ = structure[old]

            is_rename = old.split('/')[-1] != new.split('/')[-1]
            if is_rename:
                self.api.rename(id_, new.split('/')[-1])

            is_move = old.split('/')[:-1] != new.split('/')[:-1]
            if is_move:
                new_parent = '/'.join(new.split('/')[:-1])
                if new_parent == '':
                    new_parent = '/'
                new_parent_id = structure[new_parent]
                self.api.move(id_, new_parent_id)

            self.remote_files_structure = self.api.get_remote_files_structure()
            self.remote_folder_structure = self.api.get_remote_folder_structure()

    def do_upload(self, args):
        parser = argparse.ArgumentParser()
        parser.add_argument('files', nargs='*', help='Files to be uploaded.')
        parser.add_argument('-to', '--to', help='Directory to upload the files to.')
        parser.add_argument('-d', '--directories', nargs='+', help='Directories to be uploaded.', default=[])
        parser.add_argument('-t', '--tags', nargs='+', help='Tags to be added to the files.', default=[])
        parser.add_argument('-r', '--regex', help='Regex to filter files.')
        args = parser.parse_args(args.split())

        if self.validate_upload(args):
            self.upload(args)

    def help_upload(self):
        print("Upload files.")
        print("Usage: upload [OPTIONS] FILES")
        print("Note: FILES are the files to be uploaded.")
        print("Options:")
        print("  -d, --directories TEXT  Directories to be uploaded.")
        print("  -t, --tags TEXT         Tags to be added to the files.")
        print("  -r, --regex TEXT        Regex to filter files.")

    def validate_upload(self, args):
        if args.directories:
            args.directories = utils.format_paths(self.local_dir, args.directories)
            for directory in args.directories:
                if not utils.path_exists(directory, MODES.LOCAL, self.remote_folder_structure):
                    print(f"Directory {directory} does not exist.")
                    return False
        if args.files:
            args.files = utils.format_paths(self.local_dir, args.files)
            for file in args.files:
                if not utils.path_exists(file, MODES.LOCAL, self.remote_folder_structure):
                    print(f"File {file} does not exist.")
                    return False
        if args.to:
            args.to = utils.format_path(self.remote_dir, args.to)
            if not utils.path_exists(args.to, MODES.REMOTE, self.remote_folder_structure):
                print(f"Directory {args.to} does not exist in the remote.")
                return False
        return True

    def upload(self, args):
        directories = args.directories if args.directories else []
        files = args.files if args.files else []
        to = self.remote_folder_structure[args.to if args.to else self.remote_dir]
        tags = args.tags
        regex = args.regex

        directories = utils.format_paths(self.local_dir, directories)
        files = utils.format_paths(self.local_dir, files)

        for directory in directories:
            for root, dirs, files_ in os.walk(directory):
                for file in files_:
                    path = os.path.join(root, file)
                    files.append(path)

        if regex:
            files = [file for file in files if re.search(regex, file)]

        for file in files:
            self.api.upload(file, to, tags)

        self.remote_files_structure = self.api.get_remote_files_structure()
        self.remote_folder_structure = self.api.get_remote_folder_structure()

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

    def do_rm(self, args):
        parser = argparse.ArgumentParser()
        parser.add_argument('files', nargs='+', help='Files to be removed.')
        parser.add_argument('-r', '--regex', help='Regex to filter files.')
        args = parser.parse_args(args.split())

        if self.validate_rm(args):
            self.rm(args)

    def help_rm(self):
        print("Remove files.")
        print("Usage: rm [OPTIONS] FILES")
        print("Note: FILES are the files to be removed.")
        print("Options:")
        print("  -d, --directories TEXT  Directories to be removed.")
        print("  -r, --regex TEXT        Regex to filter files.")

    def validate_rm(self, args):
        args.files = utils.format_paths(self.local_dir if self.mode == MODES.LOCAL else self.remote_dir, args.files)
        for file in args.files:
            if not utils.path_exists(file, self.mode, self.remote_files_structure):
                print(f"File {file} does not exist.")
                return False
        return True

    def rm(self, args):
        if self.mode == MODES.LOCAL:
            for file in args.files:
                os.remove(file)
        else:
            files = args.files
            regex = args.regex

            files = utils.format_paths(self.local_dir if self.mode == MODES.LOCAL else self.remote_dir, files)

            if regex:
                files = [file for file in files if re.search(regex, file)]

            for file in files:
                file_id = self.remote_files_structure[file]
                self.api.rm(file_id)

            self.remote_files_structure = self.api.get_remote_files_structure()
            self.remote_folder_structure = self.api.get_remote_folder_structure()

