# Copyright 2022 by Minh Nguyen. All rights reserved.
#     @author Minh Tu Nguyen
#     @email  nmtu.mia@gmail.com
# 
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from worker.base.silentworker_base import SilentWorkerBase
from utils.utils import log
import json
import os
import time
from main.sandbox import Sandbox_API
import shutil
import glob
import subprocess


class SilentWorker(SilentWorkerBase):
    """
    This is the baseline for the SilentWorker.

    SilentWorker should be the one carrying the main work.
    Sometimes a module might take a great deal of time to generate outputs. 

    Whenever your model finishes an operation, make sure to call `__onFinish__` function to populate your results to db as well as to the next module in the chain.
        Command:
            self.__onFinish__(output[, note])

        whereas:
            - output (mandatory): A dict that maps a `orig_input_hash` => output
                Output could be of any type. Just make sure to note that in your module's configuration and description for others to interpret your results.
                For example,
                    - a detector module can return a boolean (to represent detection result).
                    - a non-detector module (eg. processor or sandbox) can return the path storing processed result.
                eg.
                    {
                        'hash_of_input_1': true,
                        'hash_of_input_2': false,
                        'hash_of_input_3': false,
                        ...
                    }
            - note (optional).
                It could be a dict or a string.
                If it's a dict, it must be a map of a filepath to a note (string). The system will find and save the note accordingly with the file. 
                If it's not a map, use a string. The system will save this note for all the files analyzed in this batch
    """

    def __init__(self, config) -> None:
        """ Dont change/remove this super().__init__ line.
            This line passes config to initialize services. 
        """
        super().__init__(config)

        #! Add your parts of initializing the model or anything you want here. 
        #! You might want to load everything at this init phase, not reconstructing everything at each request (which shall then be defined in run())
        print('Nooby doo')
        if 'cuckoo_API' not in config or 'cuckoo_SECRET_KEY' not in config or 'cuckoo_timeout' not in config:
            log(f'[x] Missing config for sandbox', 'error')
            exit()
        self.sandbox = Sandbox_API(config['cuckoo_API'], config['cuckoo_SECRET_KEY'], config['cuckoo_timeout'])

    
    def onChangeConfig(self, config_data):
        """
        Callback function when module's config is changed.
        (usually at each request to analyze, when config_data is sent along as a parameter)
        ---
        This is the module's config which is passed at each analysis request. (usually the config to initialize the model)
        """

        log(f'[ ][SilentWorker][onChangeConfig] config_data is passed: {config_data}')

        #! Want to do something with the model when the config is changed ? Maybe reconfig the model's params, batch size etc. ?
        #? eg. change global module's config
        #self._config = config_data
        #? let my main module decide
        
        return


    def infer(self, config_data):
        """
        #? This function is to be overwritten.
        Main `inference` function. 

            #? (used for all modules, `detector`, `(pre)processor`, `sandbox`)
            Whatever you need to do in silence, put it here.
            We provide inference in batch, for heavy models.

        ----
        Use these vars to access input data:
            - self._map_ohash_inputs: dict of inputs to feed this module (eg. filepath to the executable files already stored on the system / url).
                map `orig_input_hash` => `prev module's output for orig_path correspond with orig_input_hash`
            - self._map_ohash_oinputs: dict of original inputs that is fed to this module flow.
                map `orig_input_hash` => one `orig_path`.
                (multiple orig_path might have the same hash, but just map to one path)
        
        Params:
            - config_data: modules configuration stored in the db.
        """

        #! Do something
        log('[ ][SilentWorker][infer] I\'m pretty')

        """ Submit to cuckoo """
        map_ohash_taskid = {}
        for ohash,filepath in self._map_ohash_inputs.items():
            if not os.path.isfile(filepath):
                log(f'[!][SilentWorker][infer] File not exists: {filepath}')
                continue
            task_id = self.sandbox.start_analysis(filepath)
            if task_id is None: #? something went wrong
                return
            map_ohash_taskid[ohash] = task_id

        """ Write `map_ohash_taskid` to a file for other thread to check status of these tasks """
        last_idx = 0
        tasks_filepaths = sorted(glob.glob('.*.task_ids.tmp'), reverse=True)
        if len(tasks_filepaths) > 0:
            last_idx = int(tasks_filepaths[0].split('.task_ids.tmp')[0].split('.')[1])
        last_idx += 1
        new_filepath = f'.{last_idx}.task_ids.tmp'
        json.dump(map_ohash_taskid, open(new_filepath, 'w'))


    def check_tasks_status(self):
        """
        Cuckoo might take some time to generate reports.
        So open a thread to check status of submitted tasks.
        This function will be called from `worker_threads.py`
        """
        # log(f'[check_tasks_status] module_code: {self.module_code}')

        try:
            #? get all files that store tasks ids
            tasks_filepaths = sorted(glob.glob('.*.task_ids.tmp'))

            cuckoo_reports_dir = self._config['cuckoo_reports_dir'] if 'cuckoo_reports_dir' in self._config else '/home/'
            cuckoo_filesrv = self._config['cuckoo_filesrv'] if 'cuckoo_filesrv' in self._config else ""

            for tasks_filepath in tasks_filepaths:
                print(f'[ ][check_tasks_status] tasks_filepath', tasks_filepath)
                result = {} #? required.  {}
                note = {} #? optional.  {} | ''

                map_ohash_taskid = json.load(open(tasks_filepath))

                for ohash,task_id in map_ohash_taskid.items():
                    task_id = str(task_id)
                    while True: #? check until status return `reported`
                        #? check status of this task
                        status, errors = self.sandbox.get_task_status(task_id)
                        # if status is not None: #? done
                        #     report = self.sandbox.get_report(task_id)
                        print(f'   [>] task_id = {task_id} | status = {status}')

                        if status is not None:
                            if status == 'reported': #? finished analysing
                                print(f'      [+] Reported')
                                break
                            if status == 'error': #? error
                                print(f'      [!] Error')
                                break
                        print(f'      [-] Not finished. Rest before checking')
                        time.sleep(10) #? else, rest a bit

                    #? get report folder & json report file and call __onFinishInfer__
                    if status == 'reported': #? only if `status` = reported, else maybe error or no report generated
                        #? process downloaded file
                        report_folder = os.path.join(self.module_outdir, task_id)
                        report_filepath = os.path.join(self.module_outdir, task_id, 'reports', 'report.json')
                        if not os.path.isdir(os.path.dirname(report_filepath)):
                            os.makedirs(os.path.dirname(report_filepath))

                        #? download report file from hosted cuckoo folder
                        if len(cuckoo_filesrv) > 0 and (cuckoo_filesrv[:7] == 'http://' or cuckoo_filesrv[:8] == 'https://'):
                            print('[ ] Downloading report file')
                            # subprocess.run(['curl', '-X', 'GET', f'{cuckoo_filesrv}/{task_id}/reports/report.json', '>', report_filepath])
                            os.system(f'curl -X GET {cuckoo_filesrv}/{task_id}/reports/report.json > {report_filepath}')
                        else:
                            cuckoo_outdir = os.path.join(cuckoo_reports_dir, task_id)
                            log(f'[+] Task reported. Moving from cuckoo output folder to module outdir. {cuckoo_outdir} -> {report_folder}')
                            if os.path.isdir(cuckoo_outdir):
                                shutil.move(cuckoo_outdir, self.module_outdir)

                        if not os.path.isfile(report_filepath):
                            log(f'[!] report_filepath {report_filepath} not found')

                        #? get cuckoo score. cuckoo report might be extremely huge => read only first several lines
                        score = 0
                        file = open(report_filepath, 'r')
                        # while True: #? to read all
                        if True: #? to read the first chunk only
                            chunk = file.read(4096)
                            if not chunk:
                                break
                            # print(chunk)
                            if '"score": ' in chunk:
                                score = float(chunk.split('"score": ')[1].split(',')[0]) * 10

                        #! After finish, clean up and return data in appropriate format
                        result[ohash] = [report_folder, report_filepath, str(score)]

                #! Call __onFinishInfer__ when the analysis is done. This can be called from anywhere in your code. In case you need synchronous processing
                self.__onFinishInfer__(result, note)

                #? remove the task_ids file
                # os.remove(tasks_filepath)
                os.rename(tasks_filepath, tasks_filepath+'.done')
        except Exception as e:
            log(f'[!][SilentWorker][infer] Failed with exception: {e}')
