; path manipulation library for the sake of my sanity

Class Path {
	static PATH_SEPARATOR := "\"
	__New(pathStrOrArr) {
		If IsObject(pathStrOrArr) {
			 this._path := pathStr := Util.Array.Join(pathStrOrArr, this.PATH_SEPARATOR)
			,this._parts := pathStrOrArr
		} Else { ; string
			 this._path := pathStr := pathStrOrArr
			,this._parts := StrSplit(pathStrOrArr, this.PATH_SEPARATOR)
		}
		SplitPath, pathStr, name, dir, suffix, stem, drive
		 this.name := name
		,this.dir := dir
		,this.suffix := suffix
		,this.stem := stem
		,this.drive := drive
		; return this
	}
	parts[lowHigh*] {
		; returns array of parts
		get {
			if (lowHigh.Length() = 2)
				return Util.Array.Slice(this._parts,lowHigh*)
			else if (lowHigh.Length() = 1)
				return this._parts[lowHigh[1]]
			; implied else
			return this._parts.Clone()
		}
	}
	parent[] {
		get {
			if (this._parts.length() == 1)
				return this
			; implied else
			return new Path(Util.Array.Slice(this._parts,1,0))
		}
	}
	parents[lowHigh*] {
		; difference between this and get() is that this returns new instances of this object
		; also ensures a root is returned if used in the original sense (pre-python3.10)
		get {
			if (lowHigh.Length() == 1) { ; 1 index, always access from the end
				end := this._parts.length() - lowHigh[1] + 1
				if (this._parts.length() == 1)
					return this
				else if (end < 1)
					return new Path(this._parts[1])
				else
					return new Path(Util.Array.Slice(this._parts,1,end))
					
			} else { ; 2 indices (start and end) (from python 3.10+)
				return new Path(Util.Array.Slice(this._parts,lowHigh*))
			}
		}
	}
	
	joinPath(other*) {
		newParts := this._parts.clone()
		For _, part in other
			If (IsObject(part) && part.__Class == this.__Class)
				If part.isAbsolute
					Throw Exception("Cannot concatenate absolute path to other path", -1)
				Else
					newParts.Push(other.parts*)
			Else
				newParts.Push(StrSplit(part, this.PATH_SEPARATOR)*)
		Return new Path(newParts)
	}
	relativeTo(other) {
		otherArr := (IsObject(other) && other.__Class == this.__Class)
			? other.parts : StrSplit(other, this.PATH_SEPARATOR)
		For i in otherArr
			If otherArr[i] != this._parts[i]
				throw Exception(Format("ValueError: ""{}"" doesn't start with ""{}"""
						, this._path
						, Util.Array.Join(otherArr, this.PATH_SEPARATOR))
					, -1)
		Return new Path(this.parts[otherArr.length()+1,""])
	}
	withName(newname) {
		return this.parent.joinpath(newname)
	}
	withSuffix(newsuffix) {
		return this.parent.joinpath(this.stem "." newsuffix)
	}
	exists() {
		return FileExist(this._path)
	}
	isDir() {
		return InStr(this.exists(),"D")
	}
	isAbsolute() {
		return !!this.drive
	}
	resolve() {
		Loop, files, % this._path
			return new Path(A_LoopFileLongPath)
		; if return nothing then path existn't
	}
	
	; returns path string. accepts arguments for slicing parts of path
	get(lowHigh*) {
		if (lowHigh.Length() == 0) ; no index, return self
			return this._path
			
		else if (lowHigh.Length() == 1) { ; 1 index, return single part
			; make n absolute. if <0 access from the end
			n := lowHigh[1] < 1 
				? lowHigh[1] + this._parts.length() 
				: lowHigh[1]
			return this._parts[n]
		}
		else ; 2 indices (start and end)
			return Util.Array.Join(Util.Array.Slice(this._parts,lowHigh*)
				, this.PATH_SEPARATOR)
	}
	toString() {
		return this._path
	}
	__Item[lowHigh*] { ; for v2
		get {
			return this.get(lowHigh*) ; aliased to get()
		}
	}
	__get(lowHigh*) { 
		; supports [index] or [start:end] slicing for ahk v1.1
		If (!lowHigh.length())
			return this.get()
		Else If (lowHigh.length() <= 2) {
			; the two values must be a number or a space
			isSliceParams:=0
			for _, val in lowHigh
				If val is integer
					isSliceParams++
				Else If val is space
					isSliceParams++
			If (isSliceParams = lowHigh.length())
				return this.get(lowHigh*)
		}
	}
}
