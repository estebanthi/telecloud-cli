import cmd
import argparse
from termcolor import colored
import os
import logging

from src.interpreter.modes import MODES
from src.api import Api
from src.filesystems import LocalFileSystem, RemoteFileSystem, FileSystemConnector
import src.interpreter.colors as colors
from src.interpreter.complete_parser import CompleteParser


class Interpreter(cmd.Cmd):

    def __init__(self, api_url, default_mode=MODES.LOCAL):
        cmd.Cmd.__init__(self)
        self.remote_filesystem = None
        self.local_filesystem = None
        self.mode = None
        self.api = None
        self.logger = None
        self.configure(api_url, default_mode)

    def configure(self, api_url, default_mode=MODES.LOCAL):
        self.logger = logging.getLogger('app')
        self.logger.setLevel(logging.INFO)
        self.logger.info(f"Logging level set to {logging.getLevelName(self.logger.level)}")

        self.logger.info(f"Connecting to {api_url}")
        try:
            self.api = Api(api_url)
        except Exception as e:
            self.logger.error(f"Failed to connect to {api_url}")
            self.logger.error(e)
            exit(1)
        self.logger.info(f"Connected to {api_url} - Starting interpreter")

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
        self.cmdloop('\n' + colors.rainbow("Welcome to Telecloud CLI!", randomize=True) + '\n' + 'Type help or ? to list commands.\n')

    def do_exit(self, args):
        return -1

    def help_exit(self):
        print("Exit the interpreter.")

    def do_lg(self, args):
        if self.logger.level == logging.INFO:
            self.logger.info("Logging level will be set to ERROR.")
            self.logger.setLevel(logging.ERROR)
        else:
            self.logger.setLevel(logging.INFO)
            self.logger.info("Logging level set to INFO.")

    def help_lg(self):
        print("Toggle logging level between INFO and ERROR.")

    @update_prompt_decorator
    def do_sw(self, args):
        self.mode = MODES.REMOTE if self.mode == MODES.LOCAL else MODES.LOCAL

    def help_sw(self):
        print("Switch between local and remote mode.")

    def validate_path(self, path, filesystem=None, should_exist=True):
        filesystem = filesystem or self.get_filesystem()

        if should_exist and not filesystem.exists(path):
            self.logger.error(f"Path {path} does not exist.")
            return False
        elif not should_exist and filesystem.exists(path):
            self.logger.error(f"Path {path} already exists.")
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
            self.logger.error(f"Path {path} is not a directory.")
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
            self.logger.error(f"Path {path} is not a file.")
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
            self.logger.error("Tags are only available in remote mode.")
            return False

        return True

    def help_ls(self):
        print("List files and directories.")
        print("Usage: ls [directories] [-t tags] [-re regex] [-r]")
        print("Options:")
        print("  -t, --tags [tags]    Filter by tags.")
        print("  -re, --regex [regex] Filter by regex.")
        print("  -r, --recursive      List recursively.")

    def complete_ls(self, text, line, begidx, endidx):
        last_arg_name, last_arg_value = CompleteParser.parse_line(line)

        if not last_arg_name:
            filesystem = self.get_filesystem()
            return [directory for directory in filesystem.listdir(filesystem.current, files=False) if directory.startswith(text)]

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

    def complete_cd(self, text, line, begidx, endidx):
        filesystem = self.get_filesystem()
        return [directory for directory in filesystem.listdir(filesystem.current, files=False) if directory.startswith(text)]

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

    def complete_rmdir(self, text, line, begidx, endidx):
        filesystem = self.get_filesystem()
        return [directory for directory in filesystem.listdir(filesystem.current, files=False) if directory.startswith(text)]

    def validate_rmdir(self, directory):
        filesystem = self.get_filesystem()

        if not filesystem.isempty(directory):
            self.logger.error(f"Directory {directory} is not empty.")
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

    def complete_rm(self, text, line, begidx, endidx):
        filesystem = self.get_filesystem()
        last_arg_name, last_arg_value = CompleteParser.parse_line(line)

        if not last_arg_name and last_arg_name not in ['-r', '--recursive']:
            return [file for file in filesystem.listdir(filesystem.current, files=True) if file.startswith(text)]
        if not last_arg_name and last_arg_name in ['-r', '--recursive']:
            return [path for path in filesystem.listdir(filesystem.current) if path.startswith(text)]

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

    def complete_mv(self, text, line, begidx, endidx):
        filesystem = self.get_filesystem()
        last_arg_name, last_arg_value = CompleteParser.parse_line(line)

        if not last_arg_name:
            return [path for path in filesystem.listdir(filesystem.current) if path.startswith(text)]

    def validate_mv(self, args):
        filesystem = self.get_filesystem()
        old = args.old
        new = args.new

        old_is_file = filesystem.isfile(old)
        new_is_file = filesystem.isfile(new)

        if not self.validate_path(old, filesystem, should_exist=True):
            return False

        if old_is_file and new_is_file:
            self.logger.error(f"Cannot move a file to another file.")
            return False

        if not old_is_file and new_is_file:
            self.logger.error(f"Cannot move a directory to a file.")
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
        parser.add_argument('tags', nargs='*', help='Tags to be added to the file.', default=[])
        parser.add_argument('-re', '--regex', help='Regex to filter files.')
        parser.add_argument('-r', '--recursive', action='store_true', help='Tag recursively.')
        parser.add_argument('-d', '--directories', nargs='+', help='Directories to tag.', default=[])
        parser.add_argument('-f', '--files', nargs='+', help='Files to tag.', default=[])
        parser.add_argument('-s', '--show', action='store_true', help='Show tags.')
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
        print("  -s, --show           Show tags.")

    def complete_tag(self, text, line, begidx, endidx):
        filesystem = self.get_filesystem()
        last_arg_name, last_arg_value = CompleteParser.parse_line(line)

        if last_arg_name in ['-d', '--directories']:
            return [path for path in filesystem.listdir(filesystem.current, files=False) if path.startswith(last_arg_value)]
        elif last_arg_name in ['-f', '--files']:
            return [file for file in filesystem.listdir(filesystem.current, directories=False) if file.startswith(last_arg_value)]
        elif last_arg_name in ['-s', '--show']:
            return [path for path in filesystem.listdir(filesystem.current, directories=False) if path.startswith(last_arg_value)]

    def validate_tag(self, args):
        files = args.files or []
        directories = args.directories or []

        if self.mode == MODES.LOCAL:
            self.logger.error("Cannot tag files in local mode.")
            return False

        return self.validate_files(files, should_exist=True) and self.validate_directories(directories, should_exist=True)


    def tag(self, args):
        filesystem = self.get_filesystem()

        files = args.files if args.files else []
        directories = args.directories if args.directories else []
        tags = args.tags
        regex = args.regex
        recursive = args.recursive
        show = args.show

        if tags:
            filesystem.tag(files, directories, tags, regex, recursive)

        if show:
            if not files and not directories:
                directories = [filesystem.current]

            to_print = filesystem.get_tags(files, directories, regex, recursive)
            for file in to_print:
                path = filesystem.relative(file[0], filesystem.current)

                tags_color = 'yellow'
                tags = [colored(f"#{tag}", tags_color) for tag in file[1]]
                tags_str = ', '.join(tags)

                print(f"{path}: {colored(tags_str, 'yellow')}")

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

    def complete_untag(self, text, line, begidx, endidx):
        filesystem = self.get_filesystem()
        last_arg_name, last_arg_value = CompleteParser.parse_line(line)

        if last_arg_name in ['-d', '--directories']:
            return [path for path in filesystem.listdir(filesystem.current, files=False) if path.startswith(last_arg_value)]
        elif last_arg_name in ['-f', '--files']:
            return [file for file in filesystem.listdir(filesystem.current, directories=False) if file.startswith(last_arg_value)]

    def validate_untag(self, args):
        files = args.files or []
        directories = args.directories or []

        if self.mode == MODES.LOCAL:
            self.logger.error("Cannot untag files in local mode.")
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

    def complete_upload(self, text, line, begidx, endidx):
        last_arg_name, last_arg_value = CompleteParser.parse_line(line)

        if not last_arg_name:
            local_paths = self.local_filesystem.listdir(self.local_filesystem.current, directories=False)
            return [path for path in local_paths if path.startswith(last_arg_value)]

        if last_arg_name in ['-to', '--to']:
            remote_paths = self.remote_filesystem.listdir(self.remote_filesystem.current, files=False)
            return [path for path in remote_paths if path.startswith(last_arg_value)]

        if last_arg_name in ['-d', '--directories']:
            local_paths = self.local_filesystem.listdir(self.local_filesystem.current, files=False)
            return [path for path in local_paths if path.startswith(last_arg_value)]


    def validate_upload(self, args):
        files = args.files or []
        directories = args.directories or []
        to = args.to or self.remote_filesystem.current

        if not self.validate_files(files, should_exist=True, filesystem=self.local_filesystem):
            return False

        if not self.validate_directories(directories, should_exist=True, filesystem=self.local_filesystem):
            return False

        if not self.remote_filesystem.exists(to):
            self.logger.error("Directory '{}' does not exist.".format(args.to))
            return False

        for file in files:
            if self.remote_filesystem.exists(os.path.join(to, os.path.basename(file))):
                self.logger.error("File '{}' already exists.".format(file))
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
        parser.add_argument('-r', '--recursive', action='store_true', help='Download recursively.')
        parser.add_argument('-re', '--regex', help='Regex to filter files.')
        parser.add_argument('-t', '--tags', nargs='+', help='Filter by tags.')
        args = parser.parse_args(args.split())

        if self.validate_download(args):
            self.download(args)

    def help_download(self):
        print("Download files from the remote server.")
        print("Usage: download [-to directory] [-d directories] [-r] [-re regex] [-t tags] [files]")
        print("Options:")
        print("  -to, --to [directory] Directory to download the files to.")
        print("  -d, --directories      Directories to be downloaded.")
        print("  -r, --recursive        Download recursively.")
        print("  -re, --regex [regex]   Filter by regex.")
        print("  -t, --tags             Filter by tags.")

    def validate_download(self, args):
        files = args.files or []
        directories = args.directories or []
        to = args.to or self.local_filesystem.current

        if not self.validate_files(files, should_exist=True, filesystem=self.remote_filesystem):
            return False

        if not self.validate_directories(directories, should_exist=True, filesystem=self.remote_filesystem):
            return False

        if not self.local_filesystem.exists(to):
            self.logger.error("Directory '{}' does not exist.".format(args.to))
            return False

        for file in files:
            if self.local_filesystem.exists(os.path.join(to, os.path.basename(file))):
                self.logger.error("File '{}' already exists.".format(file))
                return False

        return True

    def download(self, args):
        directories = args.directories if args.directories else []
        files = args.files if args.files else []
        to = args.to or self.local_filesystem.current
        tags = args.tags
        regex = args.regex
        recursive = args.recursive

        filesystem_connector = FileSystemConnector(self.local_filesystem, self.remote_filesystem)
        filesystem_connector.download(files, directories, to, tags, regex, recursive)

    def complete_download(self, text, line, begidx, endidx):
        last_arg_name, last_arg_value = CompleteParser.parse_line(line)

        if not last_arg_name:
            remote_paths = self.remote_filesystem.listdir(self.remote_filesystem.current, directories=False)
            return [path for path in remote_paths if path.startswith(last_arg_value)]

        if last_arg_name in ['-to', '--to']:
            local_paths = self.local_filesystem.listdir(self.local_filesystem.current, files=False)
            return [path for path in local_paths if path.startswith(last_arg_value)]

        if last_arg_name in ['-d', '--directories']:
            remote_paths = self.remote_filesystem.listdir(self.remote_filesystem.current, files=False)
            return [path for path in remote_paths if path.startswith(last_arg_value)]