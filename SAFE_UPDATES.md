# 🔒 Safe Update Guide - RTA Break Tracker

## ⚠️ Important: Your Data is Safe!

**Good News:** Making code changes and deploying updates **will NOT delete your data**. The database persists across deployments.

However, it's always good practice to backup your data before major changes, just in case.

---

## 📋 How to Safely Make Updates

### Step 1: Export Your Data (Recommended)

1. **Login to RTM Dashboard**
   - Go to your website URL
   - Login as RTM admin

2. **Navigate to Backup Tab**
   - Click on "💾 Data Backup" tab in the dashboard

3. **Export All Data**
   - Click "📥 Export All Data" button
   - Save the JSON file in a safe location (your computer, cloud storage, etc.)
   - The file will be named: `rta-backup-YYYY-MM-DD.json`

### Step 2: Make Your Code Changes

1. **Edit your code** as needed
2. **Test locally** (if possible) before deploying
3. **Commit and push** to GitHub

### Step 3: Deploy Your Changes

1. **Railway/Render will automatically deploy** when you push to GitHub
2. **Your database persists** - all users, breaks, and shifts remain intact
3. **No data loss** - the database is separate from your code

### Step 4: Verify Everything Works

1. **Check the website** after deployment
2. **Login and verify** your data is still there
3. **Test new features** if you added any

---

## 🔄 If Something Goes Wrong

### Option 1: Restore from Backup

1. **Go to Backup Tab** in RTM Dashboard
2. **Click "Restore Data"**
3. **Select your backup file**
4. **Confirm the restore** (it will ask twice for safety)
5. **Wait for confirmation** - the page will reload

### Option 2: Contact Support

If restore doesn't work, you can:
- Check Railway/Render logs for errors
- Verify database connection is working
- Check environment variables are set correctly

---

## 📊 What Gets Backed Up?

The backup includes:
- ✅ **All Users** (agents and RTM accounts)
- ✅ **All Break Records** (with screenshots, times, notes)
- ✅ **All Shifts** (agent schedules for 2 weeks)
- ✅ **All Metadata** (creation dates, etc.)

**Note:** Passwords are NOT included in backups for security. Restored users will have default password: `changeme123` (users should change it after restore).

---

## 🛡️ Database Safety Features

### What Happens on Deployment:

1. **Database is NOT dropped** - Your data stays intact
2. **Tables are only created if missing** - Existing tables are untouched
3. **No data deletion** - Only new records are added
4. **PostgreSQL persists** - Railway/Render keeps your database running

### What `db.create_all()` Does:

- ✅ Creates tables **only if they don't exist**
- ✅ Does **NOT** drop existing tables
- ✅ Does **NOT** delete data
- ✅ Safe to run on every deployment

---

## 📝 Best Practices

1. **Always backup before major changes**
   - Especially before changing database schema
   - Before updating dependencies
   - Before major feature additions

2. **Test locally first** (if possible)
   - Run the app on your computer
   - Test new features
   - Verify nothing breaks

3. **Keep multiple backups**
   - Save backups in different locations
   - Keep backups from different dates
   - Don't delete old backups immediately

4. **Document your changes**
   - Note what you changed
   - Keep track of backup dates
   - Document any new features

---

## 🚨 When to Be Extra Careful

Be especially cautious when:

- **Changing database models** (User, BreakRecord, Shift classes)
- **Modifying authentication** (login, password handling)
- **Updating dependencies** (requirements.txt changes)
- **Changing timezone settings**
- **Modifying data structure** (adding/removing fields)

For these cases:
1. ✅ Export backup first
2. ✅ Test thoroughly
3. ✅ Have a rollback plan
4. ✅ Monitor after deployment

---

## ❓ FAQ

### Q: Will my data be deleted when I deploy?
**A:** No! Your database persists across deployments. Only code changes.

### Q: Do I need to backup every time?
**A:** Not required, but recommended before major changes. Regular small updates are usually safe.

### Q: What if I forget to backup?
**A:** Your data is likely still safe. The database doesn't get deleted automatically. But always backup before major changes to be safe.

### Q: Can I restore individual records?
**A:** Currently, the restore function restores everything. Individual record restore can be added if needed.

### Q: How often should I backup?
**A:** 
- **Before major changes:** Always
- **Weekly:** Recommended for active systems
- **After important data entry:** Good practice

---

## 📞 Need Help?

If you encounter issues:
1. Check the backup/restore logs
2. Verify your database connection
3. Check Railway/Render deployment logs
4. Review error messages carefully

---

**Remember:** Your data is safe! The backup feature is just an extra safety measure. Code deployments don't automatically delete your database.

