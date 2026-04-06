@echo off
title Riddle & Puzzle - Reel Generator
color 0A

echo =======================================================
echo     🚀 STARTING RIDDLE & PUZZLE INSTAGRAM GENERATOR 🚀
echo =======================================================
echo.

:: Navigate strictly to your Python project directory
cd /d "C:\Users\Shubham\RiddleAnPuzzle"

:: Run the pipeline script exclusively in dry-run mode
python pipeline.py --dry-run

echo.
echo =======================================================
echo   ✅ REEL GENERATION COMPLETE!
echo   📸 Your video is in: C:\Users\Shubham\Downloads\TEMPORARY\riddleReels
echo =======================================================
echo.
echo Note: Copy your Instagram Description from the text above!
echo.

:: Keep the command prompt open so you can copy the description
pause
