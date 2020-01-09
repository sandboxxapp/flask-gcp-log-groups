# Copyright 2018 Google Inc. All rights reserved.
# Use of this source code is governed by the Apache 2.0
# license that can be found in the LICENSE file.

import datetime
import logging
import os

from flask import has_request_context
from flask import request
from google.cloud import logging as gcplogging
from google.cloud.logging.resource import Resource

from flask_gcp_log_groups.background_thread import BackgroundThreadTransport

_GLOBAL_RESOURCE = Resource(type='global', labels={})

logger = logging.getLogger(__name__)
client = gcplogging.Client()

class GCPHandler(logging.Handler):
    
    def __init__(self, app, childLogName='application',
                 traceHeaderName=None, labels=None, resource=None):
        logging.Handler.__init__(self)
        self.app = app
        self.labels=labels
        self.traceHeaderName = traceHeaderName
        if (resource is None):
            resource = _GLOBAL_RESOURCE
        else:
            resource = Resource(type=resource['type'], labels=resource['labels'])
        self.resource = resource
        self.transport_child = BackgroundThreadTransport(client, childLogName)           
        self.mLogLevels = []
            
    def emit(self, record):
        if not has_request_context():
            return
        msg = self.format(record)
        SEVERITY = record.levelname

        self.mLogLevels.append(record.levelno)
        TRACE = None
        SPAN = None
        if (self.traceHeaderName in request.headers.keys()):
          # trace can be formatted as "X-Cloud-Trace-Context: TRACE_ID/SPAN_ID;o=TRACE_TRUE"
          rawTrace = request.headers.get(self.traceHeaderName).split('/')
          trace_id = rawTrace[0]
          TRACE = "projects/{project_id}/traces/{trace_id}".format(
              project_id=os.getenv('GOOGLE_CLOUD_PROJECT'),
              trace_id=trace_id)
          if (len(rawTrace) > 1):
              SPAN = rawTrace[1].split(';')[0]

        self.transport_child.send(
                msg,
                timestamp=datetime.datetime.utcnow(),                
                severity=SEVERITY,
                resource=self.resource,
                labels=self.labels,
                trace=TRACE,
                span_id=SPAN)            
