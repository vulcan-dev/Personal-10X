from N10X import Editor as Ed

# Modify these based on your project:
ARCH_MAX_INT = 8
IS_GCC_OLDER_THAN_14_2 = False # Only change this if it's true, and if you're using GCC.

# This was a pain to write.

############################################################
########## Notes
############################################################
"""
Language C
  Bool
    GCC   - 1 (Trunk GCC, 14.2 results in 4)
    MSVC  - 1
    Clang - 1

  True/False
    GCC   - 4 (If you don't include stdbool.h, then it results in 1)
    MSVC  - 4
    Clang - 4

Restrictions:
  - The custom types must be in the same file unless you have already added them to the map by clicking on it or a variable

Issues:
```
void foo() { int c = 1; }
                 ^
will result in the types: ['void', 'foo()', '{', 'int']
this means it will call `ExtractInfoFromLine`
```


"""

IS_DRAGGING = False

############################################################
########## Symbols
############################################################
SymbolMap = {
    "bool":        1,
    "char":        1,
    "short":       2,
    "int":         4,
    "float":       4,
    "double":      8,
    "wchar_t":     2
}

SymbolMap_X64 = {
    "long":        8,
    "size_t":      8
}

SymbolMap_X86 = {
    "long":        4,
    "size_t":      4
}

SymbolMap = SymbolMap | SymbolMap_X64 if ARCH_MAX_INT == 8 else SymbolMap | SymbolMap_X86

############################################################
########## Functions
############################################################
def FindSymbolByName(SymbolName):
    """
    Returns tuple (Column, Line)
    """
    FileContents = Ed.GetFileText()
    Lines = FileContents.split('\n')
    
    for LineNum, Line in enumerate(Lines):
        ColPos = Line.find(SymbolName)
        if ColPos != -1:
            # Found the symbol
            return (ColPos, LineNum)
            
    return (-1, -1)  # Not found

def CalculateTypePositionsInLine(Line, Types):
    LeadingSpaces = len(Line) - len(Line.lstrip())
    CurrentPosition = LeadingSpaces
    TypePositions = {}
        
    for Type in Types:
        TypePosition = Line.find(Type, CurrentPosition)
        TypePositions[Type] = TypePosition
        CurrentPosition = TypePosition + len(Type)
    return TypePositions

def GetWordInLineFromCursorPosition(Line):
    CursorPosX, _ = Ed.GetCursorPos()

    Start = max(Line.rfind(' ', 0, CursorPosX), Line.rfind('(', 0, CursorPosX)) + 1
    End = min((pos for pos in (Line.find(' ', CursorPosX), Line.find('(', CursorPosX), Line.find(')', CursorPosX)) if pos != -1), default=len(Line))
    return Line[Start:End]

def ExtractInfoFromLine(Line, IsTypedef=False, IsVariable=False, TypeToAdd=None):
    Declaration = Line.split("=")[0].strip()
    Parts = Declaration.split()
    Types = Parts[:-1]
    Size = 0

    TypePositions = CalculateTypePositionsInLine(Line, Types)

    # We pressed on a typedef
    if IsTypedef:
        if len(Types) >= 2 and (Types[1] == "signed" or Types[1] == "unsigned"):
            Types = Types[2:] # typedef signed
        else:
            Types = Types[1:] # typedef

        if TypeToAdd is None:
            # Extract Name
            # ['typedef', 'double', 'f64']
            #                        ^
            TypeToAdd = Parts[-1]

        for Type in Types:
            if Type in SymbolMap:
                SymbolMap[TypeToAdd] = SymbolMap[Type]
                Size += SymbolMap[TypeToAdd]
            else:
                # We are now here: typedef   f64             test;
                #                            ^
                SymbolPosition = FindSymbolByName(Type)
                if SymbolPosition[0] != -1 and SymbolPosition[1] != -1:
                    Definition = Ed.GetSymbolDefinition(SymbolPosition)
                    Size = ExtractInfoFromLine(Definition, IsTypedef=True)

        return Size
    # We pressed on a variable
    elif IsVariable:
        for Type in Types:
            # Check if that type is already defined
            if Type in SymbolMap:
                Size += SymbolMap[Type]
            # That type is not defined, let's find it
            else:
                _, LinePosition = Ed.GetCursorPos()
                TypePosition = TypePositions[Type]
                Definition = Ed.GetSymbolDefinition((TypePosition, LinePosition))
                Size += ExtractInfoFromLine(Definition, IsTypedef=True, TypeToAdd=Type)

    return Size

def LocateSize(CursorPos):
    SymbolType = Ed.GetSymbolType(CursorPos)
    SymbolDef = Ed.GetSymbolDefinition(CursorPos)
    if SymbolType == "":
        return
    ProcessedLine = Ed.GetPreprocessedLine()
    if ProcessedLine == "":
        return
    
    Size     = 0
    Types    = []
    Variable = ""

    Word = GetWordInLineFromCursorPosition(ProcessedLine)
    
    if SymbolDef != "":
        if SymbolType == "Typedef":
            ProcessedLine = SymbolDef
            Size = ExtractInfoFromLine(ProcessedLine, IsTypedef=True)
        elif SymbolType == "Variable" or SymbolType == "MemberVariable":
            ToExtract = ""

            OpenBracket = ProcessedLine.find('(')
            if OpenBracket != -1: # Function
                _, CursorPosY = Ed.GetCursorPos()
                Start = OpenBracket-1 # Todo: Actually find the start, it might be "void foo ("
                Type = Ed.GetSymbolType((OpenBracket-1, CursorPosY))
                if Type == "FunctionDefinition":
                    # This for example: void foo(int v0, char v1, wchar_t p) { int c = 1; wchar_t f = 2; }
                    CursorPosX, CursorPosY = Ed.GetCursorPos()
                    SymbolAtCursor = Ed.GetSymbolType((CursorPosX, CursorPosY))
                    
                    if SymbolAtCursor == "Variable":
                        VarDefinition = Ed.GetSymbolDefinition((CursorPosX, CursorPosY))
                        ToExtract = VarDefinition
            else:
                # Allow  this to work: long long f = 4; char ad = "c";
                Split = ProcessedLine.split(";")[:-1]
                ToExtract = Split[0]
            
                for i, Section in enumerate(Split):
                    if Word in Section:
                        ToExtract = Split[i]
                        break
            
            Size = ExtractInfoFromLine(ToExtract, IsVariable=True)
        else:
            return
    else:
        # We have the cursor position, and we have the line. Get the current word and get the type
        #               long long d=4;
        #    we might be ^ or ^, so let's find the word

        if Word in SymbolMap:
            Size = SymbolMap[Word]
        else:
            Size = 0

    if Size >= ARCH_MAX_INT:
        Size = ARCH_MAX_INT

    if Size > 0:
        Ed.SetStatusBarText(f"{Size}bytes")
    else:
        Ed.SetStatusBarText("")

def PrintSymbolSizes():
    print(SymbolMap)

LastCursor = (0, 0)
def SZ_Update():
    global LastCursor

    if Ed.GetCursorCount() == 0: # Prevent crash when right clicking
        return

    CursorPos = Ed.GetCursorPos(0)
    if not IS_DRAGGING and LastCursor != CursorPos and Ed.GetCurrentFilename() and not Ed.IsCommandPanelOpen():
        # "and not Ed.IsCommandPanelOpen()" - Fix crash when opening command panel
        LastCursor = CursorPos
        LocateSize(CursorPos)

def SZ_MouseSelectStartedFunction(Pos):
    global IS_DRAGGING
    IS_DRAGGING = True

def SZ_MouseSelectFinishedFunction(Pos):
    global IS_DRAGGING
    IS_DRAGGING = False

Ed.AddUpdateFunction(SZ_Update)
Ed.AddMouseSelectStartedFunction(SZ_MouseSelectStartedFunction)
Ed.AddMouseSelectFinishedFunction(SZ_MouseSelectFinishedFunction)