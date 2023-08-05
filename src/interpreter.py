import cmd
import argparse
from termcolor import colored
import os
import re
import shutil

from src.modes import MODES
import src.utils as utils
from src.api import Api


class Interpreter(cmd.Cmd):

    def __init__(self, api_url, default_mode=MODES.LOCAL):
        cmd.Cmd.__init__(self)
        self.configure(api_url, default_mode)

    def configure(self, api_url, default_mode=MODES.LOCAL, root_symbol='/'):
        self.api = Api(api_url)

        self.mode = default_mode

        self.local_dir = os.path.expanduser('~')
        self.remote_dir = '/'
        self.remote_folder_structure = self.api.get_remote_folder_structure()
        self.remote_files_structure = self.api.get_remote_files_structure()

        self.prompt = self.get_prompt()

    def get_prompt(self):
        selected_color = 'yellow'
        return f"[ {colored(self.local_dir, selected_color) if self.mode == MODES.LOCAL else self.local_dir} || {colored(self.remote_dir, selected_color) if self.mode == MODES.REMOTE else self.remote_dir} ]$ "

    def update_prompt(self):
        self.prompt = self.get_prompt()

    def update_prompt_decorator(func):
        def wrapper(self, args):
            func(self, args)
            self.update_prompt()
        return wrapper

    def run(self):
        self.cmdloop("\n--- Telecloud CLI - Type help or ? to list commands. ---\n")

    def do_exit(self, args):
        return -1

    @update_prompt_decorator
    def do_sw(self, args):
        self.mode = MODES.REMOTE if self.mode == MODES.LOCAL else MODES.LOCAL

    def help_sw(self):
        print("Switch between local and remote mode.")

    def do_ls(self, args):
        parser = argparse.ArgumentParser()
        parser.add_argument('-t', "--tags", type=str, nargs='+', required=False)
        parser.add_argument('-d', "--directories", type=str, nargs='+', required=False)
        parser.add_argument('-r', "--regex", type=str, required=False)
        parser.add_argument('-a', "--all", action='store_true', required=False)
        args = parser.parse_args(args.split())

        if self.validate_ls(args, self.mode):
            self.ls(args, self.mode)

    def validate_ls(self, args, mode):
        directories = utils.format_paths(self.local_dir if mode == MODES.LOCAL else self.remote_dir, args.directories or [])
        for directory in directories:
            if not utils.path_exists(directory, mode, self.remote_folder_structure):
                print(f"Directory {directory} does not exist.")
                return False
        return True


    def help_ls(self):
        print("List files and directories.")
        print("Usage: ls [-t TAGS] [-d DIRECTORIES] [-r REGEX] [-a]")
        print("If no options are specified, all files and directories in current directory are listed.")
        print("Options:")
        print("  -t, --tags TAGS\t\t\tList files with specified tags.")
        print("  -d, --directories DIRECTORIES\t\tList files and directories in specified directories.")
        print("  -r, --regex REGEX\t\t\tList files and directories with names matching specified regex.")
        print("  -a, --all\t\t\t\tList all files and directories.")
        print("Note: If multiple options are specified, only files and directories that satisfy all options are listed.")

    def ls(self, args, mode):
        entities = self.get_local_entities(args) if mode == MODES.LOCAL else self.get_remote_entities(args)
        entities = utils.remove_dupes(entities)

        regex = args.regex
        if regex:
            entities = [(entity[0], entity[1]) for entity in entities if re.search(regex, entity[0])]

        for entity in entities:
            self.print_entity(entity)

    def print_entity(self, entity):
        if entity[1] == 'directory':
            print(colored(entity[0], 'blue'))
        else:
            print(entity[0])

    def get_local_entities(self, args):
        entities = []

        directories = args.directories or [self.local_dir]
        directories = utils.format_paths(self.local_dir, directories)
        for directory in directories:
            entities.append(self.get_local_directory(directory))

        entities = utils.flatten_list(entities)
        return entities

    def get_local_directory(self, directory):
        entities = []

        for file in os.listdir(directory):
            if os.path.isdir(os.path.join(directory, file)):
                entities.append((file, 'directory'))
            else:
                entities.append((file, 'file'))

        return entities

    def get_remote_entities(self, args):
        tags = args.tags or []
        directories = [] if args.all else (args.directories or [self.remote_dir])
        directories = utils.format_paths(self.remote_dir, directories)

        directories_ids = [self.remote_folder_structure[directory] for directory in directories if directory in self.remote_folder_structure]

        files = self.api.get_files_meta(tags, directories_ids)

        directories_ = []
        if args.all:
            directories_ = [directory for directory in self.remote_folder_structure]
        else:
            for directory in directories:
                children = utils.get_directory_children(self.remote_folder_structure, directory)
                children = [child.replace(f'{directory}', '', 1) for child in children]  # replacing base path
                children = [child[1:] if child.startswith('/') else child for child in children]  # removing leading '/' if existing
                children = [child.split('/')[0] if '/' in child else child for child in children]  # keep only the first part of the path
                children = utils.remove_dupes(children)
                directories_ += children
            directories_ = utils.remove_dupes(directories_)

        entities = []
        for file in files:
            entities.append((file['name'], 'file'))
        for directory in directories_:
            entities.append((directory, 'directory'))

        return entities

    @update_prompt_decorator
    def do_cd(self, directory):
        current_path = self.local_dir if self.mode == MODES.LOCAL else self.remote_dir
        new_directory = utils.format_path(current_path, directory)
        if self.validate_cd(new_directory):
            self.local_dir = new_directory if self.mode == MODES.LOCAL else self.local_dir
            self.remote_dir = new_directory if self.mode == MODES.REMOTE else self.remote_dir

    def help_cd(self):
        print("Change directory.")
        print("Usage: cd DIRECTORY")
        print("Note: DIRECTORY can be either absolute or relative path.")

    def validate_cd(self, directory):
        if utils.path_exists(directory, self.mode, self.remote_folder_structure):
            return True
        print(f"Directory {directory} does not exist.")

    def do_mkdir(self, directory):
        directory = utils.format_path(self.local_dir if self.mode == MODES.LOCAL else self.remote_dir, directory)
        if self.validate_mkdir(directory):
            self.mkdir(directory)

    def help_mkdir(self):
        print("Create directory.")
        print("Usage: mkdir DIRECTORY")
        print("Note: DIRECTORY can be either absolute or relative path.")

    def validate_mkdir(self, directory):
        if utils.path_exists(directory, self.mode, self.remote_folder_structure):
            print(f"Directory {directory} already exists.")
            return False
        return True

    def mkdir(self, directory):
        if self.mode == MODES.LOCAL:
            os.mkdir(directory)
        else:
            directory_parent = utils.get_directory_parent(directory)
            if directory_parent not in self.remote_folder_structure:
                print(f"Parent directory {directory_parent} does not exist.")
                return

            parent_id = self.remote_folder_structure[directory_parent]
            directory_name = directory.split('/')[-1]
            self.api.create_directory(directory_name, parent_id)
            self.remote_folder_structure = self.api.get_remote_folder_structure()

    def do_rmdir(self, directory):
        directory = utils.format_path(self.local_dir if self.mode == MODES.LOCAL else self.remote_dir, directory)
        if self.validate_rmdir(directory):
            self.rmdir(directory)

    def help_rmdir(self):
        print("Remove directory.")
        print("Usage: rmdir DIRECTORY")
        print("Note: DIRECTORY can be either absolute or relative path.")

    def validate_rmdir(self, directory):
        if not utils.path_exists(directory, self.mode, self.remote_folder_structure):
            print(f"Directory {directory} does not exist.")
            return False
        return True

    def rmdir(self, directory):
        if self.mode == MODES.LOCAL:
            shutil.rmtree(directory)
        else:
            directory_id = self.remote_folder_structure[directory]
            self.api.delete_directory(directory_id)
            self.remote_folder_structure = self.api.get_remote_folder_structure()

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

