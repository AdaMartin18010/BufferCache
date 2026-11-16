@echo off
rem TLA+ 模型检查一键运行（需 Java 11+）
cd /d "%~dp0"

echo ===== Running TLC on LRU =====
java -XX:+UseParallelGC -jar tla2tools.jar -nowarning -config LRU.cfg LRU.tla
if errorlevel 1 (echo LRU: FAILED & exit /b 1) else (echo LRU: PASSED)

echo.
echo ===== Running TLC on ARC =====
java -XX:+UseParallelGC -jar tla2tools.jar -nowarning -config ARC.cfg ARC.tla
if errorlevel 1 (echo ARC: FAILED & exit /b 1) else (echo ARC: PASSED)

echo.
echo All model checks PASSED
