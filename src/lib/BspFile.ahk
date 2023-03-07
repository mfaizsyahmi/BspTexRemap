; REQUIRES:
; Keyvalues class and its shorthand VKV

Class BspFile {
	static VERSIONCHECK := 30
	; these are offset by +1 because AHK arrays starts at 1
	,LUMP_ENTITIES     :=  1
	,LUMP_PLANES       :=  2
	,LUMP_TEXTURES     :=  3
	,LUMP_VERTICES     :=  4
	,LUMP_VISIBILITY   :=  5
	,LUMP_NODES        :=  6
	,LUMP_TEXINFO      :=  7
	,LUMP_FACES        :=  8
	,LUMP_LIGHTING     :=  9
	,LUMP_CLIPNODES    := 10
	,LUMP_LEAVES       := 11
	,LUMP_MARKSURFACES := 12
	,LUMP_EDGES        := 13
	,LUMP_SURFEDGES    := 14
	,LUMP_MODELS       := 15
	,HEADER_LUMPS      := 15 ; counts the number of lumps
	
	__New(pathOrFp) {
		 this._fp := IsObject(pathOrFp) ? pathOrFp : FileOpen(pathOrFp, "rw")
		,this._fp.seek(0)
		,this.version := this._fp.ReadInt()
		if this.version != this.VERSIONCHECK
			throw Exception("Incorrect BSP version number.", -1)
		
		this.LumpDirectory := []
		Loop % this.HEADER_LUMPS
		{
			offset := this._fp.ReadInt()
			length := this._fp.ReadInt()
			this.LumpDirectory.Push([offset, length])
		}
		
		 this._ParseEntityLump(this._fp)
		,this._ParseTextureLump(this._fp)
	}
	
	_ParseTextureLump(fp) {
		 texLumpOffset := this.LumpDirectory[this.LUMP_TEXTURES][1]
		,fp.seek(texLumpOffset)
		,texCount := fp.ReadUInt()
		,this.Textures := texList := []
		loop % texCount
			texList.Push([fp.ReadUInt()])

		for i in texList
		{
			 fp.Seek(texLumpOffset + texList[i][1])
			,VarSetCapacity(texNameRaw, 16, 0)
			,fp.RawRead(&texNameRaw, 16)
			,texW := fp.ReadUInt()
			,texH := fp.ReadUInt()
			,embedded := !!fp.ReadUInt()
			
			,texList[i].Push(StrGet(&texNameRaw,"CP0"), texW, texH, embedded)
		}

	}
	; for now this only dumps the texture names
	_DumpTextureLump(fp) {
		 texLumpOffset := this.LumpDirectory[this.LUMP_TEXTURES][1]
		,texList := this.Textures
		for i, texItem in texList
		{
			fp.Seek(texLumpOffset + texItem[1])
			VarSetCapacity(texNameRaw, 16, 0)
			StrPut(texItem[2], &texNameRaw, 16, "CP0")
			fp.RawWrite(&texNameRaw, 16)
		}
	}
	_ParseEntityLump(fp) {
		 fp.seek(this.LumpDirectory[this.LUMP_ENTITIES][1])
		,VarSetCapacity(lumpRaw, this.LumpDirectory[this.LUMP_ENTITIES][2], 0)
		,fp.RawRead(&lumpRaw, 16)
		,this.Entities := entities := VKV.Load(StrGet(&lumpRaw, "CP0"),"entities")
		return entities
	}
	
	WriteChanges() {
		if this._fp
			this._DumpTextureLump(this._fp)
	}
	
	__Delete() {
		try
			this._fp.Close()
	}
}