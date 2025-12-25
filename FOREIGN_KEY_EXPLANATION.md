# Foreign Key Constraint Error - Explained

## What Happened?

You tried to delete a user and got this error:
```
ERROR: update or delete on table "user" violates foreign key constraint "shift_agent_id_fkey" 
on table "shift" 
DETAIL: Key (id)=(2) is still referenced from table "shift".
```

## What Does This Mean?

**In simple terms:** You can't delete a user that still has related data (shifts or break records).

### Why?

PostgreSQL uses **foreign key constraints** to maintain data integrity. This means:

1. **User ID 2** has shifts in the `shift` table
2. Those shifts reference the user via `agent_id = 2`
3. If you delete the user, those shifts would point to a non-existent user
4. PostgreSQL prevents this to avoid "orphaned" data

### The Relationship:

```
User (id=2)
  ↓
  ├── Shift 1 (agent_id=2) ← References user
  ├── Shift 2 (agent_id=2) ← References user
  ├── Break Record 1 (agent_id=2) ← References user
  └── Break Record 2 (agent_id=2) ← References user
```

## Solution: Safe Delete Function

I've added a **safe delete endpoint** that handles this automatically:

### How It Works:

1. **First**: Deletes all shifts for the agent
2. **Second**: Deletes all break records for the agent
3. **Third**: Deletes the user (now safe - no references left)

### How to Use:

**Option 1: Use the API endpoint (Recommended)**
```javascript
// In your dashboard JavaScript
fetch(`/api/agent/${agentId}/delete`, {
    method: 'DELETE',
    headers: {
        'Content-Type': 'application/json'
    }
})
```

**Option 2: Manual deletion (if using database directly)**
```sql
-- Step 1: Delete shifts
DELETE FROM shift WHERE agent_id = 2;

-- Step 2: Delete break records
DELETE FROM break_record WHERE agent_id = 2;

-- Step 3: Delete user (now safe)
DELETE FROM "user" WHERE id = 2;
```

## Important Notes:

- ✅ **Safe Delete Function**: Always deletes related data first
- ✅ **Prevents Orphaned Data**: No broken references
- ✅ **Reports What Was Deleted**: Shows counts of deleted records
- ⚠️ **Cannot Delete Yourself**: Safety feature
- ⚠️ **Cannot Delete RTM Users**: Protection for admin accounts

## Alternative: Cascade Delete (Advanced)

If you want automatic deletion, you can modify the models to use `ondelete='CASCADE'`:

```python
# In app.py, modify the Shift model:
agent_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)

# And BreakRecord model:
agent_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
```

**Warning**: Cascade delete is automatic and cannot be undone. Use with caution!

## Summary

- **Error = Safety Feature**: PostgreSQL is protecting your data integrity
- **Solution = Delete in Order**: Delete related data first, then the user
- **Safe Delete Function**: Handles this automatically via API endpoint

