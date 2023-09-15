; analogue of python3's operation.itemGetter
class itemGetter {
	__New(keys*) {
		this._keys := keys
	}
	__Call(name, obj) {
		If (name != "")
			return ; unknown function call. we only accept calling the object
		result := []
		for _, key in this._keys {
			result.push(obj[key])
		}
		return result
	}
}
