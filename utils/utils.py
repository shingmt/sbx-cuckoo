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

import logging
def log(msg, log_type='info'):
    logging.basicConfig(level=logging.DEBUG, filename='worker.log', filemode='a+',
                        format="%(asctime)-15s %(levelname)-8s %(message)s")
    if log_type == 'info':
        logging.info(msg)
    elif log_type == 'warning':
        logging.warning(msg)
    elif log_type == 'error':
        logging.error(msg)

    print(msg)