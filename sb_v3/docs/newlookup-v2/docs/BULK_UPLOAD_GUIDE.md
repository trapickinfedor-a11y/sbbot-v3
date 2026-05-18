# Bulk Upload Guide

## Brute Bulk Upload Instructions

This guide provides instructions for bulk uploading Brute data in CSV and TXT formats.

---

## 📋 Supported Formats

### 1. TXT Format (Pipe-Delimited)

**Format:** `BANK|LOGIN|PASS|AN|RN|BALANCE|STATE|NAME|ADDRESS|ZIP|PRICE`

**Example:**
```
chase|john.doe|password123|123456789|987654321|5000.00|CA|John Doe|123 Main St|90210|25.00
boa|jane.smith|secret456|112233445|556677889|12000.00|NY|Jane Smith|456 Oak Ave|10001|30.00
wells|bob.wilson|pass789|998877665|443322110|8500.00|TX|Bob Wilson|789 Pine Rd|75001|28.00
```

**Field Descriptions:**
| Field | Required | Description |
|-------|----------|-------------|
| BANK | ✅ | Bank ID (chase, boa, wells, citi, capital_one, usbank, pnc, td) |
| LOGIN | ✅ | Account login/username |
| PASS | ✅ | Account password |
| AN | ✅ | Account Number |
| RN | ✅ | Routing Number |
| BALANCE | ✅ | Account balance in USD |
| STATE | ✅ | State code (CA, NY, TX, FL, IL, etc.) |
| NAME | ✅ | Account holder name |
| ADDRESS | ✅ | Street address |
| ZIP | ✅ | ZIP code |
| PRICE | ✅ | Selling price in USD |

---

### 2. CSV Format (Comma-Separated)

**Header:** `bank,login,pass,an,rn,balance,state,name,address,zip,price`

**Example:**
```csv
bank,login,pass,an,rn,balance,state,name,address,zip,price
chase,john.doe,password123,123456789,987654321,5000.00,CA,John Doe,123 Main St,90210,25.00
boa,jane.smith,secret456,112233445,556677889,12000.00,NY,Jane Smith,456 Oak Ave,10001,30.00
wells,bob.wilson,pass789,998877665,443322110,8500.00,TX,Bob Wilson,789 Pine Rd,75001,28.00
```

---

## 🔄 Format Conversion Prompt

Use this prompt to convert raw data to the required format:

```
Convert the following data to Brute bulk upload format (pipe-delimited):

Format: BANK|LOGIN|PASS|AN|RN|BALANCE|STATE|NAME|ADDRESS|ZIP|PRICE

Requirements:
1. Use lowercase bank IDs: chase, boa, wells, citi, capital_one, usbank, pnc, td
2. Balance and price should be numeric with 2 decimal places
3. State should be 2-letter uppercase code
4. ZIP should be 5 digits
5. One entry per line
6. Skip any entries with missing required fields

Data to convert:
[INSERT YOUR DATA HERE]
```

---

## 📝 Upload Instructions

### Step 1: Prepare Your File

1. Create a new `.txt` or `.csv` file
2. Ensure all required fields are present
3. Verify data format matches the examples above
4. Remove any header rows (for TXT format)

### Step 2: Upload via Web Panel

1. Navigate to **Upload Center** → **Brute Bank**
2. Select **"Bulk Upload"** tab
3. Choose file format (TXT or CSV)
4. Drag & drop or click to select your file
5. Review the preview
6. Click **"Upload"**

### Step 3: Verify Upload

After upload, check:
- ✅ Total items uploaded
- ✅ No errors in validation
- ✅ Items appear in your inventory

---

## ⚠️ Validation Rules

The system will reject entries with:
- Missing required fields
- Invalid bank ID
- Non-numeric balance/price
- Invalid state code
- Invalid ZIP format
- Duplicate account numbers

---

## 🛠️ Common Issues

### Issue: "Invalid bank ID"
**Solution:** Use only supported bank IDs: `chase`, `boa`, `wells`, `citi`, `capital_one`, `usbank`, `pnc`, `td`

### Issue: "Invalid balance format"
**Solution:** Balance must be a number with up to 2 decimal places (e.g., `5000.00`)

### Issue: "Missing required fields"
**Solution:** Ensure all 11 fields are present for each entry

### Issue: "Invalid state code"
**Solution:** Use 2-letter uppercase state codes (CA, NY, TX, FL, IL, etc.)

---

## 📊 Sample Templates

### TXT Template (copy and fill)
```
bank|login|pass|an|rn|balance|state|name|address|zip|price
|||||||||||
```

### CSV Template (copy and fill)
```csv
bank,login,pass,an,rn,balance,state,name,address,zip,price
,,,,,,,,,,
```

---

## 🔐 Security Notes

- Never include real passwords in test files
- Encrypt files containing sensitive data
- Delete local copies after successful upload
- Use secure file transfer methods

---

## 📞 Support

For issues with bulk uploads:
1. Check validation error messages
2. Verify file format matches examples
3. Contact support with error details

---

**Last Updated:** March 25, 2026
**Version:** 1.0
