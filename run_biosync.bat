@echo off
echo ================================================
echo  BioSync — Starting Up
echo ================================================
echo.

:: Step 1 - Go to project root (where venv lives)
cd /d C:\Users\sarah\Documents\Flask_Apps\BioSync-Group2

:: Step 2 - Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate
echo Done.
echo.

:: Step 3 - Install dependencies from BioSync folder
echo Installing dependencies...
pip install -r BioSync\requirements.txt --quiet
pip install pdfplumber python-docx pandas numpy --quiet
echo Done.
echo.

:: Step 4 - Set Flask app (run from BioSync-Group2, app is in BioSync folder)
set FLASK_APP=BioSync
set FLASK_DEBUG=1

:: Step 5 - Ask if database needs to be initialized
echo Do you need to initialize the database?
echo WARNING: This will wipe all existing data!
echo.
set /p INIT_DB="Type YES to init-db, or press Enter to skip: "
if /i "%INIT_DB%"=="YES" (
    echo Initializing database...
    flask --app BioSync init-db
    echo Done.
    echo.
)

:: Step 6 - Run Flask
echo ================================================
echo  BioSync running at http://127.0.0.1:5000
echo  Press CTRL+C to stop
echo ================================================
echo.
flask run

pause