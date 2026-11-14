import requests

url = "http://127.0.0.1:8000/api/predict"

payload = {
    "thickness_um": 100.0,
    "oxygen_percent": 22.2,
    "flow_velocity": 50.0
}

response = requests.post(url, json=payload)

if response.status_code == 200:
    print("API Response:")
    print(response.json())
else:
    print(f"Request failed with status code {response.status_code}:")
    print(response.text)