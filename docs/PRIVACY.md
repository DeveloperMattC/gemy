# Privacy and public-sharing checklist

This repo is maintained for **open code labs and GitHub**. It should not contain personal or machine-specific data.

## What we exclude (`.gitignore`)

| Item | Why |
|------|-----|
| `logs/*.log` | May contain your PC paths, adapter names, certificate thumbprints |
| `.cursor/` | Local IDE/agent config tied to your machine |
| `*.jpg` pulled from the board | Your photos |
| Generated `*.cat` driver catalogs | Built on your PC when you run NCM install |

## What is safe to share

- **192.168.137.x** in docs — standard Windows Internet Connection Sharing subnet for USB gadgets, not your home LAN secret  
- **USB VID/PID** in drivers — public Coralboard USB identifiers  
- **Example board paths** (`/home/root/…`) — same on every board  

## What we scrubbed from docs

- No `C:\Users\…` paths — commands use repo-relative `.\greet-demo.ps1` style  
- No named NIC vendors (e.g. one PC's Ethernet chip) in setup scripts — ICS picks first non-virtual adapter  
- No author email in committed files — fill placeholders in instructor guides locally if needed  

## Before you fork or present

1. Run `install-ncm-signed.ps1` → do **not** commit `logs/ncm-setup.log`  
2. Search your fork for your name, email, or hostname if you added notes  
3. Do not commit photos from `adb pull` of the HAT camera  

## Upstream data on the board

Running demos may download models to the **board** (Hugging Face, etc.). That stays on the device unless you export it.
