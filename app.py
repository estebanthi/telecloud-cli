from yaml import safe_load

from src.interpreter import Interpreter
from src.logger import Logger


if __name__ == "__main__":
    with open('config.yaml', 'r') as f:
        config = safe_load(f)

    api_url = config['api_url']
    logger = Logger()

    interpreter = Interpreter(api_url)
    interpreter.run()
