# Quick Setup Guide

## Step-by-Step Setup

### 1. Install Python Packages
```bash
pip install -r requirements.txt
```

### 2. Set Up Supabase Database

1. Go to https://supabase.com and create a free account
2. Create a new project (choose a region close to you)
3. Wait for the project to be created (takes ~2 minutes)
4. Go to the **SQL Editor** (left sidebar)
5. Copy and paste the entire contents of `supabase_schema.sql`
6. Click "Run" to create the tables

### 3. Get Your Supabase Credentials

1. In your Supabase project, go to **Settings** (gear icon) > **API**
2. Copy the **Project URL** (looks like: https://xxxxx.supabase.co)
3. Copy the **anon public** key (under "Project API keys")

### 4. Create .env File

1. Create a new file called `.env` in the project root
2. Add your credentials:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key-here
```

### 5. Configure Family Users

Edit `users.json` and replace with your family members:
```json
{
  "users": [
    {
      "username": "mom",
      "password": "SecurePass123!",
      "display_name": "Mom"
    },
    {
      "username": "dad",
      "password": "SecurePass456!",
      "display_name": "Dad"
    },
    {
      "username": "alice",
      "password": "SecurePass789!",
      "display_name": "Alice"
    }
  ]
}
```

**IMPORTANT**: Use strong, unique passwords!

### 6. Run the App

```bash
streamlit run streamlit_app.py
```

The app will open in your browser at http://localhost:8501

## Testing the App

1. **Create a Gift List**:
   - Log in as any user
   - In the sidebar, create a new list (e.g., "Mom's Wishlist")
   - Select Mom as the recipient

2. **Add Gifts** (as recipient):
   - Log in as Mom
   - Add some gifts to her list
   - Notice you can only see your own gifts

3. **View and Manage Gifts** (as buyer):
   - Log out and log in as Dad or Alice
   - Open Mom's list
   - You can now see ALL the gifts
   - Mark gifts as "Want to Buy", "Buy Shared", or "Bought"
   - Add comments to coordinate with others

## Troubleshooting

### "Please set SUPABASE_URL and SUPABASE_KEY"
- Make sure you created the `.env` file
- Check that the file is in the same directory as `streamlit_app.py`
- Verify your credentials are correct

### "Import supabase could not be resolved"
- Run: `pip install -r requirements.txt`
- Make sure you're using the correct Python environment

### No tables in Supabase
- Go to Supabase SQL Editor
- Run the `supabase_schema.sql` script
- Check the "Table Editor" to verify tables were created

### Login not working
- Check `users.json` has the correct format
- Make sure usernames match exactly (case-sensitive)

## Need Help?

Check the full README.md for more detailed information.
