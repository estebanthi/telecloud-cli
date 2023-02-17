import cmd


class Interpreter(cmd.Cmd):

    def __init__(self, commands_controller):
        cmd.Cmd.__init__(self)
        self.prompt = ">> "
        self.commands_controller = commands_controller

    def run(self):
        self.cmdloop()

    def do_exit(self, args):
        return -1

    def do_ls(self, args):
        res = self.commands_controller.ls(args)
        for file in res:
            print(f"{file['file_name']}: type: {file['file_type']}, size (gb): {file['file_size']}, tags: {file['tags']}, id: {file['_id']}")

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