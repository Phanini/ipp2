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
            error_exit(32, 'Error 32: Wrong XML file format (order/opcode)')

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
            error_exit(53, "Error 53: Wrong number of arguments")

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

    def set_var_frame(self, frame, var_name, symb_type, symb_value):
        if frame in ('GF', 'TF'):
            Memory.frames[frame][var_name] = Variable(symb_type, symb_value)
        elif frame == 'LF':
            Memory.frames['LF'][-1][var_name] = Variable(symb_type, symb_value)
        else:
            error_exit(55, "Error 55: Frame does not exist")

    def move(self):
        var = self.get_args()[0].value
        frame, var_name = var.split('@', 1)
        if not self.check_var_exists(frame, var_name): error_exit(54, "Error 54: Non-existent variable")

        symb = self.symb_value(self.get_args()[1])
        self.set_var_frame(frame, var_name, symb.type, symb.value)

    def write(self):
        symb1 = self.symb_value(self.get_args()[0])
        if symb1.type == 'nil':
            print('', end='')
        elif symb1.type == 'float':
            print(symb1.value.hex(), end='')
        else:
            res_without_escape = re.sub(r'\\[0-9]{3}', lambda match : chr(int(match.group().replace('\\', ''))), str(symb1.value))
            print(res_without_escape, end='')

    def get_var_value(self, var):
        type, value = var.split('@', 1)
        return value

    def create_var(self, type, value):
        return type + "@" + value

    def symb_value(self, symb) -> Variable:
        if symb.type not in ('int', 'bool', 'string', 'nil', 'label', 'type', 'var', 'float'):
            error_exit(32, "Error 32: Wrong XML formatting")
        if symb.type == 'var':
            if not re.match('^(GF|TF|LF){1}@{1}\S+$', symb.value):
                error_exit(32, "Error 32: Wrong XML formatting")
            mem_frame, var_name = symb.value.split('@', 1)
            if not self.check_var_exists(mem_frame, var_name): error_exit(54, "Error 54: Non-existent var")
            match mem_frame:
                case 'GF' | 'TF':
                    value = Memory.frames[mem_frame][var_name]
                    return value
                case 'LF':
                    value = Memory.frames['LF'][-1][var_name]
                    return value
        else:
            if symb.type == 'float':
                float_val = float.fromhex(symb.value)
                return Variable('float', float_val)
            return symb

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
        label = self.get_args()[0].value
        if label not in Memory.labels.keys(): error_exit(52, "Error 52: Undefined label")
        Memory.instruction_stack.append(Memory.program_counter)
        Memory.program_counter = Memory.labels[label] - 1

    def return_ins(self):
        if not Memory.instruction_stack: error_exit(56, "Error 56: Missing value on instruction stack")
        Memory.program_counter = Memory.instruction_stack.pop()

    def pushs(self):
        value = self.get_args()[0]
        Memory.data_stack.append(value)

    def pops(self):
        if not Memory.data_stack: error_exit(56, "Error 56: Pops from empty stack")
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        symb = self.symb_value(Memory.data_stack.pop())
        symb_type = symb.type
        symb_value = symb.value
        self.set_var_frame(mem_frame, var_name, symb_type, symb_value)

    def add_sub_mul_idiv(self, stack_flag):
        if stack_flag == 1:
            var = self.get_args()[0].value
            mem_frame, var_name = var.split('@', 1)
            if not self.check_var_exists(mem_frame, var_name):
                error_exit(54, "Error 54: Non-existent variable")
            var1 = self.symb_value(self.get_args()[1])
            var2 = self.symb_value(self.get_args()[2])
        else:
            try:
                var2 = self.symb_value(Memory.data_stack.pop())
                var1 = self.symb_value(Memory.data_stack.pop())
            except IndexError:
                error_exit(56, "Error 56: Popping from empty stack")
        if var1.type not in ('int', 'float') or var2.type not in ('int', 'float'): error_exit(53, "err53: wrong operand type")
        if var1.type != var2.type: error_exit(53, "Error 53: Wrong operands")
        value1 = var1.value
        value2 = var2.value
        if var1.type == 'int':
            try:
                value1, value2 = int(var1.value), int(var2.value)
            except ValueError:
                error_exit(32, "Error 32: Wrong operand")

        match self.opcode:
            case 'ADD' | 'ADDS':
                result = value1 + value2
            case 'SUB' | 'SUBS':
                result = value1 - value2
            case 'MUL' | 'MULS':
                result = value1 * value2
            case 'IDIV' | 'IDIVS':
                if value2 == 0: error_exit(57, "Error 57: Zero division")
                result = value1 // value2
            case 'DIV':
                if value2 == 0: error_exit(57, "Error 57: Zero division")
                result = value1 / value2
        if stack_flag == 1:
            self.set_var_frame(mem_frame, var_name, var1.type, result)
        else:
            tmp = Variable('int', result)
            Memory.data_stack.append(tmp)

    def lt_gt_eq_and_or(self, stack_flag):
        if stack_flag == 1:
            var = self.get_args()[0].value
            mem_frame, var_name = var.split('@', 1)
            if not self.check_var_exists(mem_frame, var_name):
                error_exit(54, "Error 54: Non-existent variable")
            symb1 = self.get_args()[1]
            symb2 = self.get_args()[2]
        else:
            try:
                var2 = Memory.data_stack.pop()
                var1 = Memory.data_stack.pop()
                symb2 = self.symb_value(var2)
                symb1 = self.symb_value(var1)
                if self.opcode not in ('EQ', 'EQS') and (symb1.type == 'nil' or symb2.type == 'nil'):
                    error_exit(53, "Err53: nil operand")
                if self.opcode not in ('EQ', 'EQS'):
                    if symb1.type != symb2.type:
                        error_exit(53, "Error 53: Wrong operands")
                if self.opcode in ('EQ', 'EQS'):
                    if symb1.type != 'nil' and symb2.type != 'nil':
                        if symb1.type != symb2.type:
                            error_exit(53, "Error 53: Wrong operands")
            except IndexError:
                error_exit(56, str(Memory.program_counter) + "Error 56: LTSGTSEQSANDS Pop from empty stack")
        match self.opcode:
            case 'LT' | 'LTS':
                result = 'true' if symb1.value < symb2.value else 'false'
            case 'GT' | 'GTS':
                result = 'true' if symb1.value > symb2.value else 'false'
            case 'EQ' | 'EQS':
                result = 'true' if symb1.value == symb2.value else 'false'
            case 'AND' | 'ANDS':
                result = 'true' if symb1.value == 'true' and symb2.value == 'true' else 'false'
            case 'OR' | 'ORS':
                result = 'true' if symb1.value == 'true' or symb2.value == 'true' else 'false'
        if stack_flag == 1:
            self.set_var_frame(mem_frame, var_name, 'string', result)
        else:
            Memory.data_stack.append(Variable('bool', result))

    def not_ins(self, stack_flag):
        if stack_flag == 1:
            var = self.get_args()[0].value
            mem_frame, var_name = var.split('@', 1)
            if not self.check_var_exists(mem_frame, var_name):
                error_exit(54, "Error 54: Non-existent variable")
            symb1 = self.get_args()[1]
            if symb1.type != 'bool': error_exit(53, "Error 53: Wrong operand type")
            var1 = self.symb_value(symb1)
        else:
            try:
                symb1 = Memory.data_stack.pop()
                if symb1.type!= 'bool': error_exit(53, "Error 53: Wrong operand type")
                var1 = self.symb_value(symb1)
            except IndexError:
                error_exit(56, "Error 56: Popping from empty stack")

        result = 'true' if var1.value == 'false' else 'false'
        if stack_flag == 1:
            self.set_var_frame(mem_frame, var_name, 'bool',result)
        else:
            Memory.data_stack.append(Variable('bool', result))

    def int2char(self, stack_flag):
        if stack_flag == 1:
            var = self.get_args()[0].value
            mem_frame, var_name = var.split('@', 1)
            if not self.check_var_exists(mem_frame, var_name):
                error_exit(54, "Error 54: Non-existent variable")
            symb = self.get_args()[1]
            var1 = self.symb_value(symb)
        else:
            try:
                symb = Memory.data_stack.pop()
                var1 = self.symb_value(symb)
            except IndexError:
                error_exit(56, "Error 56: Pop from empty stack")
        if var1.type != 'int': error_exit(53, "Error: Wrong operand type")
        if int(var1.value) not in range(0,1114112): error_exit(58, "Error 58: Wrong string operation")
        value = chr(int(var1.value))
        if stack_flag == 1:
            self.set_var_frame(mem_frame, var_name, 'string', value)
        else:
            Memory.data_stack.append(Variable('string', value))

    def int2float(self):
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")
        symb = self.get_args()[1]
        var1 = self.symb_value(symb)
        if var1.type != 'int': error_exit(53, "Error 53: Wrong operand type")
        self.set_var_frame(mem_frame, var_name, 'float', float(var1.value))

    def float2int(self):
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")
        symb = self.get_args()[1]
        var1 = self.symb_value(symb)
        if var1.type != 'float': error_exit(53, "Error 53: Wrong operand type")
        self.set_var_frame(mem_frame, var_name, 'int', int(var1.value))

    def stri2int(self, stack_flag):
        if stack_flag == 1:
            var = self.get_args()[0].value
            mem_frame, var_name = var.split('@', 1)
            if not self.check_var_exists(mem_frame, var_name):
                error_exit(54, "Error 54: Non-existent variable")
            symb1 = self.get_args()[1]
            symb2 = self.get_args()[2]
            var1 = self.symb_value(symb1)  # string@abce
            var2 = self.symb_value(symb2)  # int@3
        else:
            try:
                symb2 = Memory.data_stack.pop()
                symb1 = Memory.data_stack.pop()
            except IndexError:
                error_exit(56, "Error 56: Popping from empty stack")
            var1 = self.symb_value(symb1)
            var2 = self.symb_value(symb2)
        if symb1.type != 'string' or symb2.type != 'int': error_exit(53, "Error 53: Wrong operand type")
        if int(var2.value) not in range(0, len(var1.value)): error_exit(58, "Error 58: Wrong string action")
        result = str(ord(var1.value[int(var2.value)]))
        if stack_flag == 1:
            self.set_var_frame(mem_frame, var_name, 'int',result)
        else:
            Memory.data_stack.append(Variable('int', result))

    def read(self):
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")
        arg_type = self.get_args()[1].value
        if arg_type not in ('int', 'string', 'bool', 'float'): error_exit(53, "Error 53: Wrong operand type")
        inpt = Memory.input_handle.readline().strip().replace('\n', '')
        try:
            match arg_type:
                case 'int':
                    result = int(inpt)
                case 'float':
                    result = hex(inpt)
                case 'string':
                    result = inpt
                case 'bool':
                    if inpt.lower() == 'true':
                        result = 'true'
                    else:
                        result = 'false'
        except ValueError:
            arg_type = 'nil'
            result = ''
        self.set_var_frame(mem_frame, var_name, arg_type, result)

    def concat(self):
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")
        symb1 = self.get_args()[1]
        symb2 = self.get_args()[2]
        var1 = self.symb_value(symb1)  # string@abce
        var2 = self.symb_value(symb2)  # string@xyz
        if var1.type != 'string' or var2.type != 'string':
            error_exit(53, "Error 53: Wrong operand type")
        result = var1.value + var2.value
        self.set_var_frame(mem_frame, var_name, 'string', result)

    def strlen(self):
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")

        symb1 = self.get_args()[1]
        var1 = self.symb_value(symb1)
        if var1.type != 'string': error_exit(53, "Error 53: Wrong operand type")
        result = len(var1.value)
        self.set_var_frame(mem_frame, var_name, 'int', result)

    def getchar(self):
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")
        symb1 = self.get_args()[1]
        symb2 = self.get_args()[2]

        var1 = self.symb_value(symb1)  # string@some
        var2 = self.symb_value(symb2)  # int@5

        if var1.type != 'string' or var2.type != 'int': error_exit(53, "Error 53: Wrong operand type")
        if int(var2.value) not in range(len(var1.value)): error_exit(58, "Error 58: Wrong string indexing")

        result = var1.v[int(var2.value)]
        result = self.create_var('string', result)
        self.set_var_frame(mem_frame, var_name, 'string', result)

    def setchar(self):
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        var_value = self.symb_value(var).value
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")

        symb1 = self.get_args()[1]
        symb2 = self.get_args()[2]
        var1 = self.symb_value(symb1)  # int@5
        var2 = self.symb_value(symb2)  # string@hello
        if var1.type != 'int' or var2.type != 'string': error_exit(53, "Error 53: Wrong operand type")
        if int(var1.value) not in range(len(var_value)): error_exit(58, "Error 58: Wrong string indexing")
        if var2.value == '': error_exit(58, "Error 58: Invalid string operation")
        var_value = list(var_value)
        var_value[int(var1.value)] = var2.value[0]
        var_value = ''.join(var_value)
        self.set_var_frame(mem_frame, var_name, 'string', var_value)

    def type_inst(self):
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")

        symb = self.get_args()[1]
        var1 = self.symb_value(symb)
        if var1.value == '':
            result = ''
        else:
            result = var1.type
        self.set_var_frame(mem_frame, var_name, result, result)

    def label(self):
        pass

    def jump(self):
        label = self.get_args()[0].value
        if label not in Memory.labels.keys(): error_exit(52, "Error 52: Jump to an undefined label")
        Memory.program_counter = Memory.labels[label] - 1

    def jumpif(self, stack_flag):
        label = self.get_args()[0].value
        if label not in Memory.labels.keys(): error_exit(52, "Error 52: Undefinded label")

        if stack_flag == 1:
            symb1 = self.get_args()[1]
            symb2 = self.get_args()[2]
        else:
            try:
                symb2 = Memory.data_stack.pop()
                symb1 = Memory.data_stack.pop()
            except IndexError:
                error_exit(56, "Error 56: Empty data stack")

        if symb1.type != symb2.type:
            if symb1.type != 'nil' and symb2.type != 'nil':
                error_exit(53, "Error 53: Wrong operands")
        var1 = self.symb_value(symb1)
        var2 = self.symb_value(symb2)
        if var1.value == var2.value:
            if self.opcode == 'JUMPIFEQ' or self.opcode == 'JUMPIFEQS':
                Memory.program_counter = Memory.labels[label] - 1
        else:
            if self.opcode == 'JUMPIFNEQ' or self.opcode == 'JUMPIFNEQS':
                Memory.program_counter = Memory.labels[label] - 1

    def exit_inst(self):
        symb1 = self.get_args()[0]
        var1 = self.symb_value(symb1)
        if symb1.type != 'int': error_exit(53, "Error 53: Wrong operand type")
        if int(var1.value) not in range(0, 50): error_exit(57, "Error 57: Invalid return code")
        exit(int(var1.value))

    def dprint(self):
        symb1 = self.get_args()[0]
        var1 = self.symb_value(self.get_args()[0])
        sys.stderr.write(symb1.type + '@' + var1.value)

    def break_inst(self):
        pass

    def clears(self):
        Memory.data_stack.clear()

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
            case 'ADD' | 'SUB' | 'MUL' | 'IDIV' | 'DIV':
                self.check_arg_num(3)
                self.add_sub_mul_idiv(1)
            case 'ADDS' | 'SUBS' | 'MULS' | 'IDIVS':
                self.check_arg_num(0)
                self.add_sub_mul_idiv(0)
            case 'LT' | 'GT' | 'EQ' | 'AND' | 'OR':
                self.check_arg_num(3)
                self.lt_gt_eq_and_or(1)
            case 'LTS' | 'GTS' | 'EQS' | 'ANDS' | 'ORS':
                self.check_arg_num(0)
                self.lt_gt_eq_and_or(0)
            case 'NOT':
                self.check_arg_num(2)
                self.not_ins(1)
            case 'NOTS':
                self.check_arg_num(0)
                self.not_ins(0)
            case 'INT2CHAR':  # <var> <symb>
                self.check_arg_num(2)
                self.int2char(1)
            case 'INT2CHARS':
                self.check_arg_num(0)
                self.int2char(0)
            case 'STRI2INT':
                self.check_arg_num(3)
                self.stri2int(1)
            case 'STRI2INTS':
                self.check_arg_num(0)
                self.stri2int(0)
            case 'INT2FLOAT':
                self.check_arg_num(2)
                self.int2float()
            case 'FLOAT2INT':
                self.check_arg_num(2)
                self.float2int()
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
                self.jumpif(1)
            case 'JUMPIFEQS' | 'JUMPIFNEQS':
                self.check_arg_num(1)
                self.jumpif(0)
            case 'EXIT':
                self.check_arg_num(1)
                self.exit_inst()

            # DEBUGING INSTRUCTIONS
            case 'DPRINT':
                self.check_arg_num(1)
                self.dprint()
            case 'CLEARS':
                self.check_arg_num(0)
                self.clears()

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
    if Memory.input_handle==sys.stdin and source_handle==sys.stdin:
        error_exit(56, "Err56: Missing file")

    # Parse XML code
    try:
        tree = ET.parse(source_handle)
    except ET.ParseError:
        sys.exit("XML parse error")

    root = tree.getroot()  # <program language>
    root[:] = sorted(root, key=lambda child: int(child.get('order')))  # Order instructions
    xml_check(root)  # Check XML formatting

    # iterate instructions
    for instruct in root:  # <instruction order= opcode=>
        instruct[:] = sorted(instruct, key=lambda instruct: (instruct.tag))
        instruct_tmp = Instruction(instruct.get('order'), instruct.get('opcode').upper())

        # Add arguments to instructions and append them to instruction_list
        for argum in instruct:  # <arg type= >text
            instruct_tmp.add_argument(argum.get('type'), argum.text)
        instruction_list.append(instruct_tmp)

    order = 0
    for instruct in instruction_list:
        if instruct.opcode == "LABEL":
            if instruct.get_args()[0].value in Memory.labels.keys():
                error_exit(52, "Err52: label redefinition")
            Memory.labels[instruct.get_args()[0].value] = order
        order += 1

    while Memory.program_counter != len(instruction_list):
        #print(Memory.program_counter)
        Instruction.instr_switch(instruction_list[Memory.program_counter])
        Memory.program_counter += 1


if __name__ == '__main__':
    main()
