cd /d C:\Users\Micro\Downloads\XAU_AI_PRO\backend
echo Installing workflow SDK...
npm install workflow --omit=optional --no-audit --no-fund > npm-install-workflow.log 2>&1
echo EXIT_CODE:%ERRORLEVEL% >> npm-install-workflow.log
echo Done >> npm-install-workflow.log
