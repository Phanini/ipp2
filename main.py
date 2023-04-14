import argparse  # command-line argument handling
import sys
import re
import xml.etree.ElementTree as ET

"""
TODO:
move() symb/var

"""


def argument_parse(src, inp):
    parser = argparse.ArgumentParser(description='interpret.py ')
    parser.add_argument('--source=', action='store', dest='src', nargs='?')
    parser.add_argument('--input=', action='store', dest='inp', nargs='?')
    arguments = parser.parse_args()
    if arguments.inp is None and arguments.src is None:
        print("ERROR 10: Wrong arguments given")
        exit(10)
    return arguments.src, arguments.inp


def xml_check(root):
    # print('-------XML CHECK-------')
    # Check if program tag exists
    if root.tag != 'program': return sys.exit('program tag error')

    # Check language attribute
    if root.attrib.get('language') is None or root.attrib.get('language').lower() != "ippcode23":
        return sys.exit("Language error")

    # Iterate children of root
    currentOrder = 0
    for instruct in root:
        # Check if tag is instruction
        if instruct.tag != 'instruction': error_exit(31, "Error 31: Wrong XML format - instruction tag")

        # Check order of instructions
        currentOrder = int(instruct.get('order')) if int(instruct.get('order')) > currentOrder else \
            error_exit(32, 'Error 32: Wrong XML instruction order')

        instruction_attribs = list(instruct.attrib.keys())
        # Check if both order and opcode exist
        if not ('order' in instruction_attribs) or not ('opcode' in instruction_attribs):
            error_exit(31, 'Error 31: Wrong XML file format (order/opcode)')

        # Check if type attribute exists
        for argum in instruct:
            if 'type' not in argum.attrib.keys(): error_exit(31, "Error 31: Wrong XML file format (no type in arg)")
    print('=XML OK=')


def error_exit(err_num, err_msg):
    sys.stderr.write(err_msg + '\n')
    exit(err_num)


class memory:
    frames = {
        'GF': dict(),
        'LF': list(),
        'TF': None
    }


class variable:
    def __init__(self, arg_type, value):
        self.type = arg_type
        self.value = value


class instruction:
    def __init__(self, order, opcode):
        self.order = order
        self.opcode = opcode
        self.args = []

    def add_argument(self, arg_type, value):
        self.args.append(variable(arg_type, value))

    def get_args(self):
        return self.args

    def check_arg_num(self, num):
        if num != len(self.args):
            error_exit(56, "Error 56: Wrong number of arguments")

    def check_frame(self, mem_frame): # memory.frames[tf] is None
        if mem_frame == 'TF' and memory.frames['TF'] is None:
            error_exit(55, "TF Error 55: Memory frame doesn't exist")
        if mem_frame == 'LF' and not memory.frames['LF']:
            error_exit(55, "LF Error 55: Memory frame doesn't exist")

    # Checks existence of variable and frame
    def check_var(self, mem_frame, var_name) -> bool:
        self.check_frame(mem_frame)
        match mem_frame:
            case 'GF' | 'TF':
                return var_name in memory.frames[mem_frame].keys()
            case 'LF':
                return var_name in memory.frames['LF'][-1].keys()
        return False
        # error_exit(54, "Error 54: variable does not exist")

    def set_var_frame(self, frame, var_name, symb):
        if frame in ('GF', 'TF'):
            memory.frames[frame][var_name] = symb
        elif frame == 'LF':
            memory.frames['LF'][-1][var_name] = symb
        else:
            error_exit(55, "Error 55: Frame does not exist")

    def move(self):
        var = self.get_args()[0].value
        frame, var_name = var.split('@', 1)

        symb = self.get_args()[1].value
        self.set_var_frame(frame, var_name, symb)

    def write(self):
        result = self.symb_value(self.get_args()[0].value)
        print('WRITE RESULT: ' + result)

    def get_var_value(self, var):
        type, value = var.split('@', 1)
        return value

    def symb_value(self, value):
        prefix, suffix = value.split("@", 1)
        # print('PREF: ' + prefix + ' SUF: ' + suffix)
        if prefix not in ('GF', 'LF', 'TF'):
            return suffix
        if self.check_var(prefix, suffix) is False: error_exit(54, "Error 54: Non-existent var")

        match prefix:
            case 'GF' | 'TF':
                return self.get_var_value(memory.frames[prefix][suffix])
            case 'LF':
                return self.get_var_value(memory.frames['LF'][-1][suffix])
        sys.stderr.write('Wrong symb')
        exit()

    def defvar(self):
        mem_frame, var_name = self.get_args()[0].value.split("@", 1)
        if self.check_var(mem_frame, var_name):
            error_exit(52, "Error 52: Variable re-definition")

        # Init of an empty <var>
        var = {var_name: variable(None, None)}

        match mem_frame:
            case 'GF' | 'TF':
                memory.frames[mem_frame].update(var)
            case 'LF':
                memory.frames['LF'][-1].update(var)
            case _:
                error_exit(1, "Error ??: DEFVAR: Unknown var")

    def createframe(self):
        memory.frames['TF'] = dict()

    def pushframe(self):
        if memory.frames['TF'] is None:
            sys.stderr.write("No created frame to PUSHFRAME")
            exit(55)
        memory.frames['LF'].append(memory.frames['TF'])
        memory.frames['TF'] = None

    def popframe(self):
        if not memory.frames['LF']:
            sys.stderr.write("No pushed TF to POP")
            exit(55)
        memory.frames['TF'] = memory.frames['LF'].pop()

    def instr_switch(self):
        match self.opcode:
            case 'MOVE':  # <var>  <=  <symb>
                self.check_arg_num(2)
                self.move()
            case 'WRITE':  # <symb>
                self.write()
            case 'DEFVAR':  # <var>
                self.check_arg_num(1)
                self.defvar()
            case 'CREATEFRAME':
                self.createframe()
            case 'PUSHFRAME':
                self.pushframe()
            case 'POPFRAME':
                self.popframe()


def main():
    src = ''
    inp = ''
    instruction_list = list()
    argument = argument_parse(src, inp)

    # print(argument[0])  # --source
    # print(argument[1])  # --input

    #  handle input and source
    if argument[0] is not None:
        try:
            source_handle = open(argument[0], 'r')
        except FileNotFoundError:
            error_exit(11, "Error 11: File does not exist")
    else:
        source_handle = sys.stdin

    if argument[1] is not None:
        try:
            input_handle = open(argument[0], 'r')
        except FileNotFoundError:
            error_exit(11, "Error 11: File does not exist")
    else:
        input_handle = sys.stdin

    try:
        tree = ET.parse(source_handle)
    except ET.ParseError:
        sys.exit("XML parse error")

    root = tree.getroot()  # <program language>
    root[:] = sorted(root, key=lambda child: int(child.get('order')))
    xml_check(root)

    # iterate instructions
    for instruct in root:  # <instruction order= opcode=>
        instruct_tmp = instruction(instruct.get('order'), instruct.get('opcode'))

        # Create instruction
        for argum in instruct:  # <arg type= >text
            instruct_tmp.add_argument(argum.get('type'), argum.text)
        instruction_list.append(instruct_tmp)

    for instruct in instruction_list:
        instruction.instr_switch(instruct)


if __name__ == '__main__':
    main()
