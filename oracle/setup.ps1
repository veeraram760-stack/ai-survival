# AI Survival - Oracle Cloud Setup Helper
# Run this in PowerShell

Write-Host "=== AI Survival - Oracle Cloud Setup ===" -ForegroundColor Cyan
Write-Host ""

# Check Terraform
Write-Host "[1/6] Checking Terraform..." -ForegroundColor Yellow
$terraform = Get-Command terraform -ErrorAction SilentlyContinue
if (-not $terraform) {
    Write-Host "ERROR: Terraform not found. Install from https://developer.hashicorp.com/terraform/downloads" -ForegroundColor Red
    exit 1
}
Write-Host "Terraform found: $($terraform.Version)" -ForegroundColor Green

# Check SSH key
Write-Host "[2/6] Checking SSH key..." -ForegroundColor Yellow
$sshKeyPath = "$env:USERPROFILE\.ssh\id_rsa.pub"
if (-not (Test-Path $sshKeyPath)) {
    Write-Host "SSH key not found. Generating new key pair..." -ForegroundColor Yellow
    ssh-keygen -t rsa -b 2048 -f "$env:USERPROFILE\.ssh\id_rsa" -N ""
    Write-Host "SSH key generated at $env:USERPROFILE\.ssh\id_rsa" -ForegroundColor Green
} else {
    Write-Host "SSH key found: $sshKeyPath" -ForegroundColor Green
}

# Get SSH public key content
$sshPublicKey = Get-Content $sshKeyPath -Raw
Write-Host ""
Write-Host "Your SSH public key (copy this for later):" -ForegroundColor Cyan
Write-Host $sshPublicKey -ForegroundColor Gray

Write-Host ""
Write-Host "[3/6] Oracle Cloud Credentials Required" -ForegroundColor Yellow
Write-Host "Please open https://cloud.oracle.com in your browser and sign in." -ForegroundColor Cyan
Write-Host ""
Write-Host "Follow these steps to get your credentials:" -ForegroundColor Cyan
Write-Host ""

Write-Host "STEP A: Get Tenancy OCID" -ForegroundColor White
Write-Host "  - Click your profile icon (top right) → Tenancy: <your-company>" -ForegroundColor Gray
Write-Host "  - Copy the OCID (starts with ocid1.tenancy...)" -ForegroundColor Gray
Write-Host ""

Write-Host "STEP B: Get User OCID" -ForegroundColor White
Write-Host "  - Go to Identity → Users" -ForegroundColor Gray
Write-Host "  - Click your username" -ForegroundColor Gray
Write-Host "  - Copy the OCID (starts with ocid1.user...)" -ForegroundColor Gray
Write-Host ""

Write-Host "STEP C: Get Compartment OCID" -ForegroundColor White
Write-Host "  - Go to Identity → Compartments" -ForegroundColor Gray
Write-Host "  - Click the Root compartment" -ForegroundColor Gray
Write-Host "  - Copy the OCID (starts with ocid1.compartment...)" -ForegroundColor Gray
Write-Host ""

Write-Host "STEP D: Create API Key" -ForegroundColor White
Write-Host "  - Go to Identity → Users → Your user" -ForegroundColor Gray
Write-Host "  - Click 'API Keys' → 'Add API Key'" -ForegroundColor Gray
Write-Host "  - Select 'Paste a public key' and paste your SSH key from above" -ForegroundColor Gray
Write-Host "  - Click 'Add'" -ForegroundColor Gray
Write-Host "  - Copy the fingerprint (12:34:56:78:90:ab:cd:ef...)" -ForegroundColor Gray
Write-Host ""

# Collect credentials
Write-Host "[4/6] Enter your Oracle Cloud credentials" -ForegroundColor Yellow

$tenancyOcid = Read-Host "`nPaste Tenancy OCID (ocid1.tenancy...)"
$userOcid = Read-Host "Paste User OCID (ocid1.user...)"
$fingerprint = Read-Host "Paste Fingerprint (12:34:56:78:90:...)"
$compartmentOcid = Read-Host "Paste Compartment OCID (ocid1.compartment...)"

# Create terraform.tfvars
Write-Host ""
Write-Host "[5/6] Creating terraform.tfvars..." -ForegroundColor Yellow

$tfvarsContent = @"
region = "us-ashburn-1"
tenancy_ocid = "$tenancyOcid"
user_ocid = "$userOcid"
fingerprint = "$fingerprint"
private_key_path = "$env:USERPROFILE/.ssh/id_rsa"
compartment_id = "$compartmentOcid"
ssh_public_key_path = "$env:USERPROFILE/.ssh/id_rsa.pub"
"@

$tfvarsPath = "C:\ai_survival\oracle\terraform.tfvars"
$tfvarsContent | Out-File -FilePath $tfvarsPath -Encoding UTF8
Write-Host "Created terraform.tfvars at $tfvarsPath" -ForegroundColor Green

# Ask to deploy
Write-Host ""
$deploy = Read-Host "[6/6] Ready to deploy? This will create 3 ARM VMs on Oracle Cloud (y/n)"

if ($deploy -eq "y" -or $deploy -eq "Y") {
    Write-Host ""
    Write-Host "Running Terraform..." -ForegroundColor Cyan
    Set-Location "C:\ai_survival\oracle"
    
    terraform init
    terraform plan
    $confirm = Read-Host "`nDo you want to apply this plan? (y/n)"
    if ($confirm -eq "y" -or $confirm -eq "Y") {
        terraform apply
        Write-Host ""
        Write-Host "=== Deployment Complete ===" -ForegroundColor Green
        terraform output
    }
} else {
    Write-Host ""
    Write-Host "Setup complete. Run these commands when ready:" -ForegroundColor Cyan
    Write-Host "  cd C:\ai_survival\oracle" -ForegroundColor Gray
    Write-Host "  terraform init" -ForegroundColor Gray
    Write-Host "  terraform plan" -ForegroundColor Gray
    Write-Host "  terraform apply" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. SSH to backend: ssh -i ~/.ssh/id_rsa opc@<backend-ip>" -ForegroundColor Gray
Write-Host "2. Configure .env with your API keys" -ForegroundColor Gray
Write-Host "3. Start services: sudo systemctl start ai-survival-backend" -ForegroundColor Gray
