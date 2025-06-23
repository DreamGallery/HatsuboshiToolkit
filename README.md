# HatsuboshiToolkit - Gakumas Resource Downloader

A comprehensive toolkit for downloading and managing resources from Gakuen IdolMaster (Gakumas), with automatic Cloudflare R2 synchronization support.

## Important Notice

***As a courtesy to other fans, please refrain from spoiling unreleased contents if any are found after decrypting.***

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/DreamGallery/HatsuboshiToolkit
   cd HatsuboshiToolkit
   git checkout resource
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure settings**
   - Edit `config.ini` with your API credentials and preferences
   - Set up Cloudflare R2 credentials if you want to use sync functionality

## Configuration
Edit `config.ini`:

### Cloudflare R2 Setup (Optional)

To enable automatic sync to Cloudflare R2, configure these settings:

```ini
[R2 settings]
R2_ACCOUNT_ID = your_cloudflare_account_id
R2_ACCESS_KEY_ID = your_r2_access_key_id
R2_SECRET_ACCESS_KEY = your_r2_secret_access_key
R2_BUCKET_NAME = your_bucket_name
R2_ENDPOINT_URL = https://your_account_id.r2.cloudflarestorage.com
ENABLE_R2_SYNC = true
```

## Usage

```bash
python main.py [OPTIONS]

Options:
  --mode [once|loop]      Script mode: 'once' for single run, 'loop' for continuous monitoring
  --reset BOOLEAN         Reset local database
  --init_download BOOLEAN Download full resource on first use
  --loop_interval INTEGER Interval between checks in seconds (default: 600)
  --sync_only BOOLEAN     Only sync existing cache to R2 without downloading
  --force_upload BOOLEAN  Force upload all files to R2.
  --help                  Show help message
```