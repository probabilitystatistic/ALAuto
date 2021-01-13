@ECHO OFF

::Setting default path
SET ALPATH=d:\program\ALAuto

::Define the default map and mode
SET PreviousMap=2-1
SET PreviousMode=


::Starting point for the loop
:looping_the_execution


:: choosing map
SET /P Map= Which map?(2-1;5-1;6-1;7-2;s;h;e)

IF "%Map%"=="2" (SET MAP=2-1)
IF "%Map%"=="5" (SET MAP=5-1)
IF "%Map%"=="6" (SET MAP=6-1)
IF "%Map%"=="73" (SET MAP=7-2)
IF "%Map%"=="77" (SET MAP=7-2full)
IF "%Map%"=="s" (SET MAP=special)
IF "%Map%"=="h" (SET MAP=hard)
IF "%Map%"==""  (SET MAP=%PreviousMap%)
IF "%Map%"=="e" (GOTO :edit_by_hand)

SET PreviousMap=%Map%

SET FlagConfig=--c config_%Map%.ini


:: choosing mode
SET /P Mode= Using normal or debug mode?(n/d)

IF "%Mode%"=="d" (SET FlagMode=--debug) ELSE (SET FlagMode= )

SET PreviousMode=%FlagMode%

ECHO "Program: python '%ALPATH%\ALAuto.py'"
ECHO "Flags: %FlagConfig% %FlagMode%"

powershell -Command "& {Set-Location -Path '%ALPATH%' -PassThru; python '%ALPATH%\ALAuto.py' %FlagConfig% %FlagMode%; }"

GOTO :looping_the_execution


:edit_by_hand
notepad '%ALPATH%\config.ini'

:: choosing mode
SET /P Mode= Using normal or debug mode?(n/d)

IF "%Mode%"=="d" (SET FlagMode=--debug) ELSE (SET FlagMode= )

SET PreviousMode=%FlagMode%

powershell -Command "& {Set-Location -Path '%ALPATH%' -PassThru; python '%ALPATH%\ALAuto.py' %FlagMode%; }"

GOTO :looping_the_execution



