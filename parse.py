# @Author Milan Jakubec, 2 BIT FIT VUT
# @Date 7.2. 2024
# @file parse.py

# Dev notes:
# - Skript nesmi spoustet zadne dalsi procesy ci prikazy operacniho systemy
# - Veskera chybova hlaseni, varovani a ladici vypisy smeruji na stderr, jinak nedodrzeni zadani
# - Skript ktery dobehne bez chyby vraci 0
# - Skript ktery neprobehne bez chyby vraci chyby nasledovne:
#   10 - chubejici parametr skriptu (je-li treba) nebo pouziti nedovolene kombinace parametru
#   11 - chyba pri otevirani vstupnich souboru (neexistence, nedostacujici opravneni atd atd)
#   12 - chyba pri otevirani vystypnich soboru pro zapis (nedostacujici opravneni, chyba pri zapisu atd atd)
#   20 az 69 - navratove kody chyb specifickych pro jednotlive skripty 
#   99 - interni chyba (neovlivnena integraci, vstupnimi soubory nebo paramery CLI)
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

# XML snippet
#<?xml version="1.0" encoding="utf-8"?>
#<program language="IPPcode21">
  #<instruction order="1" opcode="DEFVAR">
   # <arg1 type="var">GF@counter</arg1>
  #</instruction>
  #<instruction order="2" opcode="MOVE">
   # <arg1 type="var">GF@counter</arg1>
  #  <arg2 type="string"/>
 # </instruction>
#  <instruction order="3" opcode="LABEL">
#    <arg1 type="label">while</arg1>
#  </instruction>


import argparse
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
    "var_regex:" : r"^(GF|LF|TF)@[a-zA-Z_\-$&%*!?][a-zA-Z0-9_\-$&%*!?]*$",
    "label_regex:" : r"^[a-zA-Z_\-$&%*!?][a-zA-Z0-9_\-$&%*!?]*$",
    "type_regex:" : r"^(int|string|bool)$",
    "string_regex:" : r"^([^\\\s#]|\\[0-9]{3})+$",
    "int_regex:" : r"^[+-]?\d+$",
    "bool_regex:" : r"^(true|false)$",
    "nil_regex:" : r"^nil@nil$"   
}

def main():
    """The main function"""

    parser = argparse.ArgumentParser(description="Filter-type script; "
                                                "reads the source code written in "
                                                "IPPcode24 from the standard input, " 
                                                "checks the lexical and syntactic "
                                                "correctness of the code and prints "                    
                                                "the XML representation of the "
                                                "program to the standard output.")
    parser.parse_args()

    source_code = sys.stdin.read() # read the source code from the standard input
    xml_tree_root = ET.Element("program", language = "IPPcode24") # create the root element of the XML tree

    run_analysis(prepare_source(source_code), xml_tree_root)

    ET.indent(xml_tree_root) # indent the XML tree
    tree = ET.ElementTree(xml_tree_root)
    tree.write('tree.xml', encoding="unicode", xml_declaration=True) # print the XML tree to the standard output
    return 0
    

def run_analysis(source_code, xml_tree):
    """The function performs lexical analysis of the source code and generates XML elements for the instructions."""

    for line_number, line in enumerate(source_code.splitlines(), start=0):
        print(f"Working on line {line_number}:", line.strip())
        tokens = line.split()
        #print("Tokens:", tokens)

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
                    print_error_and_exit(ErrorCode.OTHER_LEXICAL_OR_SYNTACTICAL_ERR)
                    


            else:
                print_error_and_exit(ErrorCode.UNKNOWN_OPCODE)

def prepare_source(source_code):
    """The function strips comments from the input source code and gets rid of empty lines."""  
    comment_stripped = re.sub(r"#.*", "", source_code) # strip comments

    non_empty_lines = [line for line in comment_stripped.splitlines() if line.strip()]
    return '\n'.join(non_empty_lines) # return the source code without comments and empty lines
        
def print_error_and_exit(error_code):
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

main()