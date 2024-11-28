import redis

# Correctly connect to Redis with a secure URL
redis_url = "rediss://red-csd5erbv2p9s73ft12r0:t8sOTs71C4qj1uQj1cpHz49KCRPAjsyM@oregon-redis.render.com:6379"
redis_client = redis.from_url(redis_url, decode_responses=True)

# List all keys
try:
    keys = redis_client.keys("*")
    print("Keys in Redis:", keys)

    # Get a specific key's value
    for key in keys:
        value = redis_client.get(key)  # Or use the appropriate method for complex data types
        print(f"Key: {key}, Value: {value}")
except Exception as e:
    print("Error interacting with Redis:", e)
