@echo off
REM --- run_daily_auth.bat ---
REM This script navigates to the project root and runs the trigger.py script.
REM It's designed for use with Windows Task Scheduler or manual execution.

REM --- Configuration ---
REM Set the full path to your Python interpreter's executable.
REM IMPORTANT: Adjust this path to match your Python installation.
SET PYTHON_EXE="C:\Users\YourUsername\AppData\Local\Programs\Python\Python39\python.exe"

REM Set the full path to your project's root directory (where trigger.py is located).
REM IMPORTANT: Adjust this path to your 'stonks' directory.
SET PROJECT_ROOT="C:\Machine Learning\stonks\data\daily_auth\"

REM Set the name of your trigger script.
SET TRIGGER_SCRIPT="trigger.py"

REM Set the path for the log file. This will capture all output from trigger.py.
REM You can change this path as needed.
SET LOG_FILE="%PROJECT_ROOT%daily_auth_trigger.log"

REM --- Execution ---
REM Change to the project root directory. This is crucial for trigger.py to find main.py.
CD /D %PROJECT_ROOT%

REM Run the Python script and redirect its output to the log file.
REM The '>>' appends to the log file; '>' would overwrite it each time.
REM '2>&1' redirects stderr (errors) to stdout (standard output) so both go to the log.
%PYTHON_EXE% %TRIGGER_SCRIPT% >> %LOG_FILE% 2>&1

REM Optional: Add a pause if you want to see console output when running manually.
REM PAUSE