#REQUIRES Autohotkey v1.1

#INCLUDE <cJSON>
#INCLUDE <ScriptingDictionary> ; using this to preserve entity entry order
#INCLUDE <keyvalues>
; VKV.ObjectFactory := Object
VKV.ObjectFactory := ScriptingDictionary
; JSON.dump(VKV._newObject())
f := VKV._newObject()
f["a"] := 1
f["b"] := 2
for k,v in f
	MsgBox % JSON.dump([k,v])
	
/*
I have a class that has a customizeable object factory:
```ahk
class foo {
  static ObjectFactory := Object
  ...
  _newObject() {
    if (this.ObjectFactory.__Class)
      return new this.ObjectFactory
    else
      return this.ObjectFactory()
  }
  ...
}
```
and I feed it with a ScriptingDictionary class from here:
https://www.autohotkey.com/boards/viewtopic.php?p=310596&sid=accbc89162c1c8e584be3bdb05c5a365#p310596
```
class ScriptingDictionary {
	__New() {
	this._dict_ := ComObjCreate("Scripting.Dictionary")
	}
	__Delete() { ... }
	__Set(key, value) { ... }
	__Get(key) { ... }
	_NewEnum() {
		Return new ScriptingDictionary._CustomEnum_(this._dict_)
	}
	class _CustomEnum_ { ... }
	
	Count() { 
		return this._dict_.Count
	}
	Delete(key) { ... }
	HasKey(key) { ... }
}
```
this used to work in an 1.1.33.02 version I kept around for performance reasons. but now I've updated to 1.1.36.02 and win10x64 and this no longer seem to work.

to make it worse, the default objectfactory also don't work now:
```ahk
f := foo._newObject()
f["a"] := 1
for k,v in f
	MsgBox % JSON.dump([k,v]) ; didn't run, f is not an object
```
and cJSON screaming at me that it's not an object during debugging is just frustrating.
*/