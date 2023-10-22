@echo off
copy "D:\SteamLibrary\steamapps\common\Half-Life\valve_addon\maps\dm_hellhole.bsp.bak" tests\integration\fixtures\dm_hellhole.ORIGIN

python tests\integration\test_integration.py
set RESULT=%ERRORLEVEL%

msg %username% Integration Test Result: %RESULT%
