import asyncio
import httpx
import json


async def test_nvidia_api_direct():
    """Test NVIDIA API endpoints directly"""

    base_url = "http://127.0.0.1:8081"

    print("=" * 60)
    print("NVIDIA API Direct Test")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Test models endpoint
        print("\n1. Testing /nvidia/models endpoint...")
        try:
            resp = await client.get(f"{base_url}/nvidia/models")
            print(f"   Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"   Total models: {data.get('count', 0)}")
                models = data.get("models", [])
                print(f"   First 5 models:")
                for m in models[:5]:
                    print(f"      - {m['id']}")
        except Exception as e:
            print(f"   Error: {e}")

        # 2. Test curated models endpoint
        print("\n2. Testing /nvidia/curated endpoint...")
        try:
            resp = await client.get(f"{base_url}/nvidia/curated")
            print(f"   Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("models", [])
                print(f"   Curated models count: {len(models)}")
                for m in models:
                    print(f"      - {m['id']}: {m.get('name', 'N/A')}")
        except Exception as e:
            print(f"   Error: {e}")

        # 3. Test generate endpoint
        print("\n3. Testing /nvidia/generate endpoint...")
        try:
            payload = {
                "model": "meta/llama-3.1-8b-instruct",
                "prompt": "Write a short poem about AI.",
                "max_tokens": 100,
                "temperature": 0.7,
            }
            print(f"   Model: {payload['model']}")
            print(f"   Prompt: {payload['prompt']}")
            print("   Sending request...")

            resp = await client.post(f"{base_url}/nvidia/generate", json=payload)
            print(f"   Status: {resp.status_code}")

            if resp.status_code == 200:
                data = resp.json()
                print(f"   Response received!")
                print(f"   Content: {data.get('content', 'N/A')[:200]}...")
            else:
                print(f"   Error response: {resp.text}")
        except Exception as e:
            print(f"   Error: {e}")

        # 4. Test validate endpoint
        print("\n4. Testing /nvidia/validate endpoint...")
        try:
            resp = await client.get(f"{base_url}/nvidia/validate")
            print(f"   Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"   Valid: {data.get('valid', False)}")
        except Exception as e:
            print(f"   Error: {e}")

    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_nvidia_api_direct())
