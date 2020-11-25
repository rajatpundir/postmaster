import os, time, json, requests, hashlib
from datetime import datetime, timedelta
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from git import Repo

tests_filename = 'tests.json'
token = 'Bearer eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICI3RjE2NHhQVlYzTTBCU1ZDZ1dEQTBKOVh5b1UzWEdQRVJ3SlZDLXZVUmF3In0.eyJleHAiOjE2MDYzMjcyMzgsImlhdCI6MTYwNjI5MTIzOCwiYXV0aF90aW1lIjoxNjA2MjkxMjM4LCJqdGkiOiI5ZWQzMjc0My04MzdkLTQ4MjItOWE0OC05NzNiMGZiNTczYTUiLCJpc3MiOiJodHRwOi8vbG9jYWxob3N0OjgwODEvYXV0aC9yZWFsbXMvaW52ZW50b3J5IiwiYXVkIjpbInJlYWxtLW1hbmFnZW1lbnQiLCJhY2NvdW50Il0sInN1YiI6ImE4MzE1Y2JjLTA2NGUtNDE2Zi04N2Y2LTg1NmE5ODg2ZTQyOCIsInR5cCI6IkJlYXJlciIsImF6cCI6InBpYml0eS1lcnAiLCJub25jZSI6IjdmZjQ5MzhjLWEwZGQtNDEwYS1hOTY1LTc4NzI4NDZmZDE3YiIsInNlc3Npb25fc3RhdGUiOiJmOTI2NTJmNi1hOTEzLTRlNGUtYjNiMS1hOWMxYzZmYWM0NTEiLCJhY3IiOiIxIiwiYWxsb3dlZC1vcmlnaW5zIjpbImh0dHA6Ly9sb2NhbGhvc3Q6MzAwMCJdLCJyZWFsbV9hY2Nlc3MiOnsicm9sZXMiOlsiU1VQRVJVU0VSIiwiVVNFUiJdfSwicmVzb3VyY2VfYWNjZXNzIjp7InJlYWxtLW1hbmFnZW1lbnQiOnsicm9sZXMiOlsidmlldy1pZGVudGl0eS1wcm92aWRlcnMiLCJ2aWV3LXJlYWxtIiwibWFuYWdlLWlkZW50aXR5LXByb3ZpZGVycyIsImltcGVyc29uYXRpb24iLCJyZWFsbS1hZG1pbiIsImNyZWF0ZS1jbGllbnQiLCJtYW5hZ2UtdXNlcnMiLCJxdWVyeS1yZWFsbXMiLCJ2aWV3LWF1dGhvcml6YXRpb24iLCJxdWVyeS1jbGllbnRzIiwicXVlcnktdXNlcnMiLCJtYW5hZ2UtZXZlbnRzIiwibWFuYWdlLXJlYWxtIiwidmlldy1ldmVudHMiLCJ2aWV3LXVzZXJzIiwidmlldy1jbGllbnRzIiwibWFuYWdlLWF1dGhvcml6YXRpb24iLCJtYW5hZ2UtY2xpZW50cyIsInF1ZXJ5LWdyb3VwcyJdfSwiYWNjb3VudCI6eyJyb2xlcyI6WyJtYW5hZ2UtYWNjb3VudCIsIm1hbmFnZS1hY2NvdW50LWxpbmtzIiwidmlldy1wcm9maWxlIl19fSwic2NvcGUiOiJvcGVuaWQgZW1haWwgcHJvZmlsZSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiZ3JvdXBzIjpbIi8xL0FETUlOIiwiLzEvVVNFUiJdLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJzdXBlcnVzZXJAcGliaXR5LmNvbSJ9.I3BwyVIDI0BUn48pNzkHUb9VL2hl1X6bOy6Jbam0Z6eUaBtcrEfMLqqef_7rzE0rrVH2hTlr_Ax5eRf7IYOYOQgMud6Nsz8IKgZagdarcnjoenItAdV78m3X7j0K7GLG_uYCMowc9Dcn_8YO9udM7ILBaGin_ln4egbETqEWUM9AbKx14Vfn128M1BOnnRfApJ_OmWNM8zZcC59FlOJ7VogGoZgtUaWjphjb3P1Fm6jWba4oojMGPTzCxtg_Try8hhPWCb_TV5SdLw5QLFwzl6VCeVJNShhhDSPDkd5gkKLTMsJDWXw1csmtoeelJ5UDUF_lA8g9ILy41axci9qWAA'
hash_change_detected = False
repo = Repo.init("./postgres")

def checkout_branch(branch_to_checkout):
    global repo
    branches = {}
    print('Previous Branch:', repo.active_branch.name)
    for head in repo.heads:
        branches[head.name] = head
    if repo.active_branch.name != branch_to_checkout:
        if branch_to_checkout in branches:
            branches[branch_to_checkout].checkout()
        else:
            branches[branch_to_checkout] = repo.create_head(branch_to_checkout)
    print('Current Branch:', repo.active_branch.name)
    return branches

def get_commits(branch_name):
    global repo
    commits = list(repo.iter_commits(branch_name))
    commits.reverse()
    return commits

def get_first_resettable_commit(branch_name):
    global repo
    commits = get_commits(branch_name)
    resettable_commit = commits[0]
    for commit in commits:
        if len(commit.message) == 64:
            break
        else:
            resettable_commit = commit
    print('Last Resettable Commit is:', resettable_commit.message)
    return resettable_commit

def execute_tests(branch_name = 'master'):
    global repo
    checkout_branch(branch_name)
    commits = get_commits(branch_name)
    resettable_commit = get_first_resettable_commit(branch_name)
    print('Commit Messages')
    commit_messages = {}
    for commit in commits:
        if not commit.message in commit_messages:
            commit_messages[commit.message] = commit.hexsha
            print(commit.hexsha, commit.message)
    headers = {'content-type': 'application/json', 'Authorization': token}
    with open(tests_filename, 'r') as tests_json, open('urls.json', 'r') as urls_json:
        tests = json.loads(tests_json.read())
        urls = json.loads(urls_json.read())
    test_outputs = []
    step = 0
    for index, test in enumerate(tests):
        step += 1
        url = urls['server'] + test['url']
        request = test['request']
        test_output = {}
        test_output['url'] = test['url']
        test_output['request'] = request
        # Hash is computed based only on URL and Request Body (Needs to be calculated before further modifying above structure)
        test_output_hash = hashlib.sha256(json.dumps(test_output).encode('utf-8')).hexdigest()
        test_output['step'] = step
        response = requests.post(url, data=json.dumps(request), headers=headers)
        global hash_change_detected
        if not hash_change_detected:
            if test_output_hash in commit_messages:
                hash_change_detected = True
                resettable_commit = commit_messages[test_output_hash]
                print('Last Resettable Commit is:', resettable_commit.message)
                test_outputs.append(test)
                with open(tests_filename, 'w') as output:
                    temp_tests = test_outputs.copy()
                    temp_tests.extend(tests[(index+1):])
                    output.write(json.dumps(temp_tests, indent = 4))
                print('SKIPPING STEP', step, '\n')
                continue
            else:
                repo.head.reset(resettable_commit, index=True, working_tree=True)
        print('STEP', step, '\n')
        print('URL:', url, '\n')
        print('REQUEST:', json.dumps(request, indent = 1), '\n')
        if response.status_code == 200:
            print('RESPONSE:', json.dumps(response.json(), indent = 1))
            test_output['response'] = response.json()
        else:
            test_output_response = {}
            test_output_response['statusCode'] = response.status_code
            print('STATUS CODE:', response.status_code)
            try:
                print('ERROR:', json.dumps(response.json(), indent = 1))
                test_output_response['error'] = response.json()
            except:
                test_output_response['error'] = response.text
                pass
            test_output['response'] = test_output_response
            test_outputs.append(test_output)
            with open(tests_filename, 'w') as output:
                temp_tests = test_outputs.copy()
                for temp_test in tests[(index+1):]:
                    t = {}
                    t['url'] = temp_test['url']
                    t['request'] = temp_test['request']
                    temp_tests.append(t)
                output.write(json.dumps(temp_tests, indent = 4))
            print('STOPPING EXECUTION')
            break
        test_outputs.append(test_output)
        print('-------------------------------------' + '\n')
        with open(tests_filename, 'w') as output:
            temp_tests = test_outputs.copy()
            for temp_test in tests[(index+1):]:
                t = {}
                t['url'] = temp_test['url']
                t['request'] = temp_test['request']
                temp_tests.append(t)
            output.write(json.dumps(temp_tests, indent = 4))
#         repo.index.add('tests.json')
        repo.index.commit(test_output_hash)


class WatchdogHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_modified = datetime.now()
    def on_modified(self, event):
        if datetime.now() - self.last_modified < timedelta(seconds=1):
            return
        else:
            self.last_modified = datetime.now()
#         print(f'Event type: {event.event_type}  path : {event.src_path}')
#         print(event.is_directory)
        if not event.is_directory and event.src_path == ('./' + tests_filename) :
            execute_tests()


execute_tests()
# observer = Observer()
# observer.schedule(WatchdogHandler(), path='.', recursive=False)
# observer.start()
# try:
#     while True:
#         time.sleep(1)
# except KeyboardInterrupt:
#     observer.stop()
# observer.join()

