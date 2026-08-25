import pygame, sys, os

class CPUError(Exception) :
    pass

class PPU() :
    def __init__(self) :
        self.display = pygame.display.set_mode((160 * 5, 144 * 5))
        pygame.display.set_caption("GBP Test Display")

        self.pixelBuffer = [[0 for i in range(160)] for i in range(144)]

        self.SpriteAtributes = []

        self.CHR_Data_Memory = [0] * (51 * 8)
        with open(Character_Data, "rb") as chr_data :
            SpriteData = chr_data.read()
            for I, byte in enumerate(SpriteData) :
                self.CHR_Data_Memory[I] = byte

    def SetPxBuffer(self) :
        self.SpriteAtributes = []
        self.pixelBuffer = [[0 for i in range(160)] for i in range(144)]

        for I, byte in enumerate(memory[0x0500:0x05FF]) :
            self.SpriteAtributes.append(byte)

            if (I + 1) % 4 == 0 and I > 0 :
                x, y, tileIndex, Flags = self.SpriteAtributes

                if Flags & 0x1 == 1 :
                    self.SpriteAtributes = []
                    continue

                Sprite = self.CHR_Data_Memory[tileIndex:tileIndex+8] 

                for Yoffset, byte in enumerate(Sprite) :
                    for Xoffset, bit in enumerate(f"{byte:08b}") :
                        if bit == "1" :
                            if Xoffset + x < 160 and Yoffset + y < 144 :
                                self.pixelBuffer[Yoffset + y][Xoffset + x] = 1

                self.SpriteAtributes = []

    def render(self) :
        self.display.fill((155, 188, 15))

        for Yoffset, row in enumerate(self.pixelBuffer) :
            for Xoffset, pixel in enumerate(row) :
                if pixel == 1 :
                    pygame.draw.rect(self.display, (15, 56, 15), pygame.Rect(Xoffset * 5, Yoffset * 5, 5, 5))
        pygame.display.flip()

memory = bytearray(0x10000)
"""
0000 - 03FF : Free RAM

0400 - 04FF : Stack

0500 - 05FF : Zero Page

ROM data can start anywhere (preferably from 0600 - EFFF)

F000 - FFFF : I/O
"""

registers = {
    "A": 0, "X": 0, "Y": 0,

    "SP": 0x04FF,
    "PC": 0x0000,

    "P": 0x20
}

REGISTER_LookupTable = {
    0x1: "A", 0x2: "X", 0x3: "Y"
}

GBP_Buttons = {
    "UP": pygame.K_z, "DOWN": pygame.K_s, 
    "LEFT": pygame.K_q, "RIGHT": pygame.K_d, 
    "A": pygame.K_k, "B": pygame.K_o, 
    "START": pygame.K_v, "SELECT": pygame.K_b
}

Jumped = False

program = []
Signature = ""
ContinueCheck = False

cartridge = input("Please Enter A Cartridge File : ")
if len(os.listdir(cartridge)) > 1 : Character_Data, ROM_File = os.listdir(cartridge)
else : ROM_File = os.listdir(cartridge)[0]
os.chdir(cartridge)

ppu = PPU()

with open(ROM_File, "rb") as ROM :
    for byte in ROM.read() :
        program.append(byte)

for I, byte in enumerate(program) :
    if byte == 0xF0 :
        for byte in program[I+1:] :
            if Signature == "PYGBP" :
                ContinueCheck = True
            elif len(Signature) < 5 :
                Signature += chr(byte)
                continue
    elif byte == 0xF1 :
        ProgramVer = program[I+1]

        if ProgramVer < 2 :
            raise CPUError("This Version Of NES_6502 ASM Is 6502 ASM. Please Upgrade Your Code.")
    elif byte == 0xF2 :
        ProgramStart = (program[I+1] << 8) | (program[I+2] << 0)

    if byte == 0xFF :
        break

    if not ContinueCheck :
        sys.exit(1)

for i, byte in enumerate(program[I+1:]) :
    memory[ProgramStart+i] = byte
registers["PC"] = ProgramStart

clock = pygame.time.Clock()

running = True

while registers["PC"] < len(memory) and running :
    clock.tick(120)
    for event in pygame.event.get() :
        if event.type == pygame.QUIT :
            running = False
            break

    keys = pygame.key.get_pressed()
    
    controllerBits = ""
    for button in GBP_Buttons :
        if keys[GBP_Buttons[button]] :
            controllerBits += "1"
        else :
            controllerBits += "0"

    memory[0xF000] = int(controllerBits[::-1], 2)

    Instruction, Register = (memory[registers["PC"]] & 0xF0) >> 4, (memory[registers["PC"]] & 0x0F) >> 0

    ArgumentType, Argument = memory[registers["PC"]+1], memory[registers["PC"]+2]

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


        case 0xC :
            match Register :
                case 0x0 : # bit-wise and register A by argument | and [argType, arg]
                    if ArgumentType >> 4 == 0x0 :
                        registers["A"] &= memory[Argument]
                    elif ArgumentType >> 4 == 0x1 :
                        registers["A"] &= Argument
                    elif ArgumentType == 0x20 :
                        registers["A"] &= memory[((Argument << 8) | registers["X"]) & 0xFFFF]
                    elif ArgumentType == 0x21 :
                        registers["A"] &= memory[((Argument << 8) | registers["Y"]) & 0xFFFF]

                    Result = registers["A"]
                    registers["P"] = (registers["P"] | 0x02) if Result == 0 else (registers["P"] & ~0x02)
                    registers["P"] = (registers["P"] | 0x80) if Result & 0x80 else (registers["P"] & ~0x80)
                case 0x1 : # bit-wise xor register A by argument | eor/xor [argType, arg]
                    if ArgumentType >> 4 == 0x0 :
                        registers["A"] ^= memory[Argument]
                    elif ArgumentType >> 4 == 0x1 :
                        registers["A"] ^= Argument
                    elif ArgumentType == 0x20 :
                        registers["A"] ^= memory[((Argument << 8) | registers["X"]) & 0xFFFF]
                    elif ArgumentType == 0x21 :
                        registers["A"] ^= memory[((Argument << 8) | registers["Y"]) & 0xFFFF]

                    Result = registers["A"]
                    registers["P"] = (registers["P"] | 0x02) if Result == 0 else (registers["P"] & ~0x02)
                    registers["P"] = (registers["P"] | 0x80) if Result & 0x80 else (registers["P"] & ~0x80)

                case 0x2 : # shift right | shr [argType, arg]
                    if ArgumentType >> 4 == 0x0 :
                        Operand = memory[Argument]
                    elif ArgumentType >> 4 == 0x1 :
                        Operand = Argument
                    elif ArgumentType == 0x20 :
                        Operand = memory[((Argument << 8) | registers["X"]) & 0xFFFF]
                    elif ArgumentType == 0x21 :
                        Operand = memory[((Argument << 8) | registers["Y"]) & 0xFFFF]

                    RegVal = registers["A"]

                    if Operand > 0 :
                        CarryOut = (RegVal >> (Operand - 1)) & 1
                    else :
                        CarryOut = registers["P"] & 0x01

                    registers["A"] = RegVal >> Operand

                    registers["P"] = (registers["P"] | 0x01) if CarryOut else (registers["P"] & ~0x01)

                    Result = registers["A"]
                    registers["P"] = (registers["P"] | 0x02) if Result == 0 else (registers["P"] & ~0x02)
                    registers["P"] = (registers["P"] | 0x80) if Result & 0x80 else (registers["P"] & ~0x80)

                case 0x3 : # shift left | shl [argType, arg]
                    if ArgumentType >> 4 == 0x0 :
                        Operand = memory[Argument]
                    elif ArgumentType >> 4 == 0x1 :
                        Operand = Argument
                    elif ArgumentType == 0x20 :
                        Operand = memory[((Argument << 8) | registers["X"]) & 0xFFFF]
                    elif ArgumentType == 0x21 :
                        Operand = memory[((Argument << 8) | registers["Y"]) & 0xFFFF]

                    RegVal = registers["A"]
                    Shifted = RegVal << Operand

                    CarryOut = 1 if (Shifted >> 8) else 0

                    registers["A"] = Shifted & 0xFF

                    registers["P"] = (registers["P"] | 0x01) if CarryOut else (registers["P"] & ~0x01)

                    Result = registers["A"]
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
                case 0x0 : # jump to [ProgramStart] + addr | jmp [arg]
                    registers["PC"] = ProgramStart + Argument
                    Jumped = True

                case 0x1 : # jump to [ProgramStart] + addr (if bit[zero] in P) | bez [arg]
                    if registers["P"] & 0x2 :
                        registers["PC"] = ProgramStart + Argument
                        Jumped = True
                case 0x2 : # jump to [ProgramStart] + addr (if not bit[zero] in P) | bnz [arg]
                    if not (registers["P"] & 0x2) :
                        registers["PC"] = ProgramStart + Argument
                        Jumped = True

                case 0x3 : # jump to [ProgramStart] + addr (if bit[carry] in P) | bcs [arg]
                    if registers["P"] & 0x1 :
                        registers["PC"] = ProgramStart + Argument
                        Jumped = True
                case 0x4 : # jump to [ProgramStart] + addr (if not bit[carry] in P) | bcc [arg]
                    if not (registers["P"] & 0x1) :
                        registers["PC"] = ProgramStart + Argument
                        Jumped = True

                case 0x5 : # jump to [ProgramStart] + addr (if bit[overflow] in P) | bos [arg]
                    if registers["P"] & 0x40 :
                        registers["PC"] = ProgramStart + Argument
                        Jumped = True
                case 0x6 : # jump to [ProgramStart] + addr (if not bit[overflow] in P) | boc [arg]
                    if not (registers["P"] & 0x40) :
                        registers["PC"] = ProgramStart + Argument
                        Jumped = True

                case 0x7 : # jump to [ProgramStart] + addr (if bit[negative] in P) | bns [arg]
                    if registers["P"] & 0x80 :
                        registers["PC"] = ProgramStart + Argument
                        Jumped = True
                case 0x8 : # jump to [ProgramStart] + addr (if not bit[negative] in P) | bnc [arg]
                    if not (registers["P"] & 0x80) :
                        registers["PC"] = ProgramStart + Argument
                        Jumped = True

                case 0x9 : # jump to [ProgramStart] + addr and push return address to stack | call [subroutine]
                    ReturnAddress = (registers["PC"] + 3) - ProgramStart

                    memory[registers["SP"]] = ReturnAddress
                    registers["SP"] -= 1

                    registers["PC"] = ProgramStart + Argument
                    Jumped = True
                case 0xA : # pop return address from stack to PC | return
                    registers["SP"] += 1
                    ReturnAddress = (memory[registers["SP"]] + ProgramStart) + 3

                    memory[registers["SP"]] = 0

                    registers["PC"] = ReturnAddress
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

            if RegisterValue > Operand :
                registers["P"] |= 0x40
            else : 
                registers["P"] &= ~0x40

            if RegisterValue < Operand :
                registers["P"] |= 0x80
            else :
                registers["P"] &= ~0x80

            if RegisterValue == Operand :
                registers["P"] |= 0x02
            else :
                registers["P"] &= ~0x02

            if RegisterValue >= Operand :
                registers["P"] |= 0x01
            else :
                registers["P"] & ~0x01

        case 0xE : # clear | cl[Part Of P to clear (c clears all)]
            match Register :
                case 0x0 : # clear all
                    registers["P"] = 0
                case 0x1 : # clear carry
                    registers["P"] &= ~0x01
                case 0x2 : # clear negative
                    registers["P"] &= ~0x08
                case 0x3 : # clear overflow
                    registers["P"] &= ~0x04
                case 0x4 : # clear zero
                    registers["P"] &= ~0x02

        case 0xF : # Exit Program with exit code [exit_code] | .ext [exit_code]
            sys.exit(Register)

    if not Jumped :
        registers["PC"] += 3

    """print()
    print(f"Registers : {registers} | Zero Page : {memory[0x0500:0x05FF]}")
    print()"""
    
    Jumped = False

    ppu.SetPxBuffer()
    ppu.render()