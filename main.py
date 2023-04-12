import argparse  # command-line argument handling
import sys
import re
import xml.etree.ElementTree as ET


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
        self.args.append(value)
        self.args.append(variable(arg_type, value))

    def check_frame(self, mem_frame):
        if (mem_frame == 'TF' and memory.frames['TF'] is None) or \
                (mem_frame == 'LF' and not memory.frames['LF']):
            sys.stderr.write("Memory frame doesn't exist")
            exit(55)

    def check_var(self, mem_frame, var_name) -> bool:
        self.check_frame(mem_frame)
        match var_name:
            case 'GF':
                return var_name in memory.frames['GF'].keys()
            case 'LF':
                return var_name in memory.frames['LF'].pop().keys()
            case 'TF':
                return var_name in memory.frames['TF'].keys()
        return False

    def move(self):
        print('MOVE IN PROGRESS')

    def createframe(self):
        memory.frames['TF'] = dict()

    def pushframe(self):
        if memory.frames['TF'] is None:
            sys.stderr.write("No created frame to PUSHFRAME")
            exit(55)
        memory.frames['LF'].append(memory.frames['TF'])
        memory.frames = None

    def popframe(self):
        if not memory.frames['LF']:
            sys.stderr.write("No pushed TF to POP")
            exit(55)
        memory.frames['TF'] = memory.frames['LF'].pop()

    def instr_switch(self):
        match self.opcode:
            case 'MOVE':
                self.move()
            case 'CREATEFRAME':
                self.createframe()
            case 'PUSHFRAME':
                self.pushframe()
            case 'POPFRAME':
                self.popframe()


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
    print('-------XML CHECK-------')
    # Check if program tag exists
    if root.tag != 'program': return sys.exit('program tag error')

    # Check language attribute
    if root.attrib.get('language') is None or root.attrib.get('language').lower() != "ippcode23":
        return sys.exit("Language error")

    # Iterate children of root
    currentOrder = 0
    for instruct in root:
        # Check if tag is instruction
        if instruct.tag != 'instruction': exit(31)

        # Check order of instructions
        currentOrder = int(instruct.get('order')) if int(instruct.get('order')) > currentOrder else sys.exit(
            'wrong instruction order')

        instruction_attribs = list(instruct.attrib.keys())
        # Check if both order and opcode exist
        if not ('order' in instruction_attribs) or not ('opcode' in instruction_attribs): sys.exit(
            'child order/opcode error')

        # Check if type attribute exists
        for argum in instruct:
            if 'type' not in argum.attrib.keys(): sys.exit("No type in argum param")
    print('----------OK----------')


def main():
    src = ''
    inp = ''
    instruction_list = list()
    argument = argument_parse(src, inp)

    # print(argument[0])  # --source
    # print(argument[1])  # --input

    #  handle input and source
    source_handle = open(argument[0], 'r') if argument[0] is not None else sys.stdin
    input_handle = open(argument[1], 'r') if argument[1] is not None else sys.stdin

    try:
        tree = ET.parse(source_handle)
    except ET.ParseError:
        sys.exit("XML parse error")

    root = tree.getroot()  # <program language>
    xml_check(root)
    # iterate instructions
    for instruct in root:  # <instruction order= opcode=>
        instruct_tmp = instruction(instruct.get('order'), instruct.get('opcode'))

        # Create instruction
        for argum in instruct:  # <arg type= >text
            instruct_tmp.add_argument(argum.get('type'), argum.text)
        instruction_list.append(instruct_tmp)

    for instruct in instruction_list:
        print('call switch with ' + instruct.opcode)
        instruction.instr_switch(instruct)


if __name__ == '__main__':
    main()
