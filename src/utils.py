import os
from src.modes import MODES


def format_url(url, query):
    if query:
        url += "?"
        for key, value in query.items():
            if value:
                if type(value) == list:
                    for v in value:
                        url += f"{key}={v}&"
                else:
                    url += f"{key}={value}&"
        url = url[:-1]
    return url


def format_paths(cur_path, paths):
    return [format_path(cur_path, path) for path in paths]


def format_path(cur_path, path):
    if path == '.':
        return cur_path
    if path == '..':
        return os.path.dirname(cur_path)
    if path == '~':
        return os.path.expanduser('~')
    path = path if path.startswith('/') else os.path.join(cur_path, path)
    path = path[:-1] if path.endswith('/') and len(path) > 1 else path
    return os.path.normpath(path)


def path_exists(path, mode, remote_path_structure):
    if mode == MODES.LOCAL:
        return os.path.exists(path)
    return path in remote_path_structure


def get_directory_children(file_structure, path):
    return [dir_path for dir_path in file_structure if dir_path.startswith(path) and dir_path != path]


def get_directory_parent(path):
    return os.path.dirname(path)


def flatten_list(l):
    return [item for sublist in l for item in sublist]

def remove_dupes(l):
    return list(set(l))
