class Ini {
	static ARRAY_SEPARATOR := ","
	/*
	; Util.Ini.Load - INI file loader with support of loading specific sections and array values
	; sectionList: a comma-delimited string or an array containing list of sections to load
	;              a !prefixed section name will be excluded [[NOT IMPLEMENTED]]
	; options: one or more of the following strings:
	;	sectionContent[n]	loads the section content to key "_content" based on value n
	;						0: never load
	;						1: load if no key
	;						2: always load
	;						3: the section is replaced with the content rather than a kv object
	;						note: section content is meant to be read only, 
	;						no write support is provided
	*/
	Load(iniPath, byref sectionList:="", options:="") {
		RegExMatch(options, "sectionContent\K\d", optSectionContent)
		
		If !sectionList {
			IniRead, sectionList, % iniPath
			sectionList := StrSplit(sectionList, "`n", "`r")
		} Else If !IsObject(sectionList) {
			sectionList := StrSplit(sectionList, ",", " `t")
		}
		/* TODO: figure out how to filter out particular sections
		
		*/
		
		returnObj := {}
		
		for _, currentSection in sectionList ;, `n, `r
		{
			;currentSection := A_LoopField
			; retire from using the meta keys as they sneak their way into enums
			; returnObj[currentSection] := { __arrKeys:[], __jsonKeys:[] }
			returnObj[currentSection] := {}
			,keyCount := 0
			IniRead, sectionContent, % iniPath, % currentSection
			If (optSectionContent = 3) {
				returnObj[currentSection] := sectionContent
				Continue ; with next section
			}
			
			; short-circuit the loop if there's no assignment symbols in the section body
			If sectionContent not contains :,= 
			{
				If optSectionContent
					returnObj[currentSection]._content := sectionContent
				Continue
			}
			
			Loop, Parse, sectionContent, `n
			{
				RegExMatch(A_LoopField,"O)^(?P<kname>[^|:=]*)(?:\|(?P<ktype>\w+))?[:=](?P<v>.*)", m)
				if !m[0] ; no keyvalue pair matched on this line
					continue
				switch m.ktype
				{
				case "arr":
					v := _UtilBase.Array.Map(StrSplit(m.v,","), Func("Trim"))
					;,returnObj[currentSection].__arrKeys.Push(m.kname)
				case "json":
					v := JSON.load(m.v)
					;,returnObj[currentSection].__jsonKeys.Push(m.kname)
				default:
					v := Trim(m.v)
				}

				 returnObj[currentSection][m.kname] := v
				,keyCount++
			}
			
			If ((optSectionContent = 1 && !keyCount) || optSectionContent = 2)
				returnObj[currentSection]._content := sectionContent
		}
				
		return returnObj
	}

	; Util.Ini.Save - writes INI file from configObject
	Save(ConfigObject, iniPath, sectionList:="", keyList:="") {
		If (!IsObject(sectionList)) {
			sectionList:=[]
			for k, _ in ConfigObject {
				sectionList.Push(k)
			}
		}
		For _, sectionName in sectionList
		{
			currentSection := ConfigObject[sectionName]
			If !IsObject(currentSection)
				Continue
			For k, v in currentSection {
				If ((IsObject(keyList) && !_UtilBase.Array.Has(keyList, k))
				|| (SubStr(k, 1, 2) = "__")) ; the super secret keys that tag arr/json keyvalues
					Continue
				
				; retire from using the problematic meta keys, we now apply
				; heuristics to find out if the object is array or object
				; Else If _UtilBase.Array.Has(currentSection.__arrKeys, k) {
				Else If IsObject(v) && _UtilBase.Array.isArray(v) {
					vlist:=""
					For _, item in v
						vlist .= this.ARRAY_SEPARATOR item
						; vlist.="," item
					v := SubStr(vlist, 2)
					,k .="|arr"
				}
				; Else If _UtilBase.Array.Has(currentSection.__jsonKeys, k) {
				Else If IsObject(v) {
					v := JSON.dump(v)
					,k .="|json"
				}
				IniWrite, % v, % iniPath, % sectionName, % k
			}
		}
	}
	
}
