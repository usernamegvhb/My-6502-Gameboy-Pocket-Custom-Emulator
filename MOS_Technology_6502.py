import time, sys

class CPUError(Exception) :
    pass

memory = bytearray(0x10000)
"""
0000 - 03FF : Free RAM

0400 - 04FF : Stack

0500 - 05FF : Zero Page

0600 - EFFF : ROM Data

F000 - FFFF : I/O
"""

registers = {
    "A": 0, "X": 0, "Y": 0,

    "SP": 0x04FF,
    "PC": 0x0600,

    "P": 0x20
}

REGISTER_LookupTable = {
    0x1: "A", 0x2: "X", 0x3: "Y"
}

Jumped = False

program = []
Signature = ""
ContinueCheck = False

with open(input("Please Enter A ROM File : "), "rb") as ROM :
    for I, byte in enumerate(ROM.read()) :
        memory[registers["PC"]+I] = byte

while registers["PC"] < len(memory) :
    if registers["PC"] + 2 >= len(memory) :
        raise CPUError(f"PC ran past the end of memory at {hex(registers['PC'])}")

    Instruction, Register = (memory[registers["PC"]] & 0xF0) >> 4, (memory[registers["PC"]] & 0x0F) >> 0

    ArgumentType, Argument = memory[registers["PC"]+1], memory[registers["PC"]+2]

    print(f"Instruction : {hex(Instruction)}    | Register : {hex(Register)}")
    print(f"Argument Type : {hex(ArgumentType)} | Argument : {hex(Argument)}")

    match Instruction :
        case 0x0 : # load Instruction  | ld[register] [argType, arg]
            if ArgumentType >> 4 == 0x0 :
                registers[REGISTER_LookupTable[Register]] = memory[Argument]
            elif ArgumentType >> 4 == 0x1 :
                registers[REGISTER_LookupTable[Register]] = Argument
            elif ArgumentType == 0x20 :
                registers[REGISTER_LookupTable[Register]] = memory[((Argument << 8) | registers["X"]) & 0xFFFF]
            elif ArgumentType == 0x21 :
                registers[REGISTER_LookupTable[Register]] = memory[((Argument << 8) | registers["Y"]) & 0xFFFF]

            LoadedValue = registers[REGISTER_LookupTable[Register]]
            registers["P"] = (registers["P"] | 0x02) if LoadedValue == 0 else (registers["P"] & ~0x02)
            registers["P"] = (registers["P"] | 0x80) if LoadedValue & 0x80 else (registers["P"] & ~0x80)
        case 0x1 : # store Instruction | st[register] [argType, arg]
            if ArgumentType >> 4 == 0x0 :
                memory[Argument] = registers[REGISTER_LookupTable[Register]]
            elif ArgumentType >> 4 == 0x1 :
                raise CPUError("Cannot store to an immediate value")
            elif ArgumentType == 0x20 :
                memory[((Argument << 8) | registers["X"]) & 0xFFFF] = registers[REGISTER_LookupTable[Register]]
            elif ArgumentType == 0x21 :
                memory[((Argument << 8) | registers["Y"]) & 0xFFFF] = registers[REGISTER_LookupTable[Register]]

        case 0x6 : # transfer register1 value to register2 | t[register1, register2]
            match Register :
                case 0x0 :
                    registers["X"] = registers["A"]
                case 0x1 :
                    registers["A"] = registers["X"]
        
                case 0x2 :
                    registers["Y"] = registers["A"]
                case 0x3 :
                    registers["A"] = registers["Y"]

                case 0x4 :
                    registers["SP"] = registers["X"]
                case 0x5 :
                    registers["X"] = registers["SP"]

            if Register != 0x4 : # transfers into SP don't affect flags on real 6502 either
                DestinationRegister = {0x0: "X", 0x1: "A", 0x2: "Y", 0x3: "A", 0x5: "X"}[Register]
                Value = registers[DestinationRegister]
                registers["P"] = (registers["P"] | 0x02) if Value == 0 else (registers["P"] & ~0x02)
                registers["P"] = (registers["P"] | 0x80) if Value & 0x80 else (registers["P"] & ~0x80)


        case 0x2 : # add with carry Instruction | adc [argType, arg] (Only uses register A)
            if ArgumentType >> 4 == 0x0 :
                Operand = memory[Argument]
            elif ArgumentType >> 4 == 0x1 :
                Operand = Argument
            elif ArgumentType == 0x20 :
                Operand = memory[((Argument << 8) | registers["X"]) & 0xFFFF]
            elif ArgumentType == 0x21 :
                Operand = memory[((Argument << 8) | registers["Y"]) & 0xFFFF]

            CarryIn = 1 if registers["P"] & 0x01 else 0
            OldA = registers["A"]
            Total = OldA + Operand + CarryIn

            registers["P"] = (registers["P"] | 0x01) if Total > 0xFF else (registers["P"] & ~0x01)

            registers["A"] = Total & 0xFF

            # Overflow: operands share a sign but the result's sign differs from theirs
            Overflow = (~(OldA ^ Operand)) & (OldA ^ registers["A"]) & 0x80
            registers["P"] = (registers["P"] | 0x40) if Overflow else (registers["P"] & ~0x40)

            registers["P"] = (registers["P"] | 0x02) if registers["A"] == 0 else (registers["P"] & ~0x02)
            registers["P"] = (registers["P"] | 0x80) if registers["A"] & 0x80 else (registers["P"] & ~0x80)
        case 0x3 : # subtract with carry Instruction | sbc [argType, arg] (Only uses register A)
            if ArgumentType >> 4 == 0x0 :
                Operand = memory[Argument]
            elif ArgumentType >> 4 == 0x1 :
                Operand = Argument
            elif ArgumentType == 0x20 :
                Operand = memory[((Argument << 8) | registers["X"]) & 0xFFFF]
            elif ArgumentType == 0x21 :
                Operand = memory[((Argument << 8) | registers["Y"]) & 0xFFFF]

            BorrowIn = 0 if registers["P"] & 0x01 else 1
            OldA = registers["A"]
            Total = OldA - Operand - BorrowIn

            # Carry means "no borrow needed" (set when the subtraction didn't go negative)
            registers["P"] = (registers["P"] | 0x01) if Total >= 0 else (registers["P"] & ~0x01)

            registers["A"] = Total & 0xFF

            Overflow = (OldA ^ Operand) & (OldA ^ registers["A"]) & 0x80
            registers["P"] = (registers["P"] | 0x40) if Overflow else (registers["P"] & ~0x40)

            registers["P"] = (registers["P"] | 0x02) if registers["A"] == 0 else (registers["P"] & ~0x02)
            registers["P"] = (registers["P"] | 0x80) if registers["A"] & 0x80 else (registers["P"] & ~0x80)

        case 0x4 : # increment Instruction | in[register]
            registers[REGISTER_LookupTable[Register]] = (registers[REGISTER_LookupTable[Register]] + 1) & 0xFF

            if registers[REGISTER_LookupTable[Register]] == 0 :
                registers["P"] |= 0x02
            else :
                registers["P"] &= ~0x02

            if registers[REGISTER_LookupTable[Register]] & 0x80 :
                registers["P"] |= 0x80
            else :
                registers["P"] &= ~0x80
        case 0x5 : # decrement Instruction | de[register]
            registers[REGISTER_LookupTable[Register]] = (registers[REGISTER_LookupTable[Register]] - 1) & 0xFF

            if registers[REGISTER_LookupTable[Register]] == 0 :
                registers["P"] |= 0x02
            else :
                registers["P"] &= ~0x02

            if registers[REGISTER_LookupTable[Register]] & 0x80 :
                registers["P"] |= 0x80
            else :
                registers["P"] &= ~0x80


        case 0xB : # bit-wise and register A by argument | and [argType, arg]
            if ArgumentType >> 4 == 0x0 :
                registers[REGISTER_LookupTable[Register]] &= memory[Argument]
            elif ArgumentType >> 4 == 0x1 :
                registers[REGISTER_LookupTable[Register]] &= Argument
            elif ArgumentType == 0x20 :
                registers[REGISTER_LookupTable[Register]] &= memory[((Argument << 8) | registers["X"]) & 0xFFFF]
            elif ArgumentType == 0x21 :
                registers[REGISTER_LookupTable[Register]] &= memory[((Argument << 8) | registers["Y"]) & 0xFFFF]

            Result = registers[REGISTER_LookupTable[Register]]
            registers["P"] = (registers["P"] | 0x02) if Result == 0 else (registers["P"] & ~0x02)
            registers["P"] = (registers["P"] | 0x80) if Result & 0x80 else (registers["P"] & ~0x80)
        case 0xC : # bit-wise xor register A by argument | eor/xor [argType, arg]
            if ArgumentType >> 4 == 0x0 :
                registers[REGISTER_LookupTable[Register]] ^= memory[Argument]
            elif ArgumentType >> 4 == 0x1 :
                registers[REGISTER_LookupTable[Register]] ^= Argument
            elif ArgumentType == 0x20 :
                registers[REGISTER_LookupTable[Register]] ^= memory[((Argument << 8) | registers["X"]) & 0xFFFF]
            elif ArgumentType == 0x21 :
                registers[REGISTER_LookupTable[Register]] ^= memory[((Argument << 8) | registers["Y"]) & 0xFFFF]

            Result = registers[REGISTER_LookupTable[Register]]
            registers["P"] = (registers["P"] | 0x02) if Result == 0 else (registers["P"] & ~0x02)
            registers["P"] = (registers["P"] | 0x80) if Result & 0x80 else (registers["P"] & ~0x80)

        case 0x7 : # push register value to stack | ph[register]
            memory[registers["SP"]] = registers[REGISTER_LookupTable[Register]]
            registers["SP"] = (registers["SP"] - 1) & 0xFF
        case 0x8 : # pop stack value to register  | pp/pl[register]
            registers["SP"] = (registers["SP"] + 1) & 0xFF
            registers[REGISTER_LookupTable[Register]] = memory[registers["SP"]]
            memory[registers["SP"]] = 0


        case 0x9 : # Control Flow Instructions
            match Register :
                case 0x0 : # jump to [0x0500] + addr | jmp [arg]
                    registers["PC"] = 0x0500 + Argument
                    Jumped = True

                case 0x1 : # jump to [0x0500] + addr (if bit[zero] in P) | jmp [arg]
                    if registers["P"] & 0x2 :
                        registers["PC"] = 0x0500 + Argument
                        Jumped = True
                case 0x2 : # jump to [0x0500] + addr (if not bit[zero] in P) | jmp [arg]
                    if not registers["P"] & 0x2 :
                        registers["PC"] = 0x0500 + Argument
                        Jumped = True

                case 0x3 : # jump to [0x0500] + addr (if bit[carry] in P) | jmp [arg]
                    if registers["P"] & 0x1 :
                        registers["PC"] = 0x0500 + Argument
                        Jumped = True
                case 0x4 : # jump to [0x0500] + addr (if not bit[carry] in P) | jmp [arg]
                    if not registers["P"] & 0x1 :
                        registers["PC"] = 0x0500 + Argument
                        Jumped = True

                case 0x5 : # jump to [0x0500] + addr (if bit[overflow] in P) | jmp [arg]
                    if registers["P"] & 0x40 :
                        registers["PC"] = 0x0500 + Argument
                        Jumped = True
                case 0x6 : # jump to [0x0500] + addr (if not bit[overflow] in P) | jmp [arg]
                    if not registers["P"] & 0x40 :
                        registers["PC"] = 0x0500 + Argument
                        Jumped = True

                case 0x7 : # jump to [0x0500] + addr (if bit[negative] in P) | jmp [arg]
                    if registers["P"] & 0x80 :
                        registers["PC"] = 0x0500 + Argument
                        Jumped = True
                case 0x8 : # jump to [0x0500] + addr (if not bit[negative] in P) | jmp [arg]
                    if not registers["P"] & 0x80 :
                        registers["PC"] = 0x0500 + Argument
                        Jumped = True

                case 0x9 : # jump to [0x0500] + addr and push return address to stack | call [subroutine]
                    ReturnAddress = registers["PC"] + 3

                    memory[registers["SP"]] = (ReturnAddress >> 8)
                    registers["SP"] = (registers["SP"] - 1)
                    memory[registers["SP"]] = ReturnAddress
                    registers["SP"] = (registers["SP"] - 1)

                    registers["PC"] = 0x0500 + Argument
                    Jumped = True
                case 0xA : # pop return address from stack to PC | return
                    registers["SP"] = (registers["SP"] + 1)
                    Low = memory[registers["SP"]]
                    memory[registers["SP"]] = 0

                    registers["SP"] = (registers["SP"] + 1)
                    High = memory[registers["SP"]]
                    memory[registers["SP"]] = 0

                    registers["PC"] = (High << 8) | Low
                    Jumped = True

        case 0xA : # compare with [argument] | cp[register] [argType, arg] | Flags set : Overflow if [register] > arg, Negative if [register] < arg, Zero if [register] == arg, Carry if [register] >= arg
            if ArgumentType >> 4 == 0x0 :
                Operand = memory[Argument]
            elif ArgumentType >> 4 == 0x1 :
                Operand = Argument
            elif ArgumentType == 0x20 :
                Operand = memory[((Argument << 8) | registers["X"]) & 0xFFFF]
            elif ArgumentType == 0x21 :
                Operand = memory[((Argument << 8) | registers["Y"]) & 0xFFFF]

            RegisterValue = registers[REGISTER_LookupTable[Register]]

            registers["P"] = (registers["P"] | 0x40) if RegisterValue > Operand else (registers["P"] & ~0x40)
            registers["P"] = (registers["P"] | 0x80) if RegisterValue < Operand else (registers["P"] & ~0x80)
            registers["P"] = (registers["P"] | 0x02) if RegisterValue == Operand else (registers["P"] & ~0x02)
            registers["P"] = (registers["P"] | 0x01) if RegisterValue >= Operand else (registers["P"] & ~0x01)


        case 0xF : # Exit Program with exit code [exit_code] | .ext [exit_code]
            sys.exit(Register)

        case _ :
            raise CPUError(f"Unknown instruction {hex(Instruction)} at {hex(registers['PC'])}")

    print()
    print(f"Registers : {registers} | First 10 bytes of RAM : {memory[0x0100:0x010A]} | Stack : {memory[0x00: 0xFF]}")
    print()

    if not Jumped :
        registers["PC"] += 3
    
    Jumped = False
    time.sleep(0.5)