class Array {
	; heuristically determine an array from an object. 
	; zero items = yes. otherwise, must:
	; 	- key start at 1
	; 	- max index == count
	; 	- count of integer keys same as count of all keys
	isArray(arrOrObj) { ; https://www.autohotkey.com/boards/viewtopic.php?f=76&t=64332
		return !ObjCount(arrOrObj) 
			|| ObjMinIndex(arrOrObj) == 1 
			&& ObjMaxIndex(arrOrObj) == ObjCount(arrOrObj) 
			&& arrOrObj.Clone().Delete(1, arrOrObj.MaxIndex()) == ObjCount(arrOrObj)
	}

	; the missing Array analogue to AHK's Object.HasKey
	; returns the index of first found item, else none
	Has(arr, item, caseSensitive := 0) {
		for i, thing in arr
			if (caseSensitive && thing == item)
				return i
			else if (thing = item)
				return i
	}
	
	; push if absent, so the array pretends to be a set
	SetAdd(arr, items*) {
		for _, item in items
			If !this.Has(arr, item)
				arr.Push(item)
	}
	
	; near-analog to ES Array.prototype.map
	Map(arr, propOrFunction) {
		If IsObject(propOrFunction)
			propGetter := propOrFunction
		Else
			propName := propOrFunction
		
		result := []
		for _, item in arr
			result.push(propGetter ? propGetter.Call(item) : item[propName])
		return result
	}
	
	; near-analog to ES Array.prototype.slice
	; slices from start to (but not including) end
	; every index is +1 from the es counterpart because AHK
	Slice(arr, start := 1, end := "") { ;, newitems*) 
		result	:= arr.Clone()
		(!StrLen(end)) 
			? end := result.Length() + 1 ; +1 to go *past* so includes the last item
			: end
		absStart:= (start < 1) ? start + result.Length() : start
		absEnd	:= (end < 1) ? end + result.Length() : end
		if (absStart > result.Length() || absEnd <= absStart)
			return
		if (absEnd <= arr.length())
			result.RemoveAt(absEnd, arr.length() - absEnd + 1)
		(absStart>1) ? result.RemoveAt(1,absStart-1) : 0
		return result
	}
	
	; near-analog to ES Array.prototype.join
	Join(arr, sep := "|") {
		result := ""
		for i, item in arr
			result .= (i=1 ? "" : sep) . item
		return result
	}
	
	; NOT ES5 analog, this takes AHK's options
	Sort(arr, options := "") {
		arrJoined := this.Join(arr, "`n")
		Sort, arrJoined, %options%
		return StrSplit(arrJoined, "`n")
	}
	
	; moves an item at given index in place (i.e. in same array)
	; returns the new index
	MoveItem(arr, index, direction) {
		arr.InsertAt(index+direction, arr.removeAt(index))
		return index+direction
	}
	
	; analog to ES Array.prototype.reduce
	Reduce(arr, reducerFn, initialValue := "") {
		if initialValue is number 
		{
			previousValue := initialValue
			,currentIndex := 1 ; AHK ARRAYS STARTS AT 1
		} else {
			previousValue := arr[1]
			,currentIndex := 2
		}
		Loop {
			previousValue := reducerFn.(previousValue, arr[currentIndex], currentIndex, arr)
			,currentIndex++
		} until currentIndex = arr.length()
		
		return previousValue
	}
	
	; stock reducer functions to be used in Util.Array.Reduce
	class Reducer {
		Sum(previousValue, currentValue) {
			return previousValue + currentValue
		}
	}
}
