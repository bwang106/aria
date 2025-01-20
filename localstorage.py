import json
from localStoage import localStoragePy

local_storage = localStoragepy('example.mistral_app', 'json')


data = {'what': 'item','where': 'location','status': 'available','timestamp': '2022-01-01T00:00:00.000Z'}
json_data = json.dumps(data)
local_storage.setItem('item_info', json_data)

retrieved_json = local_storage.getItem('item_info')
retrieved_data = json.loads(retrieved_json)
print(retrieved_data)