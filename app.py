from src.interpreter import Interpreter
from src.commands_controller import CommandsController


if __name__ == "__main__":
    api_url = "http://localhost:5000"
    interpreter = Interpreter(api_url)
    interpreter.run()
