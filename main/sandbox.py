from utils.utils import log
import requests


class Sandbox_API(object):

    def __init__(self, cuckoo_API, SECRET_KEY, timeout):
        self.cuckoo_API = cuckoo_API
        self.SECRET_KEY = SECRET_KEY
        self.timeout = timeout
        return


    def start_analysis(self, filepath):
        REST_URL = self.cuckoo_API+'/tasks/create/file'
        HEADERS = {'Authorization': self.SECRET_KEY}

        log(f'   [ ][start_analysis] Submiting {filepath} to cuckoo via api {REST_URL}')
        with open(filepath, 'rb') as sample:
            # files = {'file': ('temp_file_name', sample)}
            files = {'file': sample}
            data = {'enforce_timeout': True, 'timeout': self.timeout}
            r = requests.post(REST_URL, headers=HEADERS, files=files, data=data)

        print('r', r)

        #? Error checking for r.status_code
        if r.status_code != 200:
            log(f'   [x] Failed to create task for file {filepath}. Reason: {r.reason}', 'error')
            return None

        task_id = r.json()['task_id']
        log(f'   [+] Created task for Cuckoo: {task_id}')

        return task_id


    def get_task_status(self, task_id):
        REST_URL = self.cuckoo_API+'/tasks/view/{}'.format(task_id)
        HEADERS = {'Authorization': self.SECRET_KEY}

        r = requests.get(REST_URL, headers=HEADERS)

        response = r.json()
        print('[ ][get_task_status] response', response)

        if 'task' not in response:
            return 'error', 'Error'

        task = response['task']

        if 'errors' in task:
            errors = list(filter(None, task['errors']))
            if len(errors) > 0:
                return 'error', errors

        return task['status'], task


    def get_report(self, task_id):
        REST_URL = self.cuckoo_API+'/tasks/report/{}'.format(task_id)
        HEADERS = {'Authorization': self.SECRET_KEY}

        r = requests.get(REST_URL, headers=HEADERS)

        task = r.json()

        return task