@echo off
echo ========================================
echo   Student Platform - Starting App
echo ========================================
echo.
echo Starting Student Opportunity Finder + Resume Builder (Flask)...
start "Student Platform" cmd /k "cd /d %~dp0 && python app.py"
echo.
echo ========================================
echo  App starting at http://localhost:5000
echo  - Opportunity Finder (AI agent)
echo  - Resume Builder (built-in, PDF export)
echo  - Menti AI (voice companion)
echo  - Nexus Interview Prep (AI interviewer)
echo ========================================
echo.
timeout /t 4 >nul
start http://localhost:5000
