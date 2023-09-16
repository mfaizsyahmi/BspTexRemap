pyinstaller ^
	--workpath ../build ^
	--distpath ../dist ^
	--clean ^
	-i ./img/BspTexRemap_64.ico ^
	BspTexRemap.py

set RESULT=%ERRORLEVEL%

msg %username% Build Result: %RESULT%
