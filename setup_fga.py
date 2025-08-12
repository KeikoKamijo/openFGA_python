#!/usr/bin/env python3
import asyncio
import os
from dotenv import load_dotenv
from openfga_sdk import OpenFgaClient, ClientConfiguration, CreateStoreRequest, WriteAuthorizationModelRequest

load_dotenv()

async def setup_fga():
    # Create client without store_id initially
    client = OpenFgaClient(ClientConfiguration(
        api_url=os.getenv('FGA_API_URL', 'http://localhost:8080')
    ))
    
    # Create a new store
    store_name = "demo-store"
    store_request = CreateStoreRequest(name=store_name)
    store_response = await client.create_store(store_request)
    store_id = store_response.id
    print(f"Created store with ID: {store_id}")
    
    # Create new client with store_id
    client = OpenFgaClient(ClientConfiguration(
        api_url=os.getenv('FGA_API_URL', 'http://localhost:8080'),
        store_id=store_id
    ))
    
    # Create authorization model
    model_request = WriteAuthorizationModelRequest(
        schema_version="1.1",
        type_definitions=[
            {
                "type": "user",
                "relations": {}
            },
            {
                "type": "resource",
                "relations": {
                    "owner": {
                        "this": {}
                    },
                    "editor": {
                        "this": {}
                    },
                    "viewer": {
                        "union": {
                            "child": [
                                {"this": {}},
                                {"computedUserset": {"relation": "editor"}},
                                {"computedUserset": {"relation": "owner"}}
                            ]
                        }
                    }
                },
                "metadata": {
                    "relations": {
                        "owner": {
                            "directly_related_user_types": [
                                {"type": "user"}
                            ]
                        },
                        "editor": {
                            "directly_related_user_types": [
                                {"type": "user"}
                            ]
                        },
                        "viewer": {
                            "directly_related_user_types": [
                                {"type": "user"}
                            ]
                        }
                    }
                }
            }
        ]
    )
    
    model_response = await client.write_authorization_model(model_request)
    model_id = model_response.authorization_model_id
    print(f"Created model with ID: {model_id}")
    
    # Update .env file with new values
    env_path = '.env'
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    # Update or add FGA_STORE_ID and FGA_MODEL_ID
    updated = False
    new_lines = []
    for line in lines:
        if line.startswith('FGA_STORE_ID='):
            new_lines.append(f'FGA_STORE_ID={store_id}\n')
            updated = True
        elif line.startswith('FGA_MODEL_ID='):
            new_lines.append(f'FGA_MODEL_ID={model_id}\n')
            updated = True
        else:
            new_lines.append(line)
    
    if not updated:
        new_lines.append(f'FGA_STORE_ID={store_id}\n')
        new_lines.append(f'FGA_MODEL_ID={model_id}\n')
    
    with open(env_path, 'w') as f:
        f.writelines(new_lines)
    
    print(f"\n.env file updated with:")
    print(f"FGA_STORE_ID={store_id}")
    print(f"FGA_MODEL_ID={model_id}")
    print("\nSetup complete! Please restart your FastAPI server.")

if __name__ == "__main__":
    asyncio.run(setup_fga())