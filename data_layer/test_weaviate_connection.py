import weaviate

# Connect to your local Weaviate instance (v4+ syntax)
client = weaviate.connect_to_local()

# Check connection
if client.is_ready():
    print("✅ Weaviate is connected and ready!")
else:
    print("❌ Connection failed.")

# Close connection
client.close()
