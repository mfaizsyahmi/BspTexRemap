pyinstaller ^
	-F -w ^
	--paths venv/lib/site-packages ^
	--workpath ../build ^
	--distpath ../dist ^
	--clean ^
	-i ./assets/images/BspTexRemap_64.ico ^
	BspTexRemap_GUI.py

set RESULT=%ERRORLEVEL%

msg %username% Build Result: %RESULT%
