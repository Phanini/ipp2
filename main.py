import argparse  # command-line argument handling
import sys
import re
import xml.etree.ElementTree as ET

"""
TODO: 
arithmetic operations type control 
call() - PC number 
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


def error_exit(err_num, err_msg):
    sys.stderr.write(err_msg + '\n')
    exit(err_num)


class Memory:
    frames = {
        'GF': dict(),
        'LF': list(),
        'TF': None
    }
    labels = dict()
    instruction_stack = []
    program_counter = 1
    data_stack = []


class Variable:
    def __init__(self, arg_type, value):
        self.type = arg_type
        self.value = value

    def check_var_empty(self):
        return self.value is None and self.value is None


class Instruction:
    def __init__(self, order, opcode):
        self.order = order
        self.opcode = opcode
        self.args = []

    def add_argument(self, arg_type, value):
        self.args.append(Variable(arg_type, value))

    def get_args(self):
        return self.args

    def check_arg_types(self, symb1, symb2):
        type1, value1 = symb1.value.split('@', 1)
        type2, value2 = symb2.value.split('@', 1)
        if type1 != type2:
            error_exit(53, "Error 53: Wrong operand types")
        if self.opcode != 'EQ':
            if type1 == 'nil':
                error_exit(53, "Error 53: nil operand")
        if self.opcode in ('AND', 'OR'):
            if type1 != 'bool':
                error_exit(53, "Error 53: Wrong operand type")
            return value1, value2
        if type1 == 'int':
            return int(value1), int(value2)
        return symb1.value, symb2.value

    def check_arg_num(self, num):
        if num != len(self.args):
            error_exit(56, "Error 56: Wrong number of arguments")

    def check_frame(self, mem_frame):  # Memory.frames[tf] is None
        if mem_frame == 'TF' and Memory.frames['TF'] is None:
            error_exit(55, "TF Error 55: Memory frame doesn't exist")
        if mem_frame == 'LF' and not Memory.frames['LF']:
            error_exit(55, "LF Error 55: Memory frame doesn't exist")

    # Checks existence of Variable and frame
    def check_var_exists(self, mem_frame, var_name) -> bool:
        self.check_frame(mem_frame)
        match mem_frame:
            case 'GF' | 'TF':
                return var_name in Memory.frames[mem_frame].keys()
            case 'LF':
                return var_name in Memory.frames['LF'][-1].keys()
        return False

    def set_var_frame(self, frame, var_name, symb):
        if frame in ('GF', 'TF'):
            Memory.frames[frame][var_name] = symb
        elif frame == 'LF':
            Memory.frames['LF'][-1][var_name] = symb
        else:
            error_exit(55, "Error 55: Frame does not exist")

    def move(self):
        var = self.get_args()[0].value
        frame, var_name = var.split('@', 1)
        if not self.check_var_exists(frame, var_name): error_exit(54, "Error 54: Non-existent variable")

        symb = self.get_args()[1].value
        self.set_var_frame(frame, var_name, symb)

    def write(self):
        var = self.get_args()[0]
        if Variable.check_var_empty(var): error_exit(56, "Error 56: Variable without value to print")
        prefix, suffix = (var.value).split('@', 1)
        if prefix in ('GF', 'LF', 'TF'):
            if not self.check_var_exists(prefix, suffix): error_exit(54, "Error 54: Non-existent variable")
            prefix, suffix = self.symb_value(var.value)
            print(suffix)
            return
        if var.type == 'nil':
            print('', end='')
        else:
            print(suffix)

    def get_var_value(self, var):
        type, value = var.split('@', 1)
        return value

    def create_var(self, type, value):
        return type + "@" + value

    def symb_value(self, value):
        prefix, suffix = value.split("@", 1)
        if prefix not in ('GF', 'LF', 'TF'):
            return prefix, suffix
        if self.check_var_exists(prefix, suffix) is False: error_exit(54, "Error 54: Non-existent var")
        match prefix:
            case 'GF' | 'TF':
                value = Memory.frames[prefix][suffix]
                if type(value) == Variable:
                    if Variable.check_var_empty(value): error_exit(56, "Error 56: Variable without value to print")
                else:
                    prefix, suffix = value.split('@', 1)
                    return prefix, suffix

            case 'LF':
                value = Memory.frames['LF'][-1][suffix]
                if type(value) == Variable:
                    if Variable.check_var_empty(value): error_exit(56, "Error 56: Variable without valut to print")
                else:
                    prefix, suffix = value.split('@', 1)
                    return prefix, suffix
        error_exit(99, "Error 99: Symb_value() internal error")

    def defvar(self):
        mem_frame, var_name = self.get_args()[0].value.split("@", 1)
        if self.check_var_exists(mem_frame, var_name):
            error_exit(52, "Error 52: Variable re-definition")

        # Init of an empty <var>
        var = {var_name: Variable(None, None)}

        match mem_frame:
            case 'GF' | 'TF':
                Memory.frames[mem_frame].update(var)
            case 'LF':
                Memory.frames['LF'][-1].update(var)
            case _:
                error_exit(1, "Error ??: DEFVAR: Unknown var")

    def createframe(self):
        Memory.frames['TF'] = dict()

    def pushframe(self):
        if Memory.frames['TF'] is None:
            error_exit(55, "Error 55: No frame to push")
        Memory.frames['LF'].append(Memory.frames['TF'])
        Memory.frames['TF'] = None

    def popframe(self):
        if not Memory.frames['LF']:
            error_exit(55, "Error 55: No frame to pop")
        Memory.frames['TF'] = Memory.frames['LF'].pop()

    def call(self):
        label = self.get_args()[0]
        if label not in Memory.labels.keys(): error_exit(52, "Error 52: Undefined label")
        Memory.instruction_stack.append(Memory.program_counter)
        Memory.program_counter = Memory.labels[label];

    def return_ins(self):
        if not Memory.instruction_stack: error_exit(56, "Error 56: Missing value on instruction stack")
        Memory.program_counter = Memory.instruction_stack.pop()

    def pushs(self):
        value = self.get_args()[0].value
        Memory.data_stack.append(value)
        # print(Memory.__dict__)

    def pops(self):
        if not Memory.data_stack: error_exit(56, "Error 56: Pops from empty stack")
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        value = Memory.data_stack.pop()
        self.set_var_frame(mem_frame, var_name, value)
        # print(Memory.__dict__)

    def add(self):
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")

        pref1, value1 = self.symb_value(self.get_args()[1].value)
        pref2, value2 = self.symb_value(self.get_args()[2].value)
        value1, value2 = int(value1), int(value2)
        result = self.create_var("int", str(value1 + value2))
        self.set_var_frame(mem_frame, var_name, result)
        # print(Memory.__dict__)

    def sub(self):
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")

        pref1, value1 = self.symb_value(self.get_args()[1].value)
        pref2, value2 = self.symb_value(self.get_args()[2].value)
        value1, value2 = int(value1), int(value2)
        result = self.create_var("int", str(value1 - value2))
        self.set_var_frame(mem_frame, var_name, result)

    def mul(self):
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")

        pref1, value1 = self.symb_value(self.get_args()[1].value)
        pref2, value2 = self.symb_value(self.get_args()[2].value)
        value1, value2 = int(value1), int(value2)
        result = self.create_var("int", str(value1 * value2))
        self.set_var_frame(mem_frame, var_name, result)

    def idiv(self):
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")

        pref1, value1 = self.symb_value(self.get_args()[1].value)
        pref2, value2 = self.symb_value(self.get_args()[2].value)
        value1, value2 = int(value1), int(value2)
        if value2 == 0: error_exit(57, "Error 57: Zero division")
        result = self.create_var("int", str(value1 // value2))
        self.set_var_frame(mem_frame, var_name, result)

    def lt(self):
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")

        symb1, symb2 = self.check_arg_types(self.get_args()[1], self.get_args()[2])
        if symb1 < symb2:
            result = self.create_var('bool', 'true');
            self.set_var_frame(mem_frame, var_name, result)
        else:
            result = self.create_var('bool', 'false');
            self.set_var_frame(mem_frame, var_name, result)

    def gt(self):
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")

        symb1, symb2 = self.check_arg_types(self.get_args()[1], self.get_args()[2])
        if symb1 > symb2:
            result = self.create_var('bool', 'true');
            self.set_var_frame(mem_frame, var_name, result)
        else:
            result = self.create_var('bool', 'false');
            self.set_var_frame(mem_frame, var_name, result)

    def eq(self):
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")

        symb1, symb2 = self.check_arg_types(self.get_args()[1], self.get_args()[2])
        if symb1 == symb2:
            result = self.create_var('bool', 'true')
            self.set_var_frame(mem_frame, var_name, result)
        else:
            result = self.create_var('bool', 'false')
            self.set_var_frame(mem_frame, var_name, result)

    def and_ins(self):
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")

        symb1, symb2 = self.check_arg_types(self.get_args()[1], self.get_args()[2])
        if symb1 and symb2:
            result = self.create_var('bool', 'true')
            self.set_var_frame(mem_frame, var_name, result)
        else:
            result = self.create_var('bool', 'false')
            self.set_var_frame(mem_frame, var_name, result)

    def or_ins(self):
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")

        symb1, symb2 = self.check_arg_types(self.get_args()[1], self.get_args()[2])
        if symb1 or symb2:
            result = self.create_var('bool', 'true')
            self.set_var_frame(mem_frame, var_name, result)
        else:
            result = self.create_var('bool', 'false')
            self.set_var_frame(mem_frame, var_name, result)

    def not_ins(self):
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")

        prefix, suffix = self.get_args()[1].value.split('@', 1)
        if suffix == 'false':
            result = self.create_var('bool', 'true')
            self.set_var_frame(mem_frame, var_name, result)
        else:
            result = self.create_var('bool', 'false')
            self.set_var_frame(mem_frame, var_name, result)

    def int2char(self):
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")

        symb = self.get_args()[1].value
        var_type, value = self.symb_value(symb)
        if var_type != 'int': error_exit(53, "Error: Wrong operand type")
        value = chr(int(value))
        result = self.create_var('string', value)
        self.set_var_frame(mem_frame, var_name, result)

    def instr_switch(self):
        match self.opcode:
            # INSTRUCTIONS FOR FRAMES, CALLS
            case 'MOVE':  # <var>  <=  <symb>
                self.check_arg_num(2)
                self.move()
            case 'CREATEFRAME':
                self.check_arg_num(0)
                self.createframe()
            case 'PUSHFRAME':
                self.check_arg_num(0)
                self.pushframe()
            case 'POPFRAME':
                self.check_arg_num(0)
                self.popframe()
            case 'DEFVAR':  # <var>
                self.check_arg_num(1)
                self.defvar()
            case 'CALL':  # <label>
                self.check_arg_num(1)
                self.call()
            case 'RETURN':
                self.check_arg_num(0)
                self.return_ins()

            # INSTRUCTIONS FOR DATA STACK
            case 'PUSHS':
                self.check_arg_num(1)
                self.pushs()
            case 'POPS':
                self.check_arg_num(1)
                self.pops()

            # INSTRUCTION FOR ARITHMETIC, RELATIONAL, BOOLEAN AND CONVERSION
            case 'ADD':
                self.check_arg_num(3)
                self.add()
            case 'SUB':
                self.check_arg_num(3)
                self.sub()
            case 'MUL':
                self.check_arg_num(3)
                self.mul()
            case 'IDIV':
                self.check_arg_num(3)
                self.idiv()
            case 'LT':
                self.check_arg_num(3)
                self.lt()
            case 'GT':
                self.check_arg_num(3)
                self.gt()
            case 'EQ':
                self.check_arg_num(3)
                self.eq()
            case 'AND':
                self.check_arg_num(3)
                self.and_ins()
            case 'OR':
                self.check_arg_num(3)
                self.or_ins()
            case 'NOT':
                self.check_arg_num(2)
                self.not_ins()
            case 'INT2CHAR':  # <var> <symb>
                self.check_arg_num(2)
                self.int2char()
            # INSTRUCTION FOR I/O
            case 'WRITE':  # <symb>
                self.check_arg_num(1)
                self.write()


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

            error_exit(11, "Error 11: File " + argument[0] + " does not exist")
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
        instruct_tmp = Instruction(instruct.get('order'), instruct.get('opcode').upper())

        # Create instruction
        for argum in instruct:  # <arg type= >text
            instruct_tmp.add_argument(argum.get('type'), argum.text)
        instruction_list.append(instruct_tmp)

    for instruct in instruction_list:
        Instruction.instr_switch(instruct)


if __name__ == '__main__':
    main()
