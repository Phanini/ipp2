#### **Implementation documentation of 2nd project of IPP 2022/2023**
#### **Name and Surname: Jakub Phan**
#### **Login: xphanj00**
## Introduction
Implement python script `interpret.py` in python3.10 that takes XML file checks for any types of error and then 
interprets and generates output.
## Script arguments
Script takes following options

`-h | --help` &emsp;&emsp;&emsp;&nbsp;Brings out this help information\
`--source=file`&emsp;&emsp;&nbsp;&nbsp;File with XML source\
`--input=file`&emsp;&emsp;&emsp;File with input

## Solution
Firstly script arguments were parsed using functions from `argparse` library. Secondly inputed XML file is parsed using
`xml.etree.ElementTree` module. After that the validity of XML input is checked using `xml_check()` function. Next we
iterate the root all while checking and sorting tags, opcodes and orders. Instance of class `Instruction` is created and
it's arguments, which are instances of class `Variable`, are added. When the instruction is complete
it is then appended to `instruction_list` where all instructions to be executed are stored. After that the root is
iterated once again to load LABELs and store them with their Program_counter values in class `Memory`.
Lastly `instruction_list` is iterated calling `instr_switch` method of class `Instruction` that executes given
instruction.

## Classes
### Memory
Acts as the memory for the whole program storing necessary data for program execution. An instance contains:
* memory frames in a dictionary `frames`
* labels and their program counter values in a dictionary `labels`
* current program counter in `program_counter`
* data stack in a list `data_stack`
* input file in a string `input_handle`

### Variable
Represents indivitual variables of the program.
* type of a variable in `type`
* value of a variable in `value`

Method `check_var_empty` used to check if var only defined 

### Instruction
Main class used for representation of Instructions and all methods used for executing them. An instance is containing:
* order in which the instruction should be executed in `order`
* the name of the instruction in `opcode`
* list of instruction's arguments (instances of class `Variable`) in `args`

## Tests
Included in the archive are is a `test.php` script used for testing `interpret.py` and a folder with the tests. The script
generates a html file `out.html` showing results of all tests.

Script usage: `php test.php --int-only --directory=tests/ --recursive > out.html`

## Bonus implementations
#### FLOAT
Bonus implementation of float values using functions `float.fromhex()` and `float.hex()`.
Instructions `INT2FLOAT`, `FLOAT2INT`, `DIV` and all of the non-bonus functions are implemented
to work with float values.

#### STACK
Bonus implementation of stack version of functions `CLEARS`, `ADDS/SUBS/MULS/IDIVS`, `LTS/GTS/EQS`, `ANDS/ORS/NOTS`
, `INT2CHARS/STRI2INTS`,`JUMPIFEQS/JUMPIFNEQS`. Operands used for these functions  from `Memory.data_stack`. 