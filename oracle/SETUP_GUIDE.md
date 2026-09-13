# AI Survival - Oracle Cloud Free Tier Setup Guide
# Complete step-by-step guide for beginners

## What is Oracle Cloud?

Oracle Cloud is like AWS/Azure/Google Cloud, but with a generous free tier:
- 4 ARM CPUs + 24GB RAM forever (free)
- 2 databases free forever
- 10TB data transfer free forever

## Step 1: Create Oracle Cloud Account

1. Go to https://signup.cloud.oracle.com/
2. Click "Start for Free"
3. Enter your details:
   - Email address
   - Country
   - Name
4. Verify your email
5. Add payment method (credit card) - you won't be charged for free tier
6. Click "Start my free trial"

**Important:** You need to verify your identity with a credit card, but you won't be charged as long as you stay within free tier limits.

## Step 2: Set Up SSH Keys

SSH keys let you securely connect to your cloud servers.

```powershell
# Open PowerShell and run:
cd C:\ai_survival\oracle
.\setup.ps1
```

The script will:
- Check if you have SSH keys
- Generate them if needed
- Show you your public key

**Copy the public key** - you'll need it later.

## Step 3: Get Oracle Cloud Credentials

After creating your account:

### 3.1 Find Your Tenancy OCID

1. Log into https://cloud.oracle.com/
2. Click your **profile icon** (top right corner)
3. Click **"Tenancy: <your-company-name>"**
4. You'll see **Tenancy OCID** - it looks like:
   ```
   ocid1.tenancy.oc1..aaaaaaaabxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
5. **Copy it** (click the copy icon)

### 3.2 Find Your User OCID

1. In Oracle Cloud Console, click the **hamburger menu** (9 dots, top left)
2. Go to **"Identity" → "Users"**
3. Click **your username**
4. You'll see **OCID** under your name - it looks like:
   ```
   ocid1.user.oc1..aaaaaaaabxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
5. **Copy it**

### 3.3 Find Your Compartment OCID

1. In the same **Identity** menu
2. Go to **"Compartments"**
3. Click the **"Root"** compartment
4. You'll see **OCID** - it looks like:
   ```
   ocid1.compartment.oc1..aaaaaaaabxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
5. **Copy it**

### 3.4 Create API Key

1. Go to **"Identity" → "Users"**
2. Click **your username**
3. Click **"API Keys"** in the left menu
4. Click **"Add API Key"**
5. Select **"Paste a public key"**
6. **Paste your SSH public key** (from Step 2)
7. Click **"Add"**
8. You'll see a **Fingerprint** - it looks like:
   ```
   12:34:56:78:90:ab:cd:ef:12:34:56:78:90:ab:cd:ef
   ```
9. **Copy it**

## Step 4: Deploy Your Infrastructure

Now you have all 5 values:
- [ ] Tenancy OCID
- [ ] User OCID
- [ ] Compartment OCID
- [ ] Fingerprint
- [ ] SSH Public Key (already in setup script)

### Option A: Automated (Recommended)

Run the setup script again and it will ask for these values:

```powershell
cd C:\ai_survival\oracle
.\setup.ps1
```

### Option B: Manual

Edit `terraform.tfvars` manually:

```powershell
notepad C:\ai_survival\oracle\terraform.tfvars
```

Replace the placeholder values with your actual credentials:

```hcl
region = "us-ashburn-1"
tenancy_ocid = "ocid1.tenancy.oc1..aaaaaaaab..."
user_ocid = "ocid1.user.oc1..aaaaaaaab..."
fingerprint = "12:34:56:78:90:ab:cd:ef..."
private_key_path = "C:\Users\YourName\.ssh\id_rsa"
compartment_id = "ocid1.compartment.oc1..aaaaaaaab..."
ssh_public_key_path = "C:\Users\YourName\.ssh\id_rsa.pub"
```

Then deploy:

```powershell
cd C:\ai_survival\oracle
terraform init
terraform plan
terraform apply
```

**Type "yes" when prompted.**

## Step 5: Configure Your Application

After Terraform finishes (takes ~10 minutes), you'll see:

```
backend_public_ip = "129.159.x.x"
dashboard_public_ip = "129.159.x.x"
```

### SSH to Backend

```powershell
ssh -i C:\Users\YourName\.ssh\id_rsa opc@129.159.x.x
```

### Upload Your .env

```powershell
# On your Windows machine
scp -i C:\Users\YourName\.ssh\id_rsa C:\ai_survival\.env opc@129.159.x.x:/home/opc/ai_survival/
```

### Start Services

```bash
# On the backend VM
cd /home/opc/ai_survival

# Start backend
sudo systemctl start ai-survival-backend

# Start worker
sudo systemctl start ai-survival-worker

# Check status
sudo systemctl status ai-survival-backend
```

## Step 6: Access Your Application

- **Dashboard**: http://129.159.x.x:3000
- **API**: http://129.159.x.x:8000
- **API Docs**: http://129.159.x.x:8000/docs

## Troubleshooting

### Can't SSH?
```powershell
# Check your SSH key
ssh -i C:\Users\YourName\.ssh\id_rsa opc@129.159.x.x
```

### Terraform errors?
```powershell
# Make sure all 5 values are correct
# Check OCI Console for exact OCIDs
```

### Services not starting?
```bash
# Check logs
sudo journalctl -u ai-survival-backend -n 100
sudo docker logs ai-survival-backend
```

## Cost

**$0/month** - All resources are in Oracle Cloud Free Tier:
- 3 ARM VMs (4 OCPU, 24GB RAM each)
- 1GB storage
- 10TB outbound bandwidth

You will NOT be charged as long as you stay within free tier limits.

## Next Steps After Deployment

1. **Configure notifications** - Update Telegram/Discord webhooks in .env
2. **Add API keys** - OpenAI, Anthropic, etc.
3. **Monitor logs** - Check agent activity via dashboard
4. **Set up alerts** - Configure notifications for agent decisions

## Need Help?

- Oracle Cloud Docs: https://docs.oracle.com/en-us/iaas/
- Terraform OCI Docs: https://registry.terraform.io/providers/oracle/oci/latest/docs
- SSH Guide: https://docs.oracle.com/en-us/iaas/Content/Compute/References/sshkeys.htm
