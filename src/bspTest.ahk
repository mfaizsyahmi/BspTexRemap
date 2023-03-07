#NoEnv  ; Recommended for performance and compatibility with future AutoHotkey releases.
; #Warn  ; Enable warnings to assist with detecting common errors.
SendMode Input  ; Recommended for new scripts due to its superior speed and reliability.
SetWorkingDir %A_ScriptDir%  ; Ensures a consistent starting directory.
#SingleInstance force

#INCLUDE <cJSON>
#INCLUDE <keyvalues>
Class _UtilBase {
    #INCLUDE <_UtilBase/Array>
}
Class Util extends _UtilBase {
}
#INCLUDE <Path> ; path manipulation library
#INCLUDE <Materials> ; uses the above
#INCLUDE <BspFile>

TESTFILE := A_ScriptDir "\trainlighttest.bsp"
TESTFILE := "H:\SteamLibrary\steamapps\common\Half-Life\valve_downloads\maps\caldera_jungle.bsp"

fpBsp := FileOpen(TESTFILE, "rw")
testBsp := new BspFile(fpBsp)

; TEST ENUM Lump directory (offset and length)
MSGTEXT := "Lump`tOffset`tLength`n"
for i, lumpDir in testBsp.LumpDirectory
    MSGTEXT .= Format("{}`t{}`t{}`n", i-1, lumpDir*)
MsgBox,,% testBsp.version, %MSGTEXT%

; dump texture list
; MSGTEXT := "      Name      `tWidth`tHeight`tEmbedded?`n"
; for _, texInfo in testBsp.Textures
;     MSGTEXT .= Format("{2:-16s}`t{3: 3i}`t{4: 3i}`t{5}`n", texInfo*)
; MsgBox,,Textures, %MSGTEXT%

; test paths
testPathObj := new Path(TESTFILE)
MsgBox % Format("
(C
get[] =`n{}
get[-1] =`n{}
parent =`n{}
parents[2] =`n{}
parents[2].withName =`n{}
parents[2].withName.joinpath =`n{}
relativeTo = `n{}
; relativeTo with nonmatch = `n{}
)"	,testPathObj.get()
	,testPathObj.get(-1)
	,testPathObj.parent.get()
	,testPathObj.parents[2].get()
	,testPathObj.parents[2]
		.withName("valve").get() 
	,testPathObj.parents[2]
		.withName("valve").joinpath("sound\materials.txt").get()
	,testPathObj.relativeTo("H:\SteamLibrary\steamapps\common\Half-Life").get() )
;	,testPathObj.relativeTo("D:\FarEast\sh").get() )

; routine to find materials.txt
bspPathObj := testPathObj
if (bspPathObj.get(-1) = "maps") {
	modname := RegExReplace(bspPathObj.get(-2), "_(?:downloads|addon)$")
	matPathObj := bspPathObj.parents[2].withName(modname).joinpath("sound\materials.txt")
	MsgBox % matPathObj.get() "`n" matPathObj.exists()
}


fpBsp.Close()