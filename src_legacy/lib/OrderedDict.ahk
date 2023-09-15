/* 
EntityDict
- case sensitive
- preserves order
- allows any number of entries with the same key (used by Source IO system)
- WIP
- requires: Util.Array
*/

class EntityDict {
	__New() {
		this._keys_ := []
		this._values_ := []
	}
	
	__Set(key, value) {
		if !(key ~= "^(_keys_|_values_)$") {
			if (key ~= "^on\w+"
			|| pos := !Util.Array.Has(this._keys_, key)) {
				this._keys_.push(key)
				this._values_.push(value)
			} else {
				this._values_[pos] := value
			}
			Return value
		}
	}
	
	__Get(key) {
		if (key ~= "^(_keys_|_values_)$")
			Return
		if (key == "Keys") 
			return this._keys_
		if (key == "Items")
			return this._values_
		else {
			pos := Util.Array.Has(this._keys_, key)
			Return this._values_[pos]
		}
	}
	
	_NewEnum() {
		Return new EntityDict._CustomEnum_(this._keys_, this._values_)
	}
	
	class _CustomEnum_ {
		__New(keys, values) {
			this.i := -1
			this.keys := keys
			this.values := values
		}
		
		Next(ByRef k, ByRef v) {
			if ( ++this.i == this.keys.Length() )
				Return false
			k := this.keys[this.i]
			v := this.values[this.i]
			Return true
		}
	}
	
	Count() {
		return this._keys_.length()
	}
	Length () {
		return this._keys_.length()
	}
	
	GetAll(key) {
		values := []
		for k, v in this
			if k == key
				values.push(v)
		return values
	}
	
	Delete(key) {
		if (pos := Util.Array.Has(this._keys_, key)) {
			value := this._values_[pos]
			this._keys_.removeAt(pos)
			this._values_.removeAt(pos)
		}
		return value
	}
	DeleteAll(key) {
		count := 0
		while (pos := Util.Array.Has(this._keys_, key)) {
			this._keys_.removeAt(pos)
			this._values_.removeAt(pos)
			count++
		}
		return count
	}
	
	HasKey(key) {
		return Util.Array.Has(this._keys_, key)
	}
}

; test suite
#INCLUDE cJSON.ahk
If (A_ScriptName == "OrderedDict.ahk") {
	d := new EntityDict()
	d.origin = "0 0 0"
	d.classname = "info_player_start"
	d.onUser1 = "startlevel,,,,"
	d.onUser1 = "lights_on,,,,"
}