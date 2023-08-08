from src.interpreter import Interpreter
from src.logger import Logger


if __name__ == "__main__":
    api_url = "http://localhost:5000"
    logger = Logger()

    interpreter = Interpreter(api_url)
    interpreter.run()
