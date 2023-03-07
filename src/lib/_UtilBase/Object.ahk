class Object {
	; analog to ES Object.assign
	Assign(targetObj, sourceObjects*) {
		for _, obj in sourceObjects
			for k, v in obj
				targetObj[k] := v
		return targetObj
	}
	
	; analog to Scripting.Dictionary. In fact will try to return the object's Keys property/method if it has one
	Keys(obj) {
		try
			return Obj.Keys
			
		result := []
		for k in obj
			result.push(k)
		return result
	}
	
	; analog to Scripting.Dictionary. In fact will try to return the object's Items property/method if it has one
	Items(obj) {
		try
			return obj.Items
			
		result := []
		for _, item in obj
			result.push(item)
		return result
	
	}
}
