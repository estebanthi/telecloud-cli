import cmd
import argparse
from termcolor import colored
import os
import shutil
import re
import requests

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
        return f"[ {colored(self.local_dir, 'green') if self.mode == MODES.LOCAL else self.local_dir} | {colored(self.remote_dir, 'green') if self.mode == MODES.REMOTE else self.remote_dir} ]$ "

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

        files = self.api.get_files_meta(tags, directories)

        directories_ = []
        if args.all:
            directories_ = [directory for directory in self.remote_folder_structure]
        else:
            for directory in directories:
                children = utils.get_directory_children(self.remote_folder_structure, directory)
                children = [child.replace(f'{directory}', '', 1) for child in children]  # replacing base path
                children = [child[1:] if child.startswith('/') else child for child in children]  # removing leading '/' if existing
                children = [child.split('/')[0] if '/' in child else child for child in children]  # keep only the first part of the path
                print(children)
                children = utils.remove_dupes(children)
                directories_ += children
            directories_ = utils.remove_dupes(directories)

        entities = []
        for file in files:
            entities.append((file['name'], 'file'))
        for directory in directories_:
            entities.append((directory, 'directory'))

        return entities

    def do_cd(self, args):
        if self.mode == MODES.LOCAL:
            self.local_cd()
        else:
            self.remote_cd()

    def local_cd(self):
        pass

    def remote_cd(self):
        pass


    def do_upload(self, args):
        res = self.commands_controller.upload(args)
        print("Upload successful")

    def do_download(self, args):
        self.commands_controller.download(args)

    def do_rm(self, args):
        self.commands_controller.rm(args)

    def do_tag(self, args):
        self.commands_controller.tag(args)

    def do_untag(self, args):
        self.commands_controller.untag(args)

    def do_tags(self, args):
        res = self.commands_controller.tags(args)
        for tag in res:
            print(tag)