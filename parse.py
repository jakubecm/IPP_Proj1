# @Author Milan Jakubec, 2 BIT FIT VUT
# @Date 7.2. 2024
# @file parse.py
# @brief IPPcode24 parser, loads source code from standard input, checks lexical and syntactic correctness and prints XML representation of the program to standard output

# Dev notes:
# - Skript nesmi spoustet zadne dalsi procesy ci prikazy operacniho systemu
# - Veskere vstupy a vystupy v kodovani UTF-8 LC_ALL=cs_CZ.UTF-8

import re
import sys
from enum import Enum
import xml.etree.ElementTree as ET

# Helper classes

class ErrorCode(Enum):
    PARAMETER_ERR = 10
    INPUT_FILE_ERR = 11
    OUTPUT_FILE_ERR = 12
    MISSING_OR_WRONG_IPPCODE_HEADER = 21
    UNKNOWN_OPCODE = 22
    OTHER_LEXICAL_OR_SYNTACTICAL_ERR = 23
    INTERNAL_ERR = 99

class ArgType(Enum):
    VARIABLE = 1
    SYMBOL = 2
    LABEL = 3
    TYPE = 4

# Helper dictionaries

instructionDict = {
    #Header instruction
    ".IPPCODE24": [],

    # Basic instructions
    "MOVE": [ArgType.VARIABLE, ArgType.SYMBOL],
    "CREATEFRAME": [],
    "PUSHFRAME": [],
    "POPFRAME": [],
    "DEFVAR": [ArgType.VARIABLE],
    "CALL": [ArgType.LABEL],
    "RETURN": [],
    
    # Stack instructions
    "PUSHS": [ArgType.SYMBOL],
    "POPS": [ArgType.VARIABLE],

    # Arithmetic, relational, boolean and conversion instructions
    "ADD": [ArgType.VARIABLE, ArgType.SYMBOL, ArgType.SYMBOL],
    "SUB": [ArgType.VARIABLE, ArgType.SYMBOL, ArgType.SYMBOL],
    "MUL": [ArgType.VARIABLE, ArgType.SYMBOL, ArgType.SYMBOL],
    "IDIV": [ArgType.VARIABLE, ArgType.SYMBOL, ArgType.SYMBOL],
    "LT": [ArgType.VARIABLE, ArgType.SYMBOL, ArgType.SYMBOL],
    "GT": [ArgType.VARIABLE, ArgType.SYMBOL, ArgType.SYMBOL],
    "EQ": [ArgType.VARIABLE, ArgType.SYMBOL, ArgType.SYMBOL],
    "AND": [ArgType.VARIABLE, ArgType.SYMBOL, ArgType.SYMBOL],
    "OR": [ArgType.VARIABLE, ArgType.SYMBOL, ArgType.SYMBOL],
    "NOT": [ArgType.VARIABLE, ArgType.SYMBOL],
    "INT2CHAR": [ArgType.VARIABLE, ArgType.SYMBOL],
    "STRI2INT": [ArgType.VARIABLE, ArgType.SYMBOL, ArgType.SYMBOL],

    # Input/output instructions
    "READ": [ArgType.VARIABLE, ArgType.TYPE],
    "WRITE": [ArgType.SYMBOL],

    # String instructions
    "CONCAT": [ArgType.VARIABLE, ArgType.SYMBOL, ArgType.SYMBOL],
    "STRLEN": [ArgType.VARIABLE, ArgType.SYMBOL],
    "GETCHAR": [ArgType.VARIABLE, ArgType.SYMBOL, ArgType.SYMBOL],
    "SETCHAR": [ArgType.VARIABLE, ArgType.SYMBOL, ArgType.SYMBOL],

    # Type instructions
    "TYPE": [ArgType.VARIABLE, ArgType.SYMBOL],

    # Flow control instructions
    "LABEL": [ArgType.LABEL],
    "JUMP": [ArgType.LABEL],
    "JUMPIFEQ": [ArgType.LABEL, ArgType.SYMBOL, ArgType.SYMBOL],
    "JUMPIFNEQ": [ArgType.LABEL, ArgType.SYMBOL, ArgType.SYMBOL],
    "EXIT": [ArgType.SYMBOL],

    # Debug instructions
    "DPRINT": [ArgType.SYMBOL],
    "BREAK": []
}

attributesRegexDict = {
    "var_regex" : r"^(GF|LF|TF)@[a-zA-Z_\-$&%*!?][a-zA-Z0-9_\-$&%*!?]*$",
    "label_regex" : r"^[a-zA-Z_\-$&%*!?][a-zA-Z0-9_\-$&%*!?]*$",
    "type_regex" : r"^(int|string|bool)$",
    "string_regex" : r"^string@(?:[^\\\s#]|\\[0-9]{3})+$",
    "int_regex" : r"^int@(?:[+-]?\d+|0[xX][0-9a-fA-F]+|0[0-7]+)$",
    "bool_regex" : r"^bool@(true|false)$",
    "nil_regex" : r"^nil@(nil)$"   
}

def main():
    """The main function"""

    parse_arguments(sys.argv)
    source_code = sys.stdin.read()

    # check if stdin is empty
    if not source_code:
        print_error_and_exit(ErrorCode.MISSING_OR_WRONG_IPPCODE_HEADER)

    xml_tree_root = ET.Element("program", language="IPPcode24")  # create the root element of the XML tree

    run_analysis(prepare_source(source_code), xml_tree_root)

    ET.indent(xml_tree_root)
    tree = ET.ElementTree(xml_tree_root)
    tree.write(sys.stdout, encoding="unicode", xml_declaration=True)  # print the XML tree to the standard output
    sys.exit(0)
    

def run_analysis(source_code, xml_tree):
    """The function performs lexical analysis of the source code and generates XML elements for the instructions."""

    for line_number, line in enumerate(source_code.splitlines(), start=0):
        # split the line into seperate tokens
        tokens = line.split()

        if(line_number == 0 and line.upper().strip() != ".IPPCODE24"):
            print_error_and_exit(ErrorCode.MISSING_OR_WRONG_IPPCODE_HEADER)

        else:
            #skip empty lines and the header
            if len(tokens) == 0 or line_number == 0 : continue
                
            if tokens[0].upper() in instructionDict:
                # add instruction to the XML tree
                xml_instruction_el = ET.SubElement(xml_tree, "instruction", order=str(line_number), opcode=tokens[0].upper())

                # check if the number of arguments is correct and solve arguments if yes, use regex for matching
                if len(tokens) - 1 != len(instructionDict[tokens[0].upper()]):
                    print(instructionDict[tokens[0].upper()])
                    print_error_and_exit(ErrorCode.OTHER_LEXICAL_OR_SYNTACTICAL_ERR)

                else: analyse_arguments(tokens, xml_instruction_el)
                    
            else:
                print_error_and_exit(ErrorCode.UNKNOWN_OPCODE)

def prepare_source(source_code):
    """The function strips comments from the input source code and gets rid of empty lines."""  
    comment_stripped = re.sub(r"#.*", "", source_code) # strip comments

    non_empty_lines = [line for line in comment_stripped.splitlines() if line.strip()]
    return '\n'.join(non_empty_lines) # return the source code without comments and empty lines
        
def print_error_and_exit(error_code):
    """The function prints an error message to the standard error output and exits the script with the given error code."""
    error_messages = {
        ErrorCode.PARAMETER_ERR: "Error: missing script parameter or invalid combination of parameters used",
        ErrorCode.INPUT_FILE_ERR: "Error: failed to open input file",
        ErrorCode.OUTPUT_FILE_ERR: "Error: failed to open output file",
        ErrorCode.MISSING_OR_WRONG_IPPCODE_HEADER: "Error: missing or wrong IPPcode24 header in source code",
        ErrorCode.UNKNOWN_OPCODE: "Error: unknown opcode in source code",
        ErrorCode.OTHER_LEXICAL_OR_SYNTACTICAL_ERR: "Error: lexical or syntactical error detected",
        ErrorCode.INTERNAL_ERR: "Error: internal error"
      }
      
    error_message = error_messages.get(error_code)
    if error_message:
        print(error_message, file=sys.stderr)
        sys.exit(error_code.value)

def parse_arguments(args):
    """The function parses the script arguments and prints the help message if the --help or -h flag is used."""
    if len(args) == 2 and args[1] in ["--help", "-h"]:

        print("parse.py - IPPcode24 parser\n", file=sys.stdout)
        print("Filter-type script; "
            "reads the source code written in "
            "IPPcode24 from the standard input, " 
            "checks the lexical and syntactic "
            "correctness of the code and prints "                    
            "the XML representation of the "
            "program to the standard output.\n", file=sys.stdout)
        print("Usage: python3 parse.py < source_code.ippcode24", file=sys.stdout)
        print("Usage: cat ippcode24_file.ippcode24 | python3 parse.py\n", file=sys.stdout)
        return 0
    else:
        if len(args) == 1:
            return 0
        else:
            print_error_and_exit(ErrorCode.PARAMETER_ERR)

def analyse_arguments(tokens, instruction):
    """The function analyses the arguments of the instruction and adds them to the XML tree."""

    for i in range(1, len(tokens)):
        argument_type = instructionDict[tokens[0].upper()][i-1]    # get type of argument

        # get literal value of argument
        split_index = tokens[i].find("@")
        if split_index != -1:
            literal_value = tokens[i][split_index+1:]
        else:
            literal_value = tokens[i]

        if argument_type == ArgType.VARIABLE:
            if not re.match(attributesRegexDict["var_regex"], tokens[i]):
                print_error_and_exit(ErrorCode.OTHER_LEXICAL_OR_SYNTACTICAL_ERR)
            else:
                ET.SubElement(instruction, "arg" + str(i), type="var").text = tokens[i]

        elif argument_type == ArgType.SYMBOL:
            if re.match(attributesRegexDict["var_regex"], tokens[i]):
                ET.SubElement(instruction, "arg" + str(i), type="var").text = tokens[i]
            elif re.match(attributesRegexDict["int_regex"], tokens[i]):
                ET.SubElement(instruction, "arg" + str(i), type="int").text = literal_value
            elif re.match(attributesRegexDict["bool_regex"], tokens[i]):
                ET.SubElement(instruction, "arg" + str(i), type="bool").text = literal_value
            elif re.match(attributesRegexDict["nil_regex"], tokens[i]):
                ET.SubElement(instruction, "arg" + str(i), type="nil").text = literal_value
            elif re.match(attributesRegexDict["string_regex"], tokens[i]):
                ET.SubElement(instruction, "arg" + str(i), type="string").text = literal_value
            else:
                print_error_and_exit(ErrorCode.OTHER_LEXICAL_OR_SYNTACTICAL_ERR)

        elif argument_type == ArgType.LABEL:
            if not re.match(attributesRegexDict["label_regex"], tokens[i]):
                print_error_and_exit(ErrorCode.OTHER_LEXICAL_OR_SYNTACTICAL_ERR)
            else:
                ET.SubElement(instruction, "arg" + str(i), type="label").text = tokens[i]

        elif argument_type == ArgType.TYPE:
            if not re.match(attributesRegexDict["type_regex"], tokens[i]):
                print_error_and_exit(ErrorCode.OTHER_LEXICAL_OR_SYNTACTICAL_ERR)
            else:
                ET.SubElement(instruction, "arg" + str(i), type="type").text = literal_value

main()