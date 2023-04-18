import argparse  # command-line argument handling
import sys
import re
import xml.etree.ElementTree as ET


def argument_parse(src, inp):
    """
    Function parsing arguments from commandline
    Return: touple of input and source
    """
    parser = argparse.ArgumentParser(description='interpret.py ')
    parser.add_argument('--source=', action='store', dest='src', nargs='?')
    parser.add_argument('--input=', action='store', dest='inp', nargs='?')
    arguments = parser.parse_args()
    if arguments.inp is None and arguments.src is None:
        error_exit(10, "Error 10: Wrong script argument/usage")
    return arguments.src, arguments.inp


def xml_check(root):
    """
    Function checking XML structures and their validity
    Input: XML root
    Return: root
    """
    # Check if program tag exists
    if root.tag != 'program': return error_exit(32, "Error 32: Wrong root tag")

    # Check language attribute
    if root.attrib.get('language') is None or root.attrib.get('language').lower() != "ippcode23":
        error_exit(32, "Error 32: Wrong XML format")

    # Iterate instructions to check they have both OPCODE and ORDER
    for instruct in root:
        if 'order' not in list(instruct.attrib.keys()) or 'opcode' not in list(instruct.attrib.keys()):
            error_exit(32, "Error 32: Missing ORDER of OPCODE")

    # Sort instructions by ORDER
    try:
        root[:] = sorted(root, key=lambda child: int(child.get('order')))
    except ValueError:
        error_exit(32, "Error 32: Order error")

    # Iterate children of root
    currentOrder = 0
    for instruct in root:
        # Check if tag is instruction
        if instruct.tag != 'instruction': error_exit(32, "Error 32: Wrong XML format - instruction tag")

        # Check order of instructions
        currentOrder = int(instruct.get('order')) if int(instruct.get('order')) > currentOrder else \
            error_exit(32, 'Error 32: (XML Check) Wrong XML instruction order')

        # Check if arguments have correct tags
        arg1_flag = 'false'
        arg2_flag = 'false'
        arg3_flag = 'false'
        for argum in instruct:
            match argum.tag:
                case 'arg1':
                    arg1_flag = 'true'
                case 'arg2':
                    arg2_flag = 'true'
                case 'arg3':
                    arg3_flag = 'true'
                case _:
                    error_exit(32, "Error 32: Unknown tag")
            # Check if type attribute exists
            if 'type' not in argum.attrib.keys(): error_exit(32, "Error 31: Wrong XML file format (no type in arg)")
        if arg2_flag == 'true' and arg1_flag == 'false': error_exit(32, "Error 32: XML arg2 without arg1")
        if arg3_flag == 'true' and (arg1_flag == 'false' or arg2_flag == 'false'):
            error_exit(32, "Error 32: XML arg2 without arg1")
    return root


def error_exit(err_num, err_msg):
    """
    Function returning error code with a error message to stderr\n
    Input: error number, error message
    """
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

    def check_var_empty(self) -> bool:
        """
        Function that checks if Variable is initialized or not
        :return: bool
        """
        return self.value is None and self.value is None


class Instruction:
    def __init__(self, order, opcode):
        self.order = order
        self.opcode = opcode
        self.args = []

    def add_argument(self, arg_type, value):
        """
        Adds argument to the instruction
        :param arg_type: string with type
        :param value: value of a var
        """
        self.args.append(Variable(arg_type, value))

    def get_args(self):
        """
        Returns list of arguments of an instruction
        :return: args[]
        """
        return self.args


    def check_arg_num(self, num):
        """
        Checks if correct number of arguments was given to an instruction
        :param num: int
        """
        if num != len(self.args):
            error_exit(32, "Error 32: Wrong number of arguments")

    def check_frame(self, mem_frame):
        """
        Checks if memory frame given exists
        :param mem_frame: string
        """
        if mem_frame == 'TF' and Memory.frames['TF'] is None:
            error_exit(55, "Error 55: Memory frame TF doesn't exist")
        if mem_frame == 'LF' and not Memory.frames['LF']:
            error_exit(55, "Error 55: Memory frame LF doesn't exist")

    def check_var_exists(self, mem_frame, var_name) -> bool:
        """
        Checks if given var exists
        :param mem_frame: string
        :param var_name: string
        :return:
        """
        self.check_frame(mem_frame)
        match mem_frame:
            case 'GF' | 'TF':
                return var_name in Memory.frames[mem_frame].keys()
            case 'LF':
                return var_name in Memory.frames['LF'][-1].keys()
            case _:
                error_exit(55, "Error 55: Non-existent frame")

    def set_var_frame(self, frame, var_name, symb_type, symb_value):
        """
        Takes destination variable and sets new values given in symb_type and symb_value
        :param frame: target frame
        :param var_name: target name
        :param symb_type: type of value
        :param symb_value: value of type string/int/float/bool/nil
        :return:
        """
        if frame in ('GF', 'TF'):
            Memory.frames[frame][var_name] = Variable(symb_type, symb_value)
        elif frame == 'LF':
            Memory.frames['LF'][-1][var_name] = Variable(symb_type, symb_value)
        else:
            error_exit(55, "Error 55: Frame does not exist")

    def move(self):
        """
        Moves values <symb1> to <var>
        """
        var = self.get_args()[0].value
        frame, var_name = var.split('@', 1)
        if not self.check_var_exists(frame, var_name): error_exit(54, "Error 54: Non-existent variable")

        symb = self.symb_value(self.get_args()[1])
        self.set_var_frame(frame, var_name, symb.type, symb.value)

    def write(self):
        """
        Prints out the value of a var
        """
        symb1 = self.symb_value(self.get_args()[0])
        if symb1.type == 'nil':
            print('', end='')
        elif symb1.type == 'float':
            print(symb1.value.hex(), end='')
        else:
            res_without_escape = re.sub(r'\\[0-9]{3}', lambda match: chr(int(match.group().replace('\\', ''))),
                                        str(symb1.value))
            print(res_without_escape, end='')

    def symb_value(self, symb) -> Variable:
        """
        Gets Variable and returns Variable with its contents from Memory Frames
        :param symb: input Variable
        :return: returning Variable
        """
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
            elif symb.type == 'int':
                try:
                    return Variable('int', int(symb.value))
                except ValueError:
                    error_exit(32, "Error 32: Wrong value")
            return symb

    def defvar(self):
        """
        Defines empty Variable in given Memory Frame
        """
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
        """
        Creates empty TemporaryFrame
        """
        Memory.frames['TF'] = dict()

    def pushframe(self):
        """
        Pushes TemporaryFrame into LocalFrame and clears TF
        """
        if Memory.frames['TF'] is None:
            error_exit(55, "Error 55: No frame to push")
        Memory.frames['LF'].append(Memory.frames['TF'])
        Memory.frames['TF'] = None

    def popframe(self):
        """
        Pops a frame from LocalFrame to TemporaryFrame
        """
        if not Memory.frames['LF']:
            error_exit(55, "Error 55: No frame to pop")
        Memory.frames['TF'] = Memory.frames['LF'].pop()

    def call(self):
        """Calls LABEL"""
        label = self.get_args()[0].value
        if label not in Memory.labels.keys(): error_exit(52, "Error 52: Undefined label")
        Memory.instruction_stack.append(Memory.program_counter)
        Memory.program_counter = Memory.labels[label] - 1

    def return_ins(self):
        if not Memory.instruction_stack: error_exit(56, "Error 56: Missing value on instruction stack")
        Memory.program_counter = Memory.instruction_stack.pop()

    def pushs(self):
        """
        Pushses Variable into data stack
        """
        value = self.get_args()[0]
        Memory.data_stack.append(value)

    def pops(self):
        """Pops Variable from data stack to a var"""
        if not Memory.data_stack: error_exit(56, "Error 56: Pops from empty stack")
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        symb = self.symb_value(Memory.data_stack.pop())
        symb_type = symb.type
        symb_value = symb.value
        self.set_var_frame(mem_frame, var_name, symb_type, symb_value)

    def add_sub_mul_idiv(self, stack_flag):
        """
        Instructions add sub mul idiv div and their stack versions
        :param stack_flag: 0 for stack operation, 1 for normal type
        """
        # Normal option
        if stack_flag == 1:
            var = self.get_args()[0].value
            mem_frame, var_name = var.split('@', 1)
            if not self.check_var_exists(mem_frame, var_name):
                error_exit(54, "Error 54: Non-existent variable")
            var1 = self.symb_value(self.get_args()[1])
            var2 = self.symb_value(self.get_args()[2])
        # Stack option
        else:
            try:
                var2 = self.symb_value(Memory.data_stack.pop())
                var1 = self.symb_value(Memory.data_stack.pop())
            except IndexError:
                error_exit(56, "Error 56: Popping from empty stack")
        if var1.type not in ('int', 'float') or var2.type not in ('int', 'float'):
            error_exit(53, "Error 53: wrong operand type")
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
        # Normal option saves to var
        if stack_flag == 1:
            self.set_var_frame(mem_frame, var_name, var1.type, result)
        # Stack option pushes result to data stack
        else:
            tmp = Variable('int', result)
            Memory.data_stack.append(tmp)

    def lt_gt_eq_and_or(self, stack_flag):
        """LT/GT/EQ/AND/OR instructions and their stack versions"""
        # Normal version
        if stack_flag == 1:
            var = self.get_args()[0].value
            mem_frame, var_name = var.split('@', 1)
            if not self.check_var_exists(mem_frame, var_name):
                error_exit(54, "Error 54: Non-existent variable")
            symb1 = self.symb_value(self.get_args()[1])
            symb2 = self.symb_value(self.get_args()[2])

        # Stack version
        else:
            try:
                var2 = Memory.data_stack.pop()
                var1 = Memory.data_stack.pop()
                symb2 = self.symb_value(var2)
                symb1 = self.symb_value(var1)
            except IndexError:
                error_exit(56, str(Memory.program_counter) + "Error 56: LTSGTSEQSANDS Pop from empty stack")
        if self.opcode not in ('EQ', 'EQS') and (symb1.type == 'nil' or symb2.type == 'nil'):
            error_exit(53, "Error 53: nil operand")
        if self.opcode not in ('EQ', 'EQS'):
            if symb1.type != symb2.type:
                error_exit(53, "Error 53: Wrong operands")
        if self.opcode in ('EQ', 'EQS'):
            if symb1.type != 'nil' and symb2.type != 'nil':
                if symb1.type != symb2.type:
                    error_exit(53, "Error 53: Wrong operands")

        match self.opcode:
            case 'LT' | 'LTS':
                result = 'true' if symb1.value < symb2.value else 'false'
            case 'GT' | 'GTS':
                result = 'true' if symb1.value > symb2.value else 'false'
            case 'EQ' | 'EQS':
                result = 'true' if symb1.value == symb2.value else 'false'
            case 'AND' | 'ANDS':
                # Check types
                if symb1.type != 'bool' or symb2.type != 'bool': error_exit(53, "Error 53: Wrong operand type")
                result = 'true' if symb1.value == 'true' and symb2.value == 'true' else 'false'
            case 'OR' | 'ORS':
                # Check types
                if symb1.type != 'bool' or symb2.type != 'bool': error_exit(53, "Error 53: Wrong operand type")
                result = 'true' if symb1.value == 'true' or symb2.value == 'true' else 'false'

        # Normal version returns value to a var
        if stack_flag == 1:
            self.set_var_frame(mem_frame, var_name, 'string', result)

        # Stack version appends result to a stack
        else:
            Memory.data_stack.append(Variable('bool', result))

    def not_ins(self, stack_flag):
        """Instruction negates the value of a var"""
        # Normal version
        if stack_flag == 1:
            var = self.get_args()[0].value
            mem_frame, var_name = var.split('@', 1)
            if not self.check_var_exists(mem_frame, var_name):
                error_exit(54, "Error 54: Non-existent variable")
            symb1 = self.symb_value(self.get_args()[1])
            if symb1.type != 'bool': error_exit(53, "Error 53: Wrong operand type")
            var1 = self.symb_value(symb1)

        # Stack version
        else:
            try:
                symb1 = Memory.data_stack.pop()
                if symb1.type != 'bool': error_exit(53, "Error 53: Wrong operand type")
                var1 = self.symb_value(symb1)
            except IndexError:
                error_exit(56, "Error 56: Popping from empty stack")

        result = 'true' if var1.value == 'false' else 'false'

        # Normal version returns result to a var
        if stack_flag == 1:
            self.set_var_frame(mem_frame, var_name, 'bool', result)

        # Stack version pushes result to data stack
        else:
            Memory.data_stack.append(Variable('bool', result))

    def int2char(self, stack_flag):
        # Normal version
        if stack_flag == 1:
            var = self.get_args()[0].value
            mem_frame, var_name = var.split('@', 1)
            if not self.check_var_exists(mem_frame, var_name):
                error_exit(54, "Error 54: Non-existent variable")
            symb = self.get_args()[1]
            var1 = self.symb_value(symb)

        # Stack version
        else:
            try:
                symb = Memory.data_stack.pop()
                var1 = self.symb_value(symb)
            except IndexError:
                error_exit(56, "Error 56: Pop from empty stack")

        if var1.check_var_empty():
            error_exit(56, "Error 56: Uninitialized var")
        if var1.type != 'int': error_exit(53, "Error 53: Wrong operand type")
        if int(var1.value) not in range(0, 1114112): error_exit(58, "Error 58: Wrong string operation")
        value = chr(int(var1.value))
        # Normal version returns value to a var
        if stack_flag == 1:
            self.set_var_frame(mem_frame, var_name, 'string', value)
        # Stack version pushes result to a data stack
        else:
            Memory.data_stack.append(Variable('string', value))

    def int2float(self):
        """BONUS IMPLEMENTATION: Converts int to float"""
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")
        symb = self.get_args()[1]
        var1 = self.symb_value(symb)
        if var1.check_var_empty():
            error_exit(56, "Error 56: Uninitialized var")
        if var1.type != 'int': error_exit(53, "Error 53: Wrong operand type")
        self.set_var_frame(mem_frame, var_name, 'float', float(var1.value))

    def float2int(self):
        """BONUS IMPLEMENTATION: Converts float to int"""
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")
        symb = self.get_args()[1]
        var1 = self.symb_value(symb)
        if var1.check_var_empty():
            error_exit(56, "Error 56: Uninicialized var")
        if var1.type != 'float': error_exit(53, "Error 53: Wrong operand type")
        self.set_var_frame(mem_frame, var_name, 'int', int(var1.value))

    def stri2int(self, stack_flag):
        # Normal version
        if stack_flag == 1:
            var = self.get_args()[0].value
            mem_frame, var_name = var.split('@', 1)
            if not self.check_var_exists(mem_frame, var_name):
                error_exit(54, "Error 54: Non-existent variable")
            symb1 = self.get_args()[1]
            symb2 = self.get_args()[2]
            var1 = self.symb_value(symb1)  # string@abce
            var2 = self.symb_value(symb2)  # int@3

        # Stack version
        else:
            try:
                symb2 = Memory.data_stack.pop()
                symb1 = Memory.data_stack.pop()
            except IndexError:
                error_exit(56, "Error 56: Popping from empty stack")
            var1 = self.symb_value(symb1)
            var2 = self.symb_value(symb2)

        if var1.type != 'string' or var2.type != 'int':
            error_exit(53, "Error 53: Wrong operand type")
        if int(var2.value) not in range(0, len(var1.value)): error_exit(58, "Error 58: Wrong string action")
        result = str(ord(var1.value[int(var2.value)]))
        # Normal version
        if stack_flag == 1:
            self.set_var_frame(mem_frame, var_name, 'int', result)

        # Stack version
        else:
            Memory.data_stack.append(Variable('int', result))

    def read(self):
        # Parse target var
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")
        arg_type = self.get_args()[1].value
        if arg_type not in ('int', 'string', 'bool', 'float'): error_exit(53, "Error 53: Wrong operand type")

        # Read from input
        inpt = Memory.input_handle.readline().strip().replace('\n', '')
        try:
            # Convert input to correct type and store into var
            match arg_type:
                case 'int':
                    result = int(inpt)
                case 'float':
                    result = float.fromhex(inpt)
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
        """Concatenate two strings and store result in var"""
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
        """Get length of symb1 and store in var"""
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
        """
        Gets char from if string<symb1> on int<symb2> index and stores it in var<var1>
        """
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

        result = var1.value[int(var2.value)]
        self.set_var_frame(mem_frame, var_name, 'string', result)

    def setchar(self):
        """Change string<var>'s int<symb1>-th char to char<symb2> """
        var = self.get_args()[0]
        try:
            mem_frame, var_name = var.value.split('@', 1)
        except AttributeError:
            error_exit(53, "Error 53: Wrong argument type given")
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
        """Automatically detect type of symb and return it to var"""
        var = self.get_args()[0].value
        mem_frame, var_name = var.split('@', 1)
        if not self.check_var_exists(mem_frame, var_name):
            error_exit(54, "Error 54: Non-existent variable")

        symb = self.get_args()[1]
        var1 = self.symb_value(symb)
        if var1.check_var_empty():
            result = ''
        else:
            result = var1.type
        self.set_var_frame(mem_frame, var_name, 'string', result)

    def label(self):
        pass

    def jump(self):
        """Unconditional jump to label"""
        label = self.get_args()[0].value
        if label not in Memory.labels.keys(): error_exit(52, "Error 52: Jump to an undefined label")
        Memory.program_counter = Memory.labels[label] - 1

    def jumpif(self, stack_flag):
        """Variations of jump-if-equal and their stack versions"""
        label = self.get_args()[0].value
        if label not in Memory.labels.keys(): error_exit(52, "Error 52: Undefinded label")

        # Normal version
        if stack_flag == 1:
            symb1 = self.get_args()[1]
            symb2 = self.get_args()[2]

        # Stack version
        else:
            try:
                symb2 = Memory.data_stack.pop()
                symb1 = Memory.data_stack.pop()
            except IndexError:
                error_exit(56, "Error 56: Empty data stack")

        var1 = self.symb_value(symb1)
        var2 = self.symb_value(symb2)
        if var1.type != var2.type:
            if var1.type != 'nil' and var2.type != 'nil':
                error_exit(53, "Error 53: Wrong operand types")

        if var1.value == var2.value:
            if self.opcode == 'JUMPIFEQ' or self.opcode == 'JUMPIFEQS':
                Memory.program_counter = Memory.labels[label] - 1
        else:
            if self.opcode == 'JUMPIFNEQ' or self.opcode == 'JUMPIFNEQS':
                Memory.program_counter = Memory.labels[label] - 1

    def exit_inst(self):
        """Stops program execution with given return code"""
        symb1 = self.get_args()[0]
        var1 = self.symb_value(symb1)
        if symb1.type != 'int': error_exit(53, "Error 53: Wrong operand type")
        if int(var1.value) not in range(0, 50): error_exit(57, "Error 57: Invalid return code")
        exit(int(var1.value))

    def dprint(self):
        """Returns given value to stderr"""
        symb1 = self.get_args()[0]
        var1 = self.symb_value(self.get_args()[0])
        sys.stderr.write(var1.type + '@' + var1.value)

    def break_inst(self):
        pass

    def clears(self):
        """Clears data stack"""
        Memory.data_stack.clear()

    def instr_switch(self):
        """
        Main instruction match case, that calls instructions and checks number of their argruments
        """
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
            case _:
                error_exit(32, "Error 32: Unknown OPCODE")


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
    if Memory.input_handle == sys.stdin and source_handle == sys.stdin:
        error_exit(56, "Err56: Missing file")

    # Parse XML code
    try:
        tree = ET.parse(source_handle)
    except ET.ParseError:
        error_exit(31, "Error 31: Wrong xml format")

    root = tree.getroot()  # <program language>
    root = xml_check(root)  # Check XML formatting

    # iterate instructions
    for instruct in root:  # <instruction order= opcode=>
        instruct_tmp = Instruction(instruct.get('order'), instruct.get('opcode').upper())

        args = sorted([i for i in instruct], key=lambda x: x.tag)
        # Add arguments to instructions and append them to instruction_list
        for arg in args:  # <arg type= >text
            instruct_tmp.add_argument(arg.get('type'), arg.text)
        instruction_list.append(instruct_tmp)

    # Iterate and collect all LABELs with their position
    order = 0
    for instruct in instruction_list:
        if instruct.opcode == "LABEL":
            if instruct.get_args()[0].value in Memory.labels.keys():
                error_exit(52, "Error 52: label redefinition")
            Memory.labels[instruct.get_args()[0].value] = order
        order += 1

    # Main instruction calling
    while Memory.program_counter != len(instruction_list):
        Instruction.instr_switch(instruction_list[Memory.program_counter])
        Memory.program_counter += 1


if __name__ == '__main__':
    main()
