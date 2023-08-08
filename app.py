import logging

from src.interpreter import Interpreter


if __name__ == "__main__":
    api_url = "http://localhost:5000"

    logger = logging.Logger('app')
    logger.setLevel(logging.INFO)

    interpreter = Interpreter(api_url)
    interpreter.run()
