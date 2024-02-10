# @Author Milan Jakubec, 2 BIT FIT VUT
# @Date 7.2. 2024
# @file parse.py

# Dev notes:
# - Skript nesmi spoustet zadne dalsi procesy ci prikazy operacniho systemy
# - Veskere vstupy a vystupy v kodovani UTF-8 LC_ALL=cs_CZ.UTF-8
# - Pomocne skripty nebo knihovny povoleny, pripona dle zvyklosti v prg jazyce
# Predinstalovane knihovny povolene, jine je nutne konzultovat
# Doporucene naprogramovat si vlastni testy
# Pro navrat chyboveho kodu pouzivat sys.exit, ne return
# Rozparsovat vstup do XML stromu
# Při tvorbě analyzátoru doporučujeme kombinovat konečně-stavové řízení a regulární výrazy a pro generování výstupního XML využít vhodnou knihovnu.

# ------------- PARAMETRY ------------- #
# Obecne kombinovatelne parametry skriptu jsou oddelene aspon jednim whitespacem a pokud neni receno jinak, mohou byt v libovolnem poradi.
# Testovane vzdy budou dlouhe verze parametru, nicmene je mozne implementovat zastupne zkracene (jedna pomlcka) parametry
# Je-li soucasti parametru i soubor (pr. --source=file nebo --source="file") anebo cesta, muze byt ten soubor/cesta zadany relativni cestou nebo absolutni cestou,
# vyskyt znaku uvozovek nemusime uvazovat, stejne tak rovnitko. Cesty/jmena souboru mohou obsahovat Unicode UTF-8 znaky.
#
# --help : Vypise na standartni vystup napovedu skriptu (nenacita vstup), napovedu lze prevzit ze zadani a vrati 0.
#          Help nelze kombinovat s zadnym dalsi parametrem, jinak skript vraci 10.
#
# -------------------------------------#

#------- POPIS FUNKCE -------#
# - Nacte ze standartniho vstupu zdrojovy kod v IPP-Code24, zkontroluje lexikalni a syntaktickou spravnost kodu
# - Pokud je vse ok, vypise na standartni vystup XML reprezentaci programu dle specifikace v sekci 3.1. zadani
#----------------------------#

#------ SPECIFICKE CHYBOVE VYSTUPY -----#
# 21 - chybna nebo chubejici hlavicka zdrojoveho kodu zapsanem v IPPcode24
# 22 - neznamy nebo chybny operacni kod ve zdrojovem kodu napsanem v IPPcode24
# 23 - jina lexikalni nebo sytakticka chuba zdrojoveho kodu zapsaneho v IPPcode24
#---------------------------------------#


import re # na praci s regulernimi vyrazy
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
    "int_regex" : r"^int@([+-]?\d+)$",
    "bool_regex" : r"^bool@(true|false)$",
    "nil_regex" : r"^nil@(nil)$"   
}

def main():
    """The main function"""

    parse_arguments(sys.argv)
    source_code = sys.stdin.read() # read the source code from the standard input

    # check if stdin is empty
    if not source_code:
        print_error_and_exit(ErrorCode.INPUT_FILE_ERR)

    xml_tree_root = ET.Element("program", language = "IPPcode24") # create the root element of the XML tree

    run_analysis(prepare_source(source_code), xml_tree_root)

    ET.indent(xml_tree_root) # indent the XML tree
    tree = ET.ElementTree(xml_tree_root)
    tree.write('tree.xml', encoding="unicode", xml_declaration=True) # print the XML tree to the standard output
    sys.exit(0)
    

def run_analysis(source_code, xml_tree):
    """The function performs lexical analysis of the source code and generates XML elements for the instructions."""

    for line_number, line in enumerate(source_code.splitlines(), start=0):
        # split the line into seperate tokens
        tokens = line.split()
        print(f"Tokens on line {line_number}:", tokens) # just for debugging

        if(line_number == 0 and line.upper().strip() != ".IPPCODE24"):
            print_error_and_exit(ErrorCode.MISSING_OR_WRONG_IPPCODE_HEADER)

        else:
            #skip empty lines and the header
            if len(tokens) == 0 or line_number == 0 : continue
                
            if tokens[0].upper() in instructionDict:
                # add instruction to the XML tree
                instruction = ET.SubElement(xml_tree, "instruction", order=str(line_number), opcode=tokens[0].upper())

                # check if the number of arguments is correct and solve arguments if yes, use regex for matching
                if len(tokens) - 1 != len(instructionDict[tokens[0].upper()]):
                    print(instructionDict[tokens[0].upper()])
                    print_error_and_exit(ErrorCode.OTHER_LEXICAL_OR_SYNTACTICAL_ERR)
                else:
                    # cross check aganist regexes based on what type is the argument
                    # first check the argtype, then check the regex
                    for i in range(1, len(tokens)):

                        argument_type = instructionDict[tokens[0].upper()][i-1]	# get type of argument
                        
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
        ErrorCode.OTHER_LEXICAL_OR_SYNTACTICAL_ERR: "Error: other lexical or syntactical error detected",
        ErrorCode.INTERNAL_ERR: "Error: internal error"
      }
      
    error_message = error_messages.get(error_code)
    if error_message:
        print(error_message, file=sys.stderr)
        sys.exit(error_code.value)

def parse_arguments(args):
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

main()