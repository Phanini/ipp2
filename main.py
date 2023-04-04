import argparse  # command-line argument handling
import sys
import re
import xml.etree.ElementTree as ET


class arg:
    def __init__(self, arg_type, value):
        self.type = arg_type
        self.value = value


class instruction:
    def __init__(self, name, number):
        self.name = name
        self.number = number
        self.args = []

    def add_argument(self, arg_type, value):
        self.args.append(value)


def argument_parse(src, inp):
    parser = argparse.ArgumentParser(description='interpret.py ')
    parser.add_argument('--source=', action='store', dest='src', nargs='?')
    parser.add_argument('--input=', action='store', dest='inp', nargs='?')
    arguments = parser.parse_args()
    if arguments.inp is None and arguments.src is None:
        print("ERROR 10: Wrong arguments given")
        sys.exit(10)
    return arguments.src, arguments.inp


def main():
    src = ''
    inp = ''
    argument = argument_parse(src, inp)

    # print(argument[0])  # --source
    # print(argument[1])  # --input

    #  handle input and source
    source_handle = open(argument[0], 'r') if argument[0] is not None else sys.stdin
    input_handle = open(argument[1], 'r') if argument[1] is not None else sys.stdin

    tree = ET.parse(source_handle)
    root = tree.getroot()
    # iterate instructions
    for child in root:
        if child.tag != 'instruction': sys.exit()
        print(child.tag)
        child_attribs = list(child.attrib.keys())
        if not('order' in child_attribs) or not('opcode' in child_attribs): sys.exit()
        print(child.get('order') + " - " + child.get('opcode'))
        for subchild in child:
            if not(re.match(r"arg[123]", subchild.tag)): sys.exit()
            print(subchild.tag + " = " + subchild.text)


if __name__ == '__main__':
    main()
