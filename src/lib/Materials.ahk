; REQUIRES:
;	Util.Array class
;	Path class
;	Console class

Class Materials {
	static MATCHARS := "MVDSTGWPY"
	, TEXNAMEPARTS_RE := "Oi)(?P<prefix>[!@{]?(?:-\d|\+[0-9a-z])?~?)?(?P<texname>.*)"
	, IGNOREPATTERN := "i)^(sky|{blue|{invisible|black|aaatrigger|scroll.*)"
	, CHARSEQUENCE := "~}|{``_^]\[@?>=<;:/.-,+*)(&%$#!ZYXWVUTSRQPONMLKJIHGFEDCBA9876543210"
	, ENTITY_RESERVED_PROPS := "i)^(classname|materials_path|spawnflags|angles)$"
	MATLIST_TEMPLATE[] {
		get {
			thing := {M:[],V:[],D:[],S:[],T:[],G:[],W:[],P:[],Y:[]}
			;thing.Totals := OBjBindMethod(Materials, "CountEntries", thing)
			return thing
		}
	}
	
	SearchForFile(bspPath, byRef CFG, byRef texRemapEntities := 0) {
		; order of precedence:
		; 1 - entity's materials_path entry
		; 2 - cmd line entry
		; 3 - mod's, if map is in maps folder
		; 4 - fallback's, if liblist.gam can be found and read
		bspPathObj := new Path(bspPath)
		
		; 1 - entities' materials_path entry
		If (IsObject(texRemapEntities) && texRemapEntities.length()) {
			For _, entTexRemap in texRemapEntities {
				If (texRemapEntity.materials_path) {
					Console.Info("Read materials_path property from info_texture_remap entity")
					candidatePathObj := new Path(texRemapEntity.materials_path)
					If candidatePathObj.exists()
						Return candidatePathObj.get()
					If !candidatePathObj.isAbsolute()  ; assume relative to bsp file
						candidatePathObj := bspPathObj.parent.joinPath(texRemapEntity.materials_path)
					If candidatePathObj.exists()
						Return candidatePathObj.get()
				}
			}
			Console.Warn("Couldn't find valid materials.txt path from entity")
		}
		
		; 2 - cmd line entry
		If (CFG.materials_path) {
			Console.Info("Read materials_path property from command line")
			If FileExist(CFG.materials_path)
				Return CFG.materials_path
			Console.Warn("Couldn't find valid materials.txt path from command line")
		}
		
		; 3 - mod's, if map is in maps folder
		If (bspPathObj.get(-1) = "maps") {
			Console.Info("Trying to find materials.txt relative to map...")
			modname := RegExReplace(bspPathObj.get(-2), "_(?:downloads|addon)$")
			modPathObj := bspPathObj.parents[2].withName(modname)
			candidatePathObj := modPathObj.joinpath("sound\materials.txt")
			If candidatePathObj.exists()
				Return candidatePathObj.get()
				
			; 4 - fallback's, if liblist.gam can be found and read
			FileRead, libListRaw, % modPathObj.joinpath("liblist.gam").get()
			If (libListContent := VKV.Load(libListRaw) && libListContent.fallback_dir) {
				Console.Info("Trying to follow mod's fallback dir...")
				candidatePathObj := modPathObj.withName(libListContent.fallback_dir)
					.joinpath("sound\materials.txt")
				If candidatePathObj.exists()
					Return candidatePathObj.get()
			}
		}
		; if you reach here, found nothing :(
		Console.Warn("No materials.txt file found.")
	}
	
	; returns: total number of entries added
	GetEntries(path, byRef outAll := "", byRef outSelected := "") {
		; 'M' metal, 'V' ventillation, 'D' dirt, 'S' slosh liquid, 'T' tile, 
		; 'G' grate (Concrete is the default), 'W' wood, 'P' computer, 'Y' glass
		 outAll		 := Materials.MATLIST_TEMPLATE
		,outSelected := Materials.MATLIST_TEMPLATE
		,totals := 0
		FileRead, contentRaw, %path%
		Loop, Parse, contentRaw, `n,`r
		{
			entry := StrSplit(StrSplit(A_LoopField, "//")[1]
				,[A_Tab, A_Space], "", 2)
			
			If (entry.Length() < 2 || !outAll.HasKey(entry[1]))
				Continue
				
			outAll[entry[1]].Push(entry[2])
			,totals++
			
			If (StrLen(entry[2]) >= 12)
				outSelected[entry[1]].Push(entry[2])
		}
		return totals
	}
	; get totals
	CountEntries(byRef inMatList) {
		totals := 0
		for mat, matList in inMatList
			totals += matList.Length()
		return totals
	}
	
	; given texinfo list, returns the texture group names
	; i.e. names with the prefixes stripped
	GetNameGroups(byRef inTexInfoList) {
		result := []
		for _, texInfo in inTexInfoList {
			RegExMatch(texInfo[2], this.TEXNAMEPARTS_RE, texParts)
			If (!Util.Array.Has(result, texParts.texname))
				result.Push(texParts.texname)
		}
		return result
	}
	
	; returns list of texture names that aren't in inMatList
	; (i.e. not in materials.txt)
	FilterUsedNames(byref inMatList, byref inTexgroupList) {
		result := []
		for _, texgroupName in inTexgroupList {
			for mat, matList in inMatList {
				If (Util.Array.Has(matList, texgroupName, 0))
					Continue 2
			}
			; past this point, no match was found
			result.Push(texgroupName)
		}
		return result
	}
	
	; replaces found matches with new names
	; NOTE: edits in place
	; TODO: returns: 1 if succeed, 0 if fail (errorlevel sets reason)
	GroupRename(byref texInfoList, inOldGroupName, inNewGroupName, collapsiblePrefix:="~") {		
		If (inOldGroupName ~= Materials.IGNOREPATTERN)
			return
			
		for _, texInfo in texInfoList 
		{
			RegExMatch(texInfo[2],Materials.TEXNAMEPARTS_RE,m)
			If (m.texname = inOldGroupName)
				texInfo[2] := SubStr(m.prefix . inNewGroupName, 1, 15) ; cap to 15 chars
		}
	}
	
	GetGibberish(width) {
		result := ""
		Loop % width
		{
			Random, val, 1, StrLen(this.CHARSEQUENCE)
			result .= SubStr(this.CHARSEQUENCE,val,1)
		}
		return result
	}
	
	; NOTE: edits target in place
	MergeMatList(byRef target, byref other) {
		for matName, targetTexList in target
			for _, otherTexname in other[matName]
				if !Util.Array.Has(targetTexList, otherTexname)
					targetTexList.Push(otherTexname)
	}
	
	; returns a 2-level copy of a matlist struct
	; that in theory should be independent objects through and through
	CopyMatList(byRef source) {
		result := Materials.MATLIST_TEMPLATE
		for mat in result
			result[mat].Push(source[mat]*)
		return result
	}
	
	GetMatType(byRef matList, texGroupName) {
		for mat in matList
			if Util.Array.Has(matList[mat], texGroupName)
				return mat
	}
	
}
