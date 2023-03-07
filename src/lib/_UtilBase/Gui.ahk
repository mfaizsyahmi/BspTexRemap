class Gui {
	
	ToolTipClear(which:= 1) {
		ToolTip, , , , % which
	}
	
	ToolTipClearAfter(timeout, which:= 1, priority := 0) {
		ClearerFn:= ObjBindMethod(this, "ToolTipClear", which)
		SetTimer, %ClearerFn%, % -timeout, % priority
	}
	/*
	Class ToolTip {
		__New(text, x, y, which := 1) {
			this._which := which
		}
	}
	*/
	
	; converts array into a string that populates a listbox/dropdown/combobox
	ListString(list, index, strRenderFn:="") {
		If IsFunc(strRenderFn) {
			useRenderFn := True
			,strRenderFn := IsObject(strRenderFn) ? strRenderFn : Func(strRenderFn)
		}
		
		result := ""
		for i, item in list
		{
			result .= (useRenderFn ? strRenderFn.(item) : item) 
					. (i = index ? "||" : "|")
		}
		return result
	}

	; returns a HICON pointer to the icon associated with the file type in filePath
	ExtractAssociatedIcon(filePath, byref iconIndex) {
		return DllCall("Shell32\ExtractAssociatedIcon", "Ptr", 0, "Str", filePath, "ShortP", iconIndex, "Ptr")
	}
	
	; https://www.autohotkey.com/boards/viewtopic.php?p=197355#p197355
	WinGetClientPos(ByRef X:="", ByRef Y:="", ByRef Width:="", ByRef Height:=""
	, WinTitle:="", WinText:="", ExcludeTitle:="", ExcludeText:="") {
		local hWnd, RECT
		 hWnd := WinExist(WinTitle, WinText, ExcludeTitle, ExcludeText)
		,VarSetCapacity(RECT, 16, 0)
		,DllCall("user32\GetClientRect", Ptr,hWnd, Ptr,&RECT)
		,DllCall("user32\ClientToScreen", Ptr,hWnd, Ptr,&RECT)
		,X := NumGet(&RECT, 0, "Int"), Y := NumGet(&RECT, 4, "Int")
		,Width := NumGet(&RECT, 8, "Int"), Height := NumGet(&RECT, 12, "Int")
	}
}