pyinstaller ^
	--workpath ../build ^
	--distpath ../dist ^
	--clean ^
	BspTexRemap.py

set RESULT=%ERRORLEVEL%

msg %username% Build Result: %RESULT%
