# Copyright 2018 Google Inc. All rights reserved.
# Use of this source code is governed by the Apache 2.0
# license that can be found in the LICENSE file.

import datetime
import logging
import os

from flask import has_request_context
from flask import request
from google.cloud import logging as gcplogging
from google.cloud.logging import Resource

from flask_gcp_log_groups.background_thread import BackgroundThreadTransport

_GLOBAL_RESOURCE = Resource(type='global', labels={})

logger = logging.getLogger(__name__)
client = gcplogging.Client()

class GCPHandler(logging.Handler):
    
    def __init__(self, child_log_name='application',
                 trace_header_name=None, labels=None, resource=None):
        logging.Handler.__init__(self)
        self.labels=labels
        self.trace_header_name = trace_header_name
        if resource is None:
            resource = _GLOBAL_RESOURCE
        else:
            resource = Resource(type=resource['type'], labels=resource['labels'])
        self.resource = resource
        self.transport_child = BackgroundThreadTransport(client, child_log_name)           
        self.mLogLevels = []
            
    def emit(self, record):
        if not has_request_context():
            return
        msg = self.format(record)

        self.mLogLevels.append(record.levelno)
        trace_path = None
        span_id = None
        if self.trace_header_name in request.headers.keys():
            # trace can be formatted as "X-Cloud-Trace-Context: TRACE_ID/SPAN_ID;o=TRACE_TRUE"
            raw_trace = request.headers.get(self.trace_header_name).split('/')
            trace_id = raw_trace[0]
            trace_path = f"projects/{os.getenv('GOOGLE_CLOUD_PROJECT')}/traces/{trace_id}"
            if len(raw_trace) > 1:
                span_id = raw_trace[1].split(';')[0]

        self.transport_child.send(msg,
                                  timestamp=datetime.datetime.utcnow(),
                                  severity=record.levelname,
                                  resource=self.resource,
                                  labels=self.labels,
                                  trace=trace_path,
                                  span_id=span_id)
