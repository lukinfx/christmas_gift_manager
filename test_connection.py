"""
Test script to verify Supabase connection and check if tables exist
"""
import os
import certifi
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

# Set SSL certificate file path for Windows
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

# Initialize Supabase client
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    print("❌ Error: SUPABASE_URL and SUPABASE_KEY not found in .env")
    exit(1)

print(f"✓ Found Supabase URL: {url}")
print(f"✓ Found Supabase Key: {key[:20]}...")

try:
    supabase = create_client(url, key)
    print("✓ Connected to Supabase successfully!")
    
    # Try to query each table
    tables = ['gift_lists', 'gifts', 'gift_comments']
    
    for table in tables:
        try:
            result = supabase.table(table).select('count', count='exact').limit(0).execute()
            print(f"✓ Table '{table}' exists")
        except Exception as e:
            print(f"❌ Table '{table}' does not exist or has issues: {str(e)}")
            print("\n🔧 Please run the SQL script from 'supabase_schema.sql' in your Supabase SQL Editor")
            print("   1. Go to your Supabase project")
            print("   2. Open SQL Editor")
            print("   3. Copy and paste the contents of supabase_schema.sql")
            print("   4. Click 'Run'\n")
    
    print("\n✅ Setup verification complete!")
    
except Exception as e:
    print(f"❌ Error connecting to Supabase: {str(e)}")
    print("\nPlease check your .env file and make sure your Supabase credentials are correct.")
