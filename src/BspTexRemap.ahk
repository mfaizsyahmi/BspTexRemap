GLOBAL APPNAME := A_ScriptName, VERSION := "0.1a"
;@Ahk2Exe-Let U_version = %A_PriorLine~U)^(.+"){1}(.+)".*$~$2%
;@Ahk2Exe-SetVersion %U_version%
GLOBAL BANNER := Format("
(
{1}
  version {2}
  (c) M Faiz Syahmi @ kimilil, 2023

)", APPNAME, VERSION)
, ABOUT := "
(C
ABOUT
This program patches a BSP file, replacing names of embedded textures to those
in a given materials.txt, to try and eliminate the need to edit or ship a
modified materials.txt, thus increasing map portability.
The match and replacement textures are defined in a info_texture_remap entity
placed in the map, or in a ""<mapname>_custommat.txt"" alongside the map file,
or supplied in an external file.

USAGE
  BspTexRemap [options] filePath

  Arguments:
    -h | -help      show this help menu and exit
    -log LEVEL      logging level (off|error|warn|info|verbose) (default:error)
    -low | -high    set process priority level
    -backup         makes backup of BSP file
    -dump_texinfo VAL1+VAL2+...+VALN
                    creates a file with names of textures used in the map
                    (embedded|external|all|grouped|uniquegrouped)
    -materials_path FILE
                    defines path to materials.txt for reference
    -custommat_path FILE
                    file with custom texture's materials
                    (used if info_texture_remap is absent)
;    -replace_method VAL
;                    how to replace texture names (prefix|exact)
    filePath        file to operate

LICENSE
  THE MIT LICENSE
  see BspTexRemap_license.txt
)"
, ENTITY_CLASSNAME := "info_texture_remap"
; COMPILE TOOLS CONVENTION
; - be a console app
; - respect the CWD, cannot SetWorkingDir
; - map names are usually passed WITHOUT the extension

;@Ahk2Exe-ExeName %A_ScriptDir%\..\%A_ScriptName%
;@Ahk2Exe-ConsoleApp
#NoEnv  ; Recommended for performance and compatibility with future AutoHotkey releases.
; #Warn  ; Enable warnings to assist with detecting common errors.
;@Ahk2Exe-IgnoreBegin
Menu, Tray, Icon, % A_ScriptDir "\" SubStr(A_ScriptName,1,-3) "_64.ico"
;@Ahk2Exe-IgnoreEnd
#NoTrayIcon
;@Ahk2Exe-SetMainIcon %A_ScriptDir%\BspTexRemap_64.ico
/*ahk2exe-keep
*/

#INCLUDE <cJSON>
#INCLUDE <ScriptingDictionary> ; using this to preserve entity entry order
#INCLUDE <keyvalues>
VKV.ObjectFactory := ScriptingDictionary
Class _UtilBase {
	#INCLUDE <_UtilBase/Array>
}
Class Util extends _UtilBase {
	DeepCopy(obj) {
		return JSON.Load(JSON.dump(obj))
	}
}
#INCLUDE <Path> ; path manipulation library
#INCLUDE <Materials> ; uses the above
#INCLUDE <BspFile>

;@Ahk2Exe-IgnoreBegin
;DllCall("AllocConsole")
ATTACH_PARENT_PROCESS = 0x0ffffffff
DllCall("AttachConsole", "UInt", ATTACH_PARENT_PROCESS)
;@Ahk2Exe-IgnoreEnd

#INCLUDE <Console> ; provides standard stream output and logging 
; Console.[Verbose|Info|Warn|Error] -- prints log message
; Console.[Banner|Help]             -- prints banners|log

DumpTexInfo(fp,texInfoList,level:=0, extraList:="") {
	static levelMap := {embedded:1,external:2,all:3,grouped:4,uniquegrouped:8}
	, descMap := {1:"Embedded", 2:"External"
		, 4:"Texture groups (for materials.txt)"
		, 8:"Unique texture groups (for materials.txt)" }
	; this allows string add e.g. all+grouped
	if (level ~= "[\w\+]+") {
		levelNum := 0
		for _, levelPart in StrSplit(level,"+")
			if levelMap.HasKey(levelPart)
				levelNum |= levelMap[levelPart]
		level := levelNum
	}
	
	Console.VerboseF("Dumping texture list (level: {})", level)
	
	loopMap := [[1,"Embedded",1],[2,"External",0]]
	for _, loopCfg in loopMap
	{
		if !(level&loopCfg[1])
			continue
		Console.VerboseF("Dumping texture list {}: {}", loopCfg[1], loopCfg[2])
		fp.WriteLine("// " loopCfg[2])
		for _, texItem in texInfoList
			if texItem[5] = loopCfg[3]
				fp.WriteLine(texItem[2])
		fp.WriteLine() ; blank line at the end
	}
	If (level&4) {
		Console.VerboseF("Dumping texture list {}: {}", 4, descMap[4])
		fp.WriteLine("// " descMap[4])
		groupList := Materials.GetNameGroups(texInfoList)
		fp.WriteLine(Util.Array.Join(groupList,"`n") . "`n")
	}
	If (level&8 && extraList[8]) {
		Console.VerboseF("Dumping texture list {}: {}", 8, descMap[8])
		fp.WriteLine("// " descMap[8])
		fp.WriteLine(Util.Array.Join(extraList[8],"`n") . "`n")
	}
}

; parse arguments
RE_ARG_SWITCHES := "i)(?<=^-)(low|high|h(elp)?|backup)$"
,RE_ARG_PROPS := "i)(?<=^-)(log|(?:match|replace)_method|(?:materials|custommat)_path|dump_texinfo)$"
,CFG := {log: Console.LOG_BANNER|1, paths:[]} ; defaults
for _, arg in A_Args
{
	 RegExMatch(arg, RE_ARG_SWITCHES, switches)
	,RegExMatch(arg, RE_ARG_PROPS, props)

	if nextVal {
		CFG[nextVal] := arg
		nextVal := ""
	}
	else if (switches ~= "low|high")
		Process, Priority, , % switches
	else if switches
		CFG[switches] := true
	else if props
		nextVal := props
	else {
		; special path parsing, as compile tools usually get passed a filename
		; WITHOUT the extension
		fullPath := "" ; reset in case previous path got carried over
		SplitPath, arg, name, dir
		Loop, files, %dir%, D
			fullPath := A_LoopFileLongPath ; resolve to long paths
		if fullPath {
			 fullPath .= "\" name . (name ~= "i)\.bsp$" ? "" : ".bsp")
			,CFG.paths.push(fullPath)
		}
	}
}

;@Ahk2Exe-IgnoreBegin
FileDelete wtf.txt
FileAppend, % JSON.Dump(CFG), wtf.txt
;@Ahk2Exe-IgnoreEnd

; set log level
Console.logLevel := CFG.log ; ? CFG.log : Console.LOG_VERBOSE
; print banner/help
If (!CFG.paths.length() || CFG.h || CFG.help) {
	Console.Banner()
	Console.Help()
	If !CFG.paths.length()
		ExitApp, 24
	Else
		ExitApp, 0
} Else If (Console.logLevel >= 3)
	Console.Banner()

for _, bspPath in CFG.paths {
	bspPathObj := new Path(bspPath)
	if (!FileExist(bspPath)) {
		Console.Warn(Format("File does not exist: ""{}""",bspPath))
		continue
	}
	else if (SubStr(bspPath, -3) != ".bsp") {
		Console.Warn(Format("Incorrect file extension: ""{}""",bspPath))
		continue
	}

	; make backup
	If (CFG.backup) {
		bakPath := bspPath ".bak"
		Console.Info(Format("Backing up file: ""{}""", bakPath))
		FileCopy, % bspPath, % bakPath
		If ErrorLevel
			Console.Warn(Format("Error on file copy: ""{}""`n-- {}"
				, bakPath, ErrorLevel))
	}
		
	; start opening file
	Console.InfoF("Open file: ""{}""",bspPath)
	try {
		thisBsp := new BspFile(bspPath)
	} catch e {
		Console.Error(Format("ERROR parsing file: ", e.message))
		thisBsp := "" ; force the open file handle to close
		continue
	}
	
	; look for info_texture_remap entity[ies] in map
	texRemapEntities := []
	for _, entItem in thisBsp.Entities
		if (entItem.classname = ENTITY_CLASSNAME) {
			Console.VerboseF("Found {}", ENTITY_CLASSNAME)
			texRemapEntities.Push(entItem)
		}
	
	entTargetMatList := Materials.MATLIST_TEMPLATE
	; early assembly of materials list if found in info_texture_remap entity
	matCharsRe := "[" Materials.MVDSTGWPY "](?=#\d+$)?"
	For _, entTexRemap in texRemapEntities
		for key, value in entTexRemap
			If (key ~= matCharsRe)
				(target := entTargetMatList[SubStr(key,1,1)]) ? target.Push(value) : 0
	
	; try find materials.txt file
	Console.Verbose("Start finding materials.txt file")
	matPath := Materials.SearchForFile(bspPath, CFG, texRemapEntities)
	If (!matPath) {
		Console.Error("No materials.txt file found. Processing cannot continue.")
		Continue
	}
	Console.InfoF("Found materials.txt file: ""{}""", matPath)

	; load the materials file
	entriesLoaded := Materials.GetEntries(matPath, matList, matListGood)
	Console.InfoF("{} entries loaded from materials.txt", entriesLoaded)
	for mat in matList
		Console.VerboseF("{1}: {2: 3u}/{3: 3u} (usable/total)"
			, mat, matListGood[mat].Length(), matList[mat].Length())
	
	bspTexGroups := Materials.GetNameGroups(thisBsp.Textures)
	Console.InfoF("{} texture groups in map", bspTexGroups.length())
	
	bspTexGroups := Materials.FilterUsedNames(matList, bspTexGroups)
	Console.InfoF("{} texture groups not in materials.txt", bspTexGroups.length())
	
	; dump tex info
	If (CFG.dump_texinfo) {
		dumpPath := bspPathObj.withName(bspPathObj.stem "_texinfo.txt").get()
		texDumpFp := fileOpen(dumpPath, "w`n")
		texDumpFp.Write(Format("// Texture List for {}`n// Generated by {}`n`n"
			, bspPathObj.name, A_ScriptName))
		DumpTexInfo(texDumpFp, thisBsp.Textures, CFG.dump_texinfo, {8:bspTexGroups})
		texDumpFp.Close()
		Console.InfoF("Dumped texture list to: ""{}""", dumpPath)
	}
	
	; now load the remappable texture material list
	entWannabeMatList := Materials.MATLIST_TEMPLATE
	For _, entTexRemap in texRemapEntities
		for texname, targetMat in entTexRemap
			If (!(targetMat ~= Materials.ENTITY_RESERVED_PROPS)
			&& InStr(Materials.MATCHARS, targetMat)
			&& target := entWannabeMatList[targetMat]
			&& !Util.Array.Has(target, texname))
				target.Push(texname)
	If (entMatEntryCount := Materials.CountEntries(entWannabeMatList))
		Console.InfoF("{} material entries loaded from {}", entMatEntryCount, ENTITY_CLASSNAME)
	
	; load from external materials file (cmd line)
	If FileExist(CFG.custommat_path) {
		Console.InfoF("Loading custom material entries from: ""{}""", CFG.custommat_path)
		Materials.GetEntries(matPath, extWannabeMatList)
		Console.InfoF("{} custom material entries loaded."
			, Materials.CountEntries(extWannabeMatList))
	}
			
	; load from external materials file (relative to bsp file)
	relMatFile := bspPathObj.withName(bspPathObj.stem "_custommat.txt")
	If (relMatFile.exists()) {
		Console.InfoF("Loading custom material entries from: ""{}""", relMatFile.get())
		Materials.GetEntries(relMatFile.get(), extWannabeMatList)
		Console.InfoF("{} custom material entries loaded."
			, Materials.CountEntries(extWannabeMatList))
	}
	; combine the lists
	wannabeMatList := Materials.CopyMatList(entWannabeMatList)
	Materials.MergeMatList(wannabeMatList, extWannabeMatList)
	Console.InfoF("{} total custom material entries."
			, Materials.CountEntries(wannabeMatList))
	
	; start looking into replacing names
	newBspTexList := Util.DeepCopy(thisBsp.Textures)
	suffixChars := StrSplit(Materials.CHARSEQUENCE)
	enumTracker := {} ; for generating the random suffix chars 
	for _, bspTexGroupName in bspTexGroups
	{
		if (targetMat := Materials.GetMatType(wannabeMatList, bspTexGroupName)) {
			Console.VerboseF("{:- 16s} wants to be mattype {}"
				, bspTexGroupName, targetMat)
			; check that there are material name candidates for this
			If (!matListGood[targetMat].Length()) {
				Console.WarnF("No suitable replacement texgroup found for material {1:U}!"
					. "`n-- Skipped: {2:Us}" , targetMat, bspTexGroupName)
				Continue
			}
				
			; grabs a sample texture name to find the prefix length
			for _, texItem in thisBsp.Textures
				if (pos:=InStr(texItem[2],bspTexGroupName)) {
					if (pos>3) { ; prefix >=3 cannot be renamed, no space for suffix!
						Console.WarnF("" 
	. "Texgroup {1:- 15Us} cannot be renamed! Prefix on ""{2:- 16s}"" is too long."
	. "`n-- Skipped {1:Us}", bspTexGroupName, texItem[2])
						Continue, 2
					
					} Else If (texItem[2] ~= Materials.IGNOREPATTERN) {
						Console.WarnF("Texture ""{2:- 16s}"" flagged unsuitable."
							. "`n-- Skipped {1:Us}", bspTexGroupName, texItem[2])
						Continue, 2
					}
				}
					
			(enumTracker.HasKey(targetMat))
				? thisEnum := ++enumTracker[targetMat]
				: thisEnum := enumTracker[targetMat] := 1
				
			; check rollovers
			If (thisEnum > suffixChars.Length()) {
				matListGood[targetMat].removeAt(1)
				thisEnum := enumTracker[targetMat] := 1
			}
			; check AGAIN that there are material name candidates for this
			If (!matListGood[targetMat].Length()) {
				Console.WarnF("No suitable replacement texgroup found for material {1:U}!"
					. "`n-- Skipped: {2:Us}" , targetMat, bspTexGroupName)
				Continue
			}
			
			targetTexName := SubStr(matListGood[targetMat][1]
					. StrReplace("~~~~~","~",suffixChars[thisEnum])
				,1,15) 
			
			Materials.GroupRename(newBspTexList, bspTexGroupName, targetTexName)
		}
	}
	
	; count changed textures
	; print old -> new tex names
	changedCount := 0
	Console.Verbose("`n----------- replacement map -------------")
	for i in newBspTexList 
	{
		Console.VerboseF("  {:- 15s} --> {:- 15s}"
			, thisBSP.textures[i][2], newBspTexList[i][2])
		If (thisBSP.textures[i][2] != newBspTexList[i][2])
			changedCount++
	}
	If changedCount
		Console.InfoF("{} textures changed and will be written.", changedCount)
	Else {
		Console.InfoF("No textures changed. Skipping file.`n")
		Continue
	}
	
	; FileDelete, DEBUG.txt
	; FileAppend, % JSON.Dump(thisBsp.Textures) "`n`n"  JSON.Dump(newBspTexList) 
	; 	,DEBUG.txt

	Console.InfoF("Writing changes to file...", changedCount)
	thisBsp.Textures := newBspTexList
	thisBsp.WriteChanges()
	Console.InfoF("DONE.`n", changedCount)
	
}

OnExit() {
	;@Ahk2Exe-IgnoreBegin
	DllCall("FreeConsole")
	;@Ahk2Exe-IgnoreEnd
}