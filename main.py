import os
import time
import json
import requests
import hashlib
from datetime import datetime, timedelta
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from keycloak import KeycloakOpenID

tests_filename = './tests.json'
config_filename = './pibity-erp/src/main/resources/postmaster.json'


with open('./pibity-erp/src/main/resources/postmaster.json', 'r') as config_file:
    config = json.loads(config_file.read())
    config_hash = hashlib.sha256(json.dumps(
        config).encode('utf-8')).hexdigest()

client_secret = config['keycloakClientSecret']
run_count = int(config['runCount'])

keycloak_openid = KeycloakOpenID(server_url="http://localhost:8081/auth/",
                    client_id="pibity-erp-admin",
                    realm_name="inventory",
                    client_secret_key=client_secret,
                    verify=True)
token = 'Bearer ' + keycloak_openid.token("superuser@pibity.com", "1234")['access_token']


def execute_tests(hash_override=False):
    global token
    headers = {'content-type': 'application/json', 'Authorization': token}
    with open(tests_filename, 'r') as tests_json, open('urls.json', 'r') as urls_json:
        tests = json.loads(tests_json.read())
        urls = json.loads(urls_json.read())
    test_outputs = []
    step = 0
    orgId = 1
    prev_block_hash = ''
    for index, test in enumerate(tests):
        step += 1
        url = urls['server'] + test['url']
        request = test['request']
        # Hash is computed based only on URL and Request Body (Needs to be calculated before further modifying above structure)
        test_output_hash = hashlib.sha256(json.dumps(
            {'url': test['url'], 'request': test['request'], 'prev_block_hash': prev_block_hash}).encode('utf-8')).hexdigest()
        prev_block_hash = test_output_hash
        test_output = {}
        test_output['step'] = step
        if not hash_override and 'hash' in test and test['hash'] == test_output_hash:
            if test['url'] == 'organization/create':
                orgId = int(test['response']['id'])
            test_outputs.append(test)
            with open(tests_filename, 'w') as output:
                temp_tests = test_outputs.copy()
                temp_tests.extend(tests[(index+1):])
                output.write(json.dumps(temp_tests, indent=4))
            print('SKIPPING STEP', step, '\n')
            continue
        if test['url'] != 'organization/create':
            request['orgId'] = orgId
        print('\n', 'STEP   :', step)
        print('\n', 'HASH   :', test_output_hash)
        print('\n', 'URL    :', url)
        print('\n', 'REQUEST:', json.dumps(request, indent=1))
        try:
            response = requests.post(url, data=json.dumps(request), headers=headers)
        except:
            return
        if response.status_code == 200 and test['url'] == 'organization/create':
            orgId = int(response.json()['id'])
            token = 'Bearer ' + \
                keycloak_openid.token(
                    "superuser@pibity.com", "1234")['access_token']
        if response.status_code == 200:
            print('\n', 'RESPONSE:', json.dumps(response.json(), indent=1))
            test_output['hash'] = test_output_hash
            test_output['response'] = response.json()
        else:
            test_output_response = {}
            test_output_response['statusCode'] = response.status_code
            print('\n', 'STATUS CODE:', response.status_code)
            try:
                if 'message' in response.json():
                    test_output_response['error'] = response.json()['message']
                else:
                    test_output_response['error'] = response.json()
                print('\n', 'ERROR:', json.dumps(test_output_response['error'], indent=1))
            except:
                test_output_response['error'] = response.text
                pass
            test_output['response'] = test_output_response
            test_output['url'] = test['url']
            test_output['request'] = request
            test_outputs.append(test_output)
            with open(tests_filename, 'w') as output:
                temp_tests = test_outputs.copy()
                for temp_test in tests[(index+1):]:
                    t = {}
                    t['url'] = temp_test['url']
                    t['request'] = temp_test['request']
                    temp_tests.append(t)
                output.write(json.dumps(temp_tests, indent = 4))
            print('\n', 'STOPPING EXECUTION')
            break
        test_output['url'] = test['url']
        test_output['request'] = request
        test_outputs.append(test_output)
        print('\n', '--------------------------------------------')
        with open(tests_filename, 'w') as output:
            temp_tests = test_outputs.copy()
            for temp_test in tests[(index+1):]:
                t = {}
                t['hash'] = test_output_hash
                t['url'] = temp_test['url']
                t['request'] = temp_test['request']
                temp_tests.append(t)
            output.write(json.dumps(temp_tests, indent = 4))

execute_tests(hash_override = True)

class MyEventHandler(PatternMatchingEventHandler):
    def on_any_event(self, event):
        global config, client_secret, run_count, keycloak_openid, token
#         print(f'Event type: {event.event_type}  path : {event.src_path}')
        if event.src_path == (tests_filename):
            print('\n', 'DETECTED: CHANGE IN TESTS')
            execute_tests()
            time.sleep(6)
        elif event.src_path == (config_filename):
            with open('./pibity-erp/src/main/resources/postmaster.json', 'r') as config_file:
                config = json.loads(config_file.read())
            if config_hash != hashlib.sha256(json.dumps(config).encode('utf-8')).hexdigest():
                if client_secret != config['keycloakClientSecret']:
                    print('\n', 'DETECTED: TOKEN UPDATE')
                    client_secret = config['keycloakClientSecret']
                    keycloak_openid = KeycloakOpenID(server_url="http://localhost:8081/auth/",
                                        client_id="pibity-erp-admin",
                                        realm_name="inventory",
                                        client_secret_key=client_secret,
                                        verify=True)
                    token = 'Bearer ' + keycloak_openid.token("superuser@pibity.com", "1234")['access_token']
                if run_count != config['runCount']:
                    run_count = config['runCount']
                    print('\n', 'DETECTED: SERVER RESTART')
                    time.sleep(6)
                    execute_tests(hash_override = True)


event_handler = MyEventHandler(patterns=['*.json'], ignore_patterns=[], ignore_directories=True)
observer = Observer()
observer.schedule(event_handler, '.', recursive=True)
observer.start()
try:
    while True:
        time.sleep(1)
finally:
    observer.stop()
    observer.join()
