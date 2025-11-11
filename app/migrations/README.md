# Database Migrations

This directory contains database migration scripts for the webapp.

## QR String Migration

### Overview
The QR code system has been updated to use random strings instead of URLs. This change improves security and allows the backend to control what data is returned when a QR code is scanned.

### Changes Made

1. **Database Model**: Added `qr_string` field to `QRObject` model
2. **QR Generation**: QR codes now contain random alphanumeric strings (16 characters)
3. **Backend API**: New endpoint `/qr/api/search?qr_string=...` to look up QR objects
4. **Frontend Scanner**: Updated to send scanned data to backend instead of parsing locally

### Migration Steps

#### For New Installations
No migration needed. The database will be created with the correct schema automatically.

#### For Existing Installations

1. **Backup your database** (important!)
   ```bash
   cp app/database.db app/database.db.backup
   ```

2. **Run the migration script**
   ```bash
   python app/migrations/add_qr_string_column.py
   ```

3. **Regenerate QR codes** (if you have existing QR objects)
   ```bash
   python app/migrations/regenerate_qr_codes.py
   ```

4. **Restart the application**
   ```bash
   # Your normal startup command
   python main.py
   # or
   uvicorn main:app --reload
   ```

### What the Migration Does

The `add_qr_string_column.py` script:
- Adds the `qr_string` column to the `qr_objects` table
- Generates unique random strings for existing QR objects
- Maintains all existing data (names, descriptions, photos, etc.)

The `regenerate_qr_codes.py` script:
- Regenerates QR code images with the new random strings
- Updates the `qr_code_path` for each object

### After Migration

- **Old QR codes** with URLs will no longer work with the scanner
- **New QR codes** must be printed/displayed with the regenerated images
- The frontend scanner will now call the backend to look up QR data
- QR objects can be searched by their unique random string

### Rollback

If you need to rollback:
1. Restore your database backup
2. Revert code changes to the previous version

### Testing

After migration, verify:
1. New QR objects can be created
2. QR codes contain random strings (not URLs)
3. Scanning QR codes in the scanner displays the correct object
4. Old QR objects (if migrated) work with new QR codes
