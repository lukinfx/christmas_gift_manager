# � Christmas Gift Manager

A family Christmas gift management app built with Streamlit and Supabase. This app allows family members to create gift lists, add wishes, and coordinate gift purchases without spoiling surprises!

## Features

- **User Authentication**: Simple username/password login system defined in `users.json`
- **Gift Lists**: Create lists with multiple recipients
- **Smart Visibility**: 
  - Recipients can only see gifts they added themselves (keeps surprises!)
  - Non-recipients can see all gifts and manage purchases
- **Gift Status Management**:
  - Want to buy
  - Want to buy together (for expensive gifts)
  - Bought
- **Comments**: Add notes and coordinate with other gift buyers

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Supabase

1. Create a free account at [supabase.com](https://supabase.com)
2. Create a new project
3. Go to the SQL Editor and run the contents of `supabase_schema.sql` to create the tables
4. Get your project URL and anon key from Settings > API

### 3. Configure Environment

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` and add your Supabase credentials:
   ```
   SUPABASE_URL=your_project_url
   SUPABASE_KEY=your_anon_key
   ```

### 4. Configure Users

Edit `users.json` to add your family members:

```json
{
  "users": [
    {
      "username": "john",
      "password": "john123",
      "display_name": "John"
    }
  ]
}
```

**Important**: Change the default passwords!

### 5. Run the App

```bash
streamlit run streamlit_app.py
```

## How It Works

### For Recipients (People receiving gifts)
- Log in with your credentials
- Add gifts you'd like to receive to any list where you're a recipient
- You can only see the gifts YOU added, not what others want to buy for you
- This keeps the surprise intact!

### For Gift Buyers (People buying gifts)
- Log in with your credentials
- View lists where you're NOT a recipient
- See ALL gifts in those lists
- Mark gifts as:
  - "Want to Buy" - You plan to buy this
  - "Buy Shared" - You want to split the cost with others
  - "Mark Bought" - You've purchased it
- Add comments to coordinate with other buyers

### Creating Gift Lists
- Use the sidebar to create a new list
- Give it a name (e.g., "Mom's Wishlist", "Kids' Christmas")
- Select the recipients (people who will receive these gifts)
- Anyone can create lists!

## Database Schema

### Tables
- **gift_lists**: Stores gift lists with recipients
- **gifts**: Individual gift items with status tracking
- **gift_comments**: Comments on gifts for coordination

## Security Notes

- This is a simple family app with basic authentication
- Passwords are stored in plain text in `users.json` - suitable for trusted family use only
- For production use, implement proper authentication and password hashing
- The `.env` file should never be committed to version control (it's already in `.gitignore`)

## Customization

- Modify `users.json` to add/remove family members
- Update the database schema for additional features
- Customize the Streamlit theme in `.streamlit/config.toml`

## Support

For issues or questions, please open an issue on the GitHub repository.
