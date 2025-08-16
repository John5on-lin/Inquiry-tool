@echo off
REM 一键自动同步本地代码到 GitHub（带时间戳提交信息）

REM 确保在 main 分支
git checkout main

REM 拉取远端最新代码
echo Pulling latest changes from GitHub...
git pull origin main

REM 添加所有修改
echo Adding all changes...
git add .

REM 生成时间戳作为提交信息
for /f "tokens=1-4 delims=/ " %%a in ("%date%") do (
    set datestr=%%a-%%b-%%c
)
for /f "tokens=1-2 delims=: " %%a in ("%time%") do (
    set timestr=%%a-%%b
)
set commit_msg=Auto commit on %datestr% %timestr%

REM 提交
git commit -m "%commit_msg%"

REM 推送到远端 main 分支
echo Pushing to GitHub...
git push origin main

echo.
echo 同步完成！
pause
