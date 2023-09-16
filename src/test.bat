cd tests\integration
python test_integration.py
set RESULT=%ERRORLEVEL%

msg %username% Integration Test Result: %RESULT%
