from termcolor import colored
import random


def rainbow(text, randomize=False):
    colors = ['red', 'yellow', 'green', 'cyan', 'blue', 'magenta']
    colored_text = ''
    for i, char in enumerate(text):
        color = colors[i % len(colors)] if not randomize else random.choice(colors)
        colored_text += colored(char, color)
    return colored_text


def blue_nuances(text, randomize=False):
    colors = ['blue', 'cyan', 'magenta']
    colored_text = ''
    for i, char in enumerate(text):
        color = colors[i % len(colors)] if not randomize else random.choice(colors)
        colored_text += colored(char, color)
    return colored_text


def light_theme(text, randomize=False):
    colors = ['white', 'yellow']
    colored_text = ''
    for i, char in enumerate(text):
        color = colors[i % len(colors)] if not randomize else random.choice(colors)
        colored_text += colored(char, color)
    return colored_text


def bold(text: str) -> str:
    return colored(text, attrs=['bold'])


def underline(text: str) -> str:
    return colored(text, attrs=['underline'])

