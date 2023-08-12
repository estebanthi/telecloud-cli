class CompleteParser:

    @classmethod
    def parse_line(cls, line):
        words_in_line = line.split()
        last_arg_name, last_arg_value = None, ''

        if len(words_in_line) > 1:  # at least a value or a name
            last_arg_value = words_in_line[-1]
            last_arg_name = words_in_line[-2]

            if not last_arg_name.startswith('-') and len(words_in_line) > 2:  # named argument without value
                last_arg_name = words_in_line[-1]
                last_arg_value = ''

            elif not last_arg_name.startswith('-') and last_arg_value.startswith('-'):
                last_arg_name = last_arg_value
                last_arg_value = ''

            elif not last_arg_name.startswith('-'):
                last_arg_name = None

            else:
                last_arg_name = words_in_line[-1]

        else:  # empty unnamed argument
            last_arg_value = ''
            last_arg_name = None

        return last_arg_name, last_arg_value