import sys, time, os, shutil

class CompilerError(Exception) :
    pass

def parse_argument(argument_tokens) :
    argument = "".join(argument_tokens).lower()
    index = ""

    if argument.endswith(",x") :
        index = ",x"
        argument = argument[:-2]
    elif argument.endswith(",y") :
        index = ",y"
        argument = argument[:-2]
    elif argument.lower() in variables :
        ArgumentValue = variables[argument.lower()][1]
        ArgumentType = variables[argument.lower()][0]
        return ArgumentType, ArgumentValue
    elif argument in labels :
        ArgumentValue = labels[argument]
        ArgumentType = "$"
        return ArgumentType, ArgumentValue

    ArgumentPrefixes = set(ARGTYPE_LookupTable["Absolute Arguments"]) | set(ARGTYPE_LookupTable["Immediate Arguments"])
    ArgumentType = next(
        (Prefix for Prefix in sorted(ArgumentPrefixes, key=len, reverse=True) if argument.startswith(Prefix)),
        ""
    )

    if index and ArgumentType not in ("", "$", "%") :
        raise CompilerError("Indexed arguments must use absolute addressing")

    ArgumentType += index
    ArgumentValueText = argument[len(ArgumentType) - len(index):]

    if "$" in ArgumentType :
        ArgumentValue = int(ArgumentValueText, 16)
    elif "%" in ArgumentType :
        ArgumentValue = int(ArgumentValueText, 2)
    else :
        ArgumentValue = int(ArgumentValueText)

    return ArgumentType, ArgumentValue

CompilerName   = sys.argv[0]
Asm_File       = sys.argv[1]
Cartridge_File = sys.argv[2]

print(f"Compiler name : {CompilerName}")
time.sleep(0.5)
print(f"Assembly file : {Asm_File}")
time.sleep(0.5)
print(f"Cartridge Name : {Cartridge_File}")
time.sleep(0.5)
print("\n===================================\n")
time.sleep(0.5)

OPCODE_LookupTable = {
    "ld": 0x0, "st": 0x1,

    "adc": 0x21, "sbc": 0x31,
    "in": 0x4, "de": 0x5,

    "t": 0x6,

    "ph": 0x7, "pl": 0x8, "pp": 0x8,

    "jmp": 0x90, 
    "bez": 0x91, "bnz": 0x92, 
    "bcs": 0x93, "bcc": 0x94, 
    "bos": 0x95, "boc": 0x96, 
    "bns": 0x97, "bnc": 0x98,
    "cp": 0xA,

    "call": 0x99, "retur": 0x9,

    "and": 0xC0, "eor": 0xC1, "xor": 0xC1,
    "shr": 0xC2, "shl": 0xC3,

    "cl": 0xE,

    ".ext": 0xF
}

REGISTER_LookupTable = {
    "a": 0x1, "x": 0x2, "y": 0x03, "n": 0xA,

    "ax": 0x0, "xa": 0x1, 
    "ay": 0x2, "ya": 0x3,
    "xs": 0x4, "sx": 0x5,

    "r": 0x0, "c": 0x1, "n": 0x2, "o": 0x3, "z": 0x4
}

ARGTYPE_LookupTable = {
    "Absolute Arguments": {"": 0x00, "$": 0x01, "%": 0x02, "$,x": 0x20, "$,y": 0x21},
    "Immediate Arguments": {"#": 0x10, "#$": 0x11, "#%": 0x12}
}

Arithmetic_Opcodes = [
    "adc", "sbc", 
    "and", "eor", "xor",
    "shr", "shl"
]

Single_Opcodes = [
    "in", "de", 
    "t",
    "ph", "pl", "pp",
    "cl",

    "retur"
]

Ctrl_Flow_Opcodes = [
    "jmp", 
    "bez", "bnz",
    "bcc", "bcs",
    "boc", "bos",
    "bnc", "bns", 
    "call"
]

labels = {}

with open(f"{Asm_File}") as Assembly :
    source_lines = [Line.strip() for Line in Assembly if Line.strip()]

ProgramOffset = 0
variables = {}
program = []

index = 0
while index < len(source_lines) :
    Line = source_lines[index]
    LineDecoder = Line.split()

    if len(LineDecoder) == 0 :
        index += 1
        continue

    if LineDecoder[0] == ".label" :
        labels[LineDecoder[1].lower()] = ProgramOffset
        index += 1

    elif LineDecoder[0] == ".sign" :
        signitureVal = bytes([0xF0])
        signiture = bytes([ord(Char) for Char in LineDecoder[1]])
        index += 1
    elif LineDecoder[0] == ".ver" :
        ProgramVerVal = bytes([0xF1])
        ProgramVer = bytes([int(LineDecoder[1], 16)])
        index += 1
    elif LineDecoder[0] == ".start" :
        ProgramStartVal = bytes([0xF2])
        ProgramStart = bytes([(int(LineDecoder[1], 16) & 0xFF00) >> 8, (int(LineDecoder[1], 16) & 0x00FF) >> 0])
        index += 1

    elif LineDecoder[0] == ".vars" :
        index += 1
        while index < len(source_lines) :
            variable_line = source_lines[index]
            variable_tokens = variable_line.split()

            if variable_tokens and variable_tokens[0] == ".end" :
                index += 1
                break

            variablesDecoder = variable_line.split("=")
            variableName = variablesDecoder[0].strip().lower()
            variableValueEncoded = variablesDecoder[1].strip()

            VariableValueType, VariableValue = parse_argument(variableValueEncoded)
            variables[variableName] = (VariableValueType, VariableValue)
            index += 1

    else :
        program.append(Line)
        ProgramOffset += 3
        index += 1

print(f"labels : {labels}")

with open(f"{Asm_File.replace(".asm", "", 1)}.a64", "wb") as ROM :
    ROM.write(signitureVal + signiture + ProgramVerVal + ProgramVer + ProgramStartVal + ProgramStart + bytes([0xFF]))
    for Line in program :
        LineDecoder = Line.split() 

        if len(LineDecoder) == 0 :
            continue

        Instruction = ""
        for InstrLen, Char in enumerate(LineDecoder[0]) :
            Instruction += Char

            if Instruction in OPCODE_LookupTable :
                break
        Argument = LineDecoder[1:] if len(LineDecoder) > 1 else []

        if Instruction not in OPCODE_LookupTable :
            raise CompilerError(f"Non-legal instruction found : {Instruction}")

        if Instruction == ".ext" :
            ROM.write(bytes([(0xF << 4) | int(Argument[0], 16)]))
            continue
        elif Instruction in Arithmetic_Opcodes :
            ArgumentType, ArgumentValue = parse_argument(Argument)

            if ArgumentType in ARGTYPE_LookupTable['Absolute Arguments'] :
                ROM.write(bytes([OPCODE_LookupTable[Instruction], ARGTYPE_LookupTable['Absolute Arguments'][ArgumentType], ArgumentValue]))
            elif ArgumentType in ARGTYPE_LookupTable['Immediate Arguments'] :
                ROM.write(bytes([OPCODE_LookupTable[Instruction], ARGTYPE_LookupTable['Immediate Arguments'][ArgumentType], ArgumentValue]))
            continue
        elif Instruction in Ctrl_Flow_Opcodes :
            ArgumentType, ArgumentValue = parse_argument(Argument)

            if ArgumentType in ARGTYPE_LookupTable['Absolute Arguments'] :
                ROM.write(bytes([OPCODE_LookupTable[Instruction], ARGTYPE_LookupTable['Absolute Arguments'][ArgumentType], ArgumentValue]))
            elif ArgumentType in ARGTYPE_LookupTable['Immediate Arguments'] :
                ROM.write(bytes([OPCODE_LookupTable[Instruction], ARGTYPE_LookupTable['Immediate Arguments'][ArgumentType], ArgumentValue]))
            continue

        InstrByte = (OPCODE_LookupTable[Instruction] << 4) | REGISTER_LookupTable[LineDecoder[0][InstrLen+1:]]

        if Instruction not in Single_Opcodes :
            ArgumentType, ArgumentValue = parse_argument(Argument)

            print(f"Current Instruction : {Instruction}") 
            print(f"Current Instruction Byte : {hex(InstrByte)}")
            print(f"Current Argument Byte & type : {hex(ArgumentValue)}, {ArgumentType}")
            if ArgumentType in ARGTYPE_LookupTable['Absolute Arguments'] :
                ROM.write(bytes([InstrByte, ARGTYPE_LookupTable['Absolute Arguments'][ArgumentType], ArgumentValue]))
            elif ArgumentType in ARGTYPE_LookupTable['Immediate Arguments'] :
                ROM.write(bytes([InstrByte, ARGTYPE_LookupTable['Immediate Arguments'][ArgumentType], ArgumentValue]))
            print()
        else :
            print(f"Current Instruction : {Instruction}") 
            print(f"Current Instruction Byte : {hex(InstrByte)}")
            ROM.write(bytes([InstrByte, 0x00, 0x00]))
            print()

        time.sleep(1)

if Cartridge_File not in os.listdir() : 
    os.mkdir(Cartridge_File)

Cartridge = os.listdir(Cartridge_File)

if f"{Asm_File.replace(".asm", "", 1)}.a64" not in Cartridge : 
    shutil.move(f"{Asm_File.replace(".asm", "", 1)}.a64", Cartridge_File) 
else :
    os.remove(f"{Cartridge_File}/{Asm_File.replace(".asm", "", 1)}.a64")
    shutil.move(f"{Asm_File.replace(".asm", "", 1)}.a64", Cartridge_File)