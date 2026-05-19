@echo off

REM 切换到当前 Skill 目录
cd /d %~dp0\..

REM 示例：把 D:\data\patient.csv 导入 MySQL
python scripts\csv_to_mysql_varchar.py ^
  --csv "D:\data\patient.csv" ^
  --host 127.0.0.1 ^
  --port 3306 ^
  --user root ^
  --password 123456 ^
  --database test ^
  --table patient_import ^
  --encoding utf-8-sig ^
  --drop

pause
