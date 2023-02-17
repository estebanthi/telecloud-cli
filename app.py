from interpreter import Interpreter
from commands_controller import CommandsController


if __name__ == "__main__":
    base_api_url = "http://localhost:5000"
    commands_controller = CommandsController(base_api_url)
    interpreter = Interpreter(commands_controller)
    interpreter.run()
