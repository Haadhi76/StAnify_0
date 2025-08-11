# A1111 Setup Script for StAnify
# Run this in the same PowerShell session where you'll start Streamlit

Write-Host "🚀 Setting up A1111 environment for StAnify..." -ForegroundColor Green

# Set environment variables for this session
$env:IMAGE_BACKEND = "sdxl-a1111"
$env:A1111_BASE_URL = "http://127.0.0.1:7860"
$env:A1111_MODEL = "sdxl_base_1.0"         # Update this to match your SDXL checkpoint name
$env:SDXL_WIDTH = "1024"
$env:SDXL_HEIGHT = "768"
$env:SDXL_STEPS = "30"
$env:SDXL_CFG_SCALE = "6.5"
$env:SDXL_SAMPLER = "DPM++ 2M Karras"

Write-Host "✅ Environment variables set:" -ForegroundColor Green
Write-Host "   IMAGE_BACKEND = $env:IMAGE_BACKEND"
Write-Host "   A1111_BASE_URL = $env:A1111_BASE_URL"
Write-Host "   A1111_MODEL = $env:A1111_MODEL"
Write-Host "   SDXL dimensions = $env:SDXL_WIDTH x $env:SDXL_HEIGHT"
Write-Host "   SDXL settings = $env:SDXL_STEPS steps, CFG $env:SDXL_CFG_SCALE, $env:SDXL_SAMPLER"

Write-Host ""
Write-Host "🔗 Testing A1111 connection..." -ForegroundColor Yellow

# Test the connection using Python
python test_a1111_connection.py

Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Cyan
Write-Host "1. Start A1111: .\webui-user.bat --api --xformers"
Write-Host "2. Open A1111 UI once to load your SDXL model"
Write-Host "3. Run Streamlit from THIS same terminal session"
Write-Host "4. Generate content and enjoy real AI images! 🎨"
