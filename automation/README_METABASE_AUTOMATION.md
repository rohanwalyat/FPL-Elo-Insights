# Metabase Database Resync Automation

This automation automatically triggers Metabase to resync its database schema after your FPL data updates, ensuring your dashboards always show the latest data.

## 🎯 What It Does

After database updates, Metabase needs to be told about schema changes to show new data properly. This automation:

1. ✅ **Checks if Metabase is running** - Starts it if needed
2. ✅ **Connects to Metabase API** - Uses admin credentials or provides manual instructions
3. ✅ **Triggers database resync** - Tells Metabase to update its schema cache
4. ✅ **Waits for completion** - Monitors the sync process
5. ✅ **Integrated with main automation** - Runs automatically after database updates

## 🚀 Quick Usage

### Automatic (Integrated)
The Metabase resync is **automatically included** in the complete automation:
```bash
./automation/run_full_update.sh
```

This will update your database AND resync Metabase automatically.

### Manual Resync Only
If you just want to resync Metabase without updating data:
```bash
./scripts/metabase_resync.sh
```

## 🔧 Setup Options

### Option 1: Automatic Authentication (Recommended)
Add Metabase admin credentials to your `.env` file:
```bash
# Add these lines to your .env file
METABASE_URL=http://localhost:3000
METABASE_ADMIN_EMAIL=your_admin_email@example.com
METABASE_ADMIN_PASSWORD=your_admin_password
```

### Option 2: Manual Process
If you don't want to store credentials, the script will provide manual instructions:
1. Open Metabase at http://localhost:3000
2. Go to Admin settings (⚙️ gear icon)
3. Click "Databases" in the left sidebar
4. Click on your PostgreSQL database
5. Click "Sync database schema now" button
6. Wait for sync to complete

## 📁 Files Created

### Core Scripts
- **`scripts/metabase_resync.py`** - Python script that uses Metabase API
- **`scripts/metabase_resync.sh`** - Shell wrapper with prerequisites checking
- **Updated `automation/full_update_automation.py`** - Includes Metabase resync step

### Features
- ✅ **Auto-starts Metabase** if not running
- ✅ **Health checking** - Verifies Metabase is accessible
- ✅ **Authentication handling** - Uses credentials or provides manual steps
- ✅ **Error recovery** - Continues automation even if Metabase sync fails
- ✅ **Progress monitoring** - Shows sync status and completion

## 🔄 Integration with Main Automation

When you run the complete automation:
```bash
./automation/run_full_update.sh
```

The workflow now includes:
1. Check GitHub for updates
2. Pull latest data
3. Update draft league data  
4. **Update database**
5. **🆕 Resync Metabase** ← New step!
6. Provide summary

## 📊 What Gets Resynced

The Metabase resync updates:
- **Table schemas** - New columns, data types
- **Table metadata** - Row counts, field information
- **Relationships** - Foreign key connections
- **Field types** - Ensures proper data type detection

This means your Metabase dashboards will immediately see:
- New player match stats
- Updated team information  
- Latest match results
- Fresh draft league data

## 🛠️ Prerequisites

### Required
- **Metabase installed** - metabase.jar in the metabase/ folder
- **PostgreSQL database** - Connected to Metabase
- **Python 3** - With requests library
- **Database already configured** - In Metabase admin settings

### Optional (for automatic sync)
- **Metabase admin credentials** - In .env file
- **Metabase running** - Script can start it automatically

## 🔍 Troubleshooting

### "Authentication required for Metabase API"
**Solution**: Add admin credentials to .env file:
```bash
METABASE_ADMIN_EMAIL=admin@example.com
METABASE_ADMIN_PASSWORD=your_password
```

### "Cannot connect to Metabase"
**Check**: 
```bash
# Is Metabase running?
./scripts/metabase_status.sh

# Start if needed
./scripts/start_metabase.sh

# Check if accessible
curl http://localhost:3000/api/health
```

### "No PostgreSQL database found"
**Solution**: Make sure you've connected your PostgreSQL database in Metabase admin settings:
1. Go to Admin → Databases
2. Add your PostgreSQL database with correct credentials
3. Test the connection

### "Metabase resync failed but automation continues"
This is **intentional behavior**. The automation won't fail completely if Metabase has issues, since the database update is more important. You can:
1. Run the resync manually: `./scripts/metabase_resync.sh`
2. Use the manual instructions provided in the log
3. Check Metabase logs for issues

## 📈 Performance

### Typical Resync Times
- **Small datasets** (like current FPL data): 5-15 seconds
- **Large datasets**: 30-60 seconds
- **First-time setup**: 1-2 minutes

### Resource Usage
- **Network**: Light API calls to Metabase
- **CPU**: Minimal during resync
- **Memory**: No additional memory usage

## 🔐 Security Notes

### Credential Storage
- Admin credentials stored in `.env` file (not in git)
- Credentials only used for API authentication
- No permanent storage of session tokens

### API Access
- Uses Metabase's official REST API
- Only accesses database management endpoints
- No data querying or dashboard modification

## 🎉 Benefits

- ✅ **No Manual Work** - Dashboards stay current automatically
- ✅ **Intelligent** - Only runs when database is actually updated
- ✅ **Resilient** - Handles Metabase being offline gracefully
- ✅ **Flexible** - Works with or without stored credentials
- ✅ **Integrated** - Part of the complete automation workflow
- ✅ **Safe** - Won't break your automation if Metabase has issues

## 🔄 Alternative Methods

If the API approach doesn't work for your setup:

### Manual Resync (Always Works)
1. Open http://localhost:3000
2. Admin settings → Databases
3. Click your database → "Sync database schema now"

### Metabase Restart (Nuclear Option)
```bash
./scripts/stop_metabase.sh
./scripts/start_metabase.sh
```
This forces a complete resync but takes longer.

### Scheduled Resync
Add to crontab for regular resyncs:
```bash
# Resync Metabase daily at 9 AM
0 9 * * * cd /path/to/fpl-elo-insights && ./scripts/metabase_resync.sh
```

## 📞 Support

### Logs
- Metabase resync logs: Included in main automation log
- Metabase application logs: `metabase/metabase.log`
- Individual resync logs: Run `./scripts/metabase_resync.sh` manually

### Common Issues
- **401 Unauthorized**: Add admin credentials to .env
- **Connection Refused**: Start Metabase with `./scripts/start_metabase.sh`
- **Database Not Found**: Configure PostgreSQL database in Metabase admin

### Manual Override
You can always manually refresh in Metabase if the automation fails:
Admin → Databases → Your Database → "Sync database schema now"

---

## 🏁 Ready to Use?

Your Metabase will now automatically stay in sync with your database updates! 

**Test the complete workflow:**
```bash
./automation/run_full_update.sh
```

**Or just test Metabase resync:**
```bash
./scripts/metabase_resync.sh
```

Your dashboards will always show the latest FPL data! 📊✨