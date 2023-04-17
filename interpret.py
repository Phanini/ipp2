import argparse  # command-line argument handling
import sys
import re
import xml.etree.ElementTree as ET


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
        arg_order = 1
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
    program_counter = 0
    data_stack = []
    input_handle = ''


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
        symb1 = self.get_args()[0]
        if symb1.type == 'nil':
            print('', end='')
        else:
            print(self.symb_value(symb1), end='')

    def get_var_value(self, var):
        type, value = var.split('@', 1)
        return value

    def create_var(self, type, value):
        return type + "@" + value

    def symb_value(self, symb):
        if symb.type not in ('int', 'bool', 'string', 'nil', 'label', 'type', 'var'):
            error_exit(32, "Error 32: Wrong XML formatting")
        if symb.type == 'var':
            if not re.match('^(GF|TF|LF){1}@{1}\S+$', symb.value):
                error_exit(32, "Error 32: Wrong XML formatting")
            mem_frame, var_name = symb.value.split('@', 1)
            if not self.check_var_exists(mem_frame, var_name): error_exit(54, "Error 54: Non-existent var")
            match mem_frame:
                case 'GF' | 'TF':
                    value = Memory.frames[mem_frame][var_name]
                    if type(value) == Variable:
                        if Variable.check_var_empty(value): error_exit(56, "Error 56: Variable without value to print")
                    else:
                        return value

                case 'LF':
                    value = Memory.frames['LF'][-1][var_name]
                    if type(value) == Variable:
                        if Variable.check_var_empty(value): error_exit(56, "Error 56: Variable without value to print")
                    else:
                        return value
        else:
            match symb.type:
                case 'int':
                    try:
                        int(symb.value)
                    except ValueError:
                        error_exit(32, "Err32: Wrong int format")
                case 'float':
                    if not re.match('^\-?[0-9]*\.?[0-9]*$', symb.value):
                        error_exit(32, "Err32: Wrong float format")
                case 'nil':
                    if symb.value != 'nil':
                        error_exit(32, "Err32: Wrong nil format")
            return symb.value
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
        Memory.program_counter = Memory.labels[label]

    def return_ins(self):
        if not Memory.instruction_stack: error_exit(56, "Error 56: Missing value on instruction stack")
        Memory.program_counter = Memory.instruction_stack.pop()

    def pushs(self):
        value = self.get_args()[0].value
        Memory.data_stack.append(value)
        # print(Memory.__dict__)

    def pops(self):
        if not Memory.data_stack: error_exit(55, "Error 55: Pops from empty stack")
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        value = Memory.data_stack.pop()
        self.set_var_frame(mem_frame, var_name, value)
        # print(Memory.__dict__)

    def add_sub_mul_idiv(self):
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")

        symb1 = self.get_args()[1]
        symb2 = self.get_args()[2]
        value1 = self.symb_value(symb1)
        value2 = self.symb_value(symb2)
        try:
            value1, value2 = int(value1), int(value2)
        except ValueError:
            error_exit(53, "err53: wrong operand type")

        match self.opcode:
            case 'ADD':
                result = str(value1 + value2)
            case 'SUB':
                result = str(value1 - value2)
            case 'MUL':
                result = str(value1 * value2)
            case 'IDIV':
                if value2==0: error_exit(57, "Error 57: Zero division")
                result = str(value1 // value2)
        self.set_var_frame(mem_frame, var_name, result)
        # print(Memory.__dict__)

    def lt_gt_eq_and_or(self):
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")

        symb1, symb2 = self.check_arg_types(self.get_args()[1], self.get_args()[2])
        match self.opcode:
            case 'LT':
                if symb1 < symb2:
                    result = self.create_var('bool', 'true')
                    self.set_var_frame(mem_frame, var_name, result)
                else:
                    result = self.create_var('bool', 'false')
                    self.set_var_frame(mem_frame, var_name, result)
            case 'GT':
                if symb1 > symb2:
                    result = self.create_var('bool', 'true')
                    self.set_var_frame(mem_frame, var_name, result)
                else:
                    result = self.create_var('bool', 'false')
                    self.set_var_frame(mem_frame, var_name, result)
            case 'EQ':
                if symb1 == symb2:
                    result = self.create_var('bool', 'true')
                    self.set_var_frame(mem_frame, var_name, result)
                else:
                    result = self.create_var('bool', 'false')
                    self.set_var_frame(mem_frame, var_name, result)
            case 'AND':
                if symb1 and symb2:
                    result = self.create_var('bool', 'true')
                    self.set_var_frame(mem_frame, var_name, result)
                else:
                    result = self.create_var('bool', 'false')
                    self.set_var_frame(mem_frame, var_name, result)
            case 'OR':
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
        value = self.symb_value(symb)
        if symb.type != 'int': error_exit(53, "Error: Wrong operand type")
        value = chr(int(value))
        result = self.create_var('string', value)
        self.set_var_frame(mem_frame, var_name, result)

    def stri2int(self):
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")
        symb1=self.get_args()[1]
        symb2=self.get_args()[2]

        value1 = self.symb_value(symb1)  # string@abce
        value2 = self.symb_value(symb2)  # int@3
        if symb1.type != 'string' or symb2.type != 'int': error_exit(53, "Error 53: Wrong operand type")
        if int(value2) not in range(len(value1)): error_exit(58, "Error 58: Wrong string action")
        result = str(ord(value1[int(value2)]))
        result = self.create_var('int', result)
        self.set_var_frame(mem_frame, var_name, result)

    def read(self):
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")
        arg_type = self.get_args()[1].value
        if arg_type not in ('int', 'string', 'bool'): error_exit(53, "Error 53: Wrong operand type")
        inpt = Memory.input_handle.readline().strip().replace('\n', '')
        try:
            match arg_type:
                case 'int':
                    result = int(inpt)
                case 'string':
                    result = inpt
                case 'bool':
                    if inpt.lower() == 'true':
                        result = 'true'
                    else:
                        result = 'false'
        except ValueError:
            arg_type = 'nil'

        result = self.create_var(arg_type, result)
        self.set_var_frame(mem_frame, var_name, result)

    def concat(self):
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")
        symb1 = self.get_args()[1]
        symb2 = self.get_args()[2]
        value1 = self.symb_value(symb1)  # string@abce
        value2 = self.symb_value(symb2)  # string@xyz
        if symb1.type != 'string' or symb2.type != 'string':
            error_exit(53, "Error 53: Wrong operand type")
        result = value1 + value2
        result = self.create_var('string', result)
        self.set_var_frame(mem_frame, var_name, result)

    def strlen(self):
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")

        symb1 = self.get_args()[1]
        value1 = self.symb_value(symb1)
        if symb1.type != 'string': error_exit(53, "Error 53: Wrong operand type")
        result = len(value1)
        result = self.create_var('int', str(result))
        self.set_var_frame(mem_frame, var_name, result)

    def getchar(self):
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")
        symb1 = self.get_args()[1]
        symb2 = self.get_args()[2]

        value1 = self.symb_value(symb1)  # string@some
        value2 = self.symb_value(symb2)  # int@5

        if symb1.type != 'string' or symb2.type != 'int': error_exit(53, "Error 53: Wrong operand type")
        if int(value2) not in range(len(value1)): error_exit(58, "Error 58: Wrong string indexing")

        result = value1[int(value2)]
        result = self.create_var('string', result)
        self.set_var_frame(mem_frame, var_name, result)

    def setchar(self):
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        var_value = self.symb_value(var)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")

        symb1 = self.get_args()[1]
        symb2 = self.get_args()[2]
        value1 = self.symb_value(symb1)  # int@5
        value2 = self.symb_value(symb2)  # string@hello
        if symb1.type != 'int' or symb2.type != 'string': error_exit(53, "Error 53: Wrong operand type")
        if int(value1) not in range(len(var_value)): error_exit(58, "Error 58: Wrong string indexing")
        if value2 == '': error_exit(58, "Error 58: Invalid string operation")
        var_value = list(var_value)
        var_value[int(value1)] = value2[0]
        var_value = ''.join(var_value)
        result = self.create_var('string', var_value)
        self.set_var_frame(mem_frame, var_name, result)

    def type_inst(self):
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")

        type1, value1 = self.symb_value(self.get_args()[1])
        result = self.create_var('string', type1)
        self.set_var_frame(mem_frame, var_name, result)

    def label(self):
        pass

    def jump(self):
        label = self.get_args()[0].value
        if label not in Memory.labels.keys(): error_exit(52, "Error 52: Jump to an undefined label")
        Memory.program_counter = Memory.labels[label] - 1

    def jumpif(self):
        label = self.get_args()[0].value
        if label not in Memory.labels.keys(): error_exit(52, "Error 52: Undefinded label")
        symb1 = self.get_args()[1]
        symb2 = self.get_args()[2]

        value1 = self.symb_value(symb1)
        value2 = self.symb_value(symb2)
        if value1 == value2:
            if self.opcode == 'JUMPIFEQ':
                Memory.program_counter = Memory.labels[label] - 1
        else:
            if self.opcode == 'JUMPIFNEQ':
                Memory.program_counter = Memory.labels[label] - 1

    def exit_inst(self):
        symb1 = self.get_args()[0]
        value1 = self.symb_value(symb1)
        if symb1.type != 'int': error_exit(53, "Error 53: Wrong operand type")
        if int(value1) not in range(0, 50): error_exit(57, "Error 57: Invalid return code")
        exit(int(value1))

    def dprint(self):
        symb1 = self.get_args()[0]
        value1 = self.symb_value(self.get_args()[0])
        sys.stderr.write(symb1.type + '@' + value1)

    def break_inst(self):
        pass

    def instr_switch(self):
        match self.opcode:
            # INSTRUCTIONS FOR FRAMES, CALLS
            case 'MOVE':  # <var> <symb>
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
            case 'ADD' | 'SUB' | 'MUL' | 'IDIV':
                self.check_arg_num(3)
                self.add_sub_mul_idiv()
            case 'LT' | 'GT' | 'EQ' | 'AND' | 'OR':
                self.check_arg_num(3)
                self.lt_gt_eq_and_or()
            case 'NOT':
                self.check_arg_num(2)
                self.not_ins()
            case 'INT2CHAR':  # <var> <symb>
                self.check_arg_num(2)
                self.int2char()
            case 'STRI2INT':
                self.check_arg_num(3)
                self.stri2int()

            # INSTRUCTION FOR I/O
            case 'READ':
                self.check_arg_num(2)
                self.read()
            case 'WRITE':  # <symb>
                self.check_arg_num(1)
                self.write()

            # INSTRUCTION FOR STRING MANIPULATION
            case 'CONCAT':
                self.check_arg_num(3)
                self.concat()
            case 'STRLEN':
                self.check_arg_num(2)
                self.strlen()
            case 'GETCHAR':
                self.check_arg_num(3)
                self.getchar()
            case 'SETCHAR':
                self.check_arg_num(3)
                self.setchar()

            # INSTRUCTIONS FOR TYPE-ING
            case 'TYPE':
                self.check_arg_num(2)
                self.type_inst()

            # INSTRUCTIONS FOR FLOW CONTROL
            case 'LABEL':
                self.check_arg_num(1)
                self.label()
            case 'JUMP':
                self.check_arg_num(1)
                self.jump()
            case 'JUMPIFEQ' | 'JUMPIFNEQ':
                self.check_arg_num(3)
                self.jumpif()
            case 'EXIT':
                self.check_arg_num(1)
                self.exit_inst()

            # DEBUGING INSTRUCTIONS
            case 'DPRINT':
                self.check_arg_num(1)
                self.dprint()


def main():
    src = ''
    inp = ''
    instruction_list = list()
    argument = argument_parse(src, inp)

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
            Memory.input_handle = open(argument[0], 'r')
        except FileNotFoundError:
            error_exit(11, "Error 11: File does not exist")
    else:
        Memory.input_handle = sys.stdin

    # Parse XML code
    try:
        tree = ET.parse(source_handle)
    except ET.ParseError:
        sys.exit("XML parse error")

    root = tree.getroot()  # <program language>
    root[:] = sorted(root, key=lambda child: int(child.get('order'))) # Order instructions
    xml_check(root) # Check XML formatting

    # iterate instructions
    for instruct in root:  # <instruction order= opcode=>
        instruct_tmp = Instruction(instruct.get('order'), instruct.get('opcode').upper())

        # Add arguments to instructions and append them to instruction_list
        for argum in instruct:  # <arg type= >text
            instruct_tmp.add_argument(argum.get('type'), argum.text)
        instruction_list.append(instruct_tmp)

    order=0
    for instruct in instruction_list:
        if instruct.opcode == "LABEL":
            if instruct.get_args()[0].value in Memory.labels.keys():
                error_exit(52, "Err52: label redefinition")
            Memory.labels[instruct.get_args()[0].value] = order
        order += 1

    for i in range(0, len(instruction_list)):
        Instruction.instr_switch(instruction_list[i])
        Memory.program_counter += 1



if __name__ == '__main__':
    main()
