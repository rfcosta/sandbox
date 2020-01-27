import datetime
import time
import boto3
import os
import base64
import re
import argparse
import json

# import urlparse
try:
    import urllib.parse as urlparse           # Python 3
except ImportError:
    import urlparse                           # Python 2

try:
    import http.client as  httplib            # Python 3
except ImportError:
    import httplib                            # Python 2

import logging
from logging  import getLogger, DEBUG, INFO, WARNING, ERROR

from botocore.config import Config

LOG_LEVEL_DEFAULT = DEBUG
NAME_DEFAULT = __name__

class AwsUtil(object):

    def __init__(self, NAME=NAME_DEFAULT, LOG_LEVEL=LOG_LEVEL_DEFAULT):

        _logger = getLogger(NAME)

        if _logger.handlers.__len__() == 0:
            _logger.propagate = 0
            _formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s %(funcName)s:%(lineno)d: %(message)s')
            _console_handler = logging.StreamHandler()
            _console_handler.setFormatter(_formatter)
            _logger.addHandler(_console_handler)

        self.loggger = _logger
        self.loggger.setLevel(LOG_LEVEL)

        pass

    def validate_datetime(self,timestamp):
        _XNUMBER = re.compile(r'^\d+$')
        # print(" %s type is %s" % (input, type(input).__name__))
        if type(timestamp).__name__ == 'datetime':
            return timestamp

        if _XNUMBER.match(str(timestamp)):
            nowEpoch = (int(time.time()) // 60) * 60
            backEpoch = nowEpoch - (int(str(timestamp)) * 60)
            backMinute = datetime.datetime.fromtimestamp(backEpoch)
            return backMinute

        if type(timestamp).__name__ == 'str':
            try:
                _input = ' '.join(timestamp.split('T'))
                return datetime.datetime.strptime(_input, '%Y-%m-%d %H:%M')
            except ValueError:
                msg = 'Not a valid date: %s' % timestamp
                raise argparse.ArgumentTypeError(msg)

    def epoch2date(self, epoch):
        return datetime.datetime.fromtimestamp(float(epoch))

    def epochMinute(self, epoch):
        return int(epoch) // 60 * 60

    def conceal(self, pwd):
        return pwd[0].ljust(pwd.__len__(), '*') + pwd[-1]

    def resetProxy(self):
        if os.environ.get("http_proxy"):
            self.loggger.debug("HTTP  Proxy cleared from " + os.environ["http_proxy"])
            del os.environ["http_proxy"]
        if os.environ.get("https_proxy"):
            self.loggger.debug("HTTPS Proxy cleared from " + os.environ["https_proxy"])
            del os.environ["https_proxy"]


    def setProxy(self, proxy=''):
        if proxy:
            os.environ["http_proxy"] = proxy
            os.environ["https_proxy"] = proxy

            (_proto, _proxy) = proxy.split('://')

            self.loggger.debug("Proxy " + proxy)
            self.loggger.debug("proto " + _proto)
            self.loggger.debug("site  " + _proxy)
        else:
            self.resetProxy()


    def getPasswords(self, hashes, proxy=''):
        config_dict = {'connect_timeout': 10, 'read_timeout': 10}

        self.setProxy(proxy)

        _config = Config(**config_dict)
        self.loggger.debug("CONFIG " + str(_config))


        KMS = boto3.client('kms')
        passwords = []

        for hashItem in hashes:
            decodedHash = base64.decodestring(hashItem)
            response = KMS.decrypt(CiphertextBlob=decodedHash)

            password = response['Plaintext'].decode('utf8')
            passwords.append(password)

        self.resetProxy()

        return passwords


    def shpEnqueueSQS(self, sqsUrlStr, shpAPIjson, proxy='', replication=False):
        config_dict = {'connect_timeout': 10, 'read_timeout': 10}

        self.setProxy(proxy)

        _config = Config(**config_dict)

        self.loggger.debug("CONFIG " + str(_config))


        SQS = boto3.client('sqs', config=_config)

        sqsBody = json.dumps(shpAPIjson)

        _replication = 'true' if replication else 'false'

        self.loggger.debug("QueueUrl:    " +  sqsUrlStr)
        self.loggger.debug("MessageBody: " + json.dumps(shpAPIjson, indent=4))
        self.loggger.debug("Replication: " + _replication)

        sqsResponse = SQS.send_message(
            QueueUrl=sqsUrlStr,
            MessageBody=sqsBody,
            MessageAttributes={
                'Replication': {
                    'StringValue': _replication,
                    'DataType': 'String'
                }
            }
        )

        self.resetProxy()

        sqsMD5OfMessageBody        = sqsResponse['MD5OfMessageBody']
        sqsMD5OfMessageAttributes  = sqsResponse['MD5OfMessageAttributes']
        sqsMessageId               = sqsResponse['MessageId']
        sqsResponseMetadata        = sqsResponse['ResponseMetadata']
        sqsRetryAttempts           = sqsResponseMetadata['RetryAttempts']
        sqsHTTPStatusCode          = sqsResponseMetadata['HTTPStatusCode']

        self.loggger.debug('Resp: ' + json.dumps(sqsResponse, indent=4))

        if sqsHTTPStatusCode == 200:
            return True

        return False


    def send_shp_request(self, sqs_url, shp_api_request, proxy='', replication=False):
        _STATUS = "OK"
        if shp_api_request['metrics'].__len__() > 0:
            if not self.shpEnqueueSQS(sqs_url, shp_api_request, proxy, replication):
                _STATUS = 'QUEUE ERROR'
            else:
                _STATUS = 'SUCCESS'
        else:
            _STATUS = 'DATA ERROR'

        return _STATUS


    def send_response(self, request, response, status=None, reason=None):
        # Send our response to the pre-signed URL supplied by CloudFormation
        # If no ResponseURL is found in the request, there is no place to send a
        # response. This may be the case if the supplied event was for testing.

        if status is not None:
            response['Status'] = status

        if reason is not None:
            response['Reason'] = reason

        if 'ResponseURL' in request and request['ResponseURL']:
            url = urlparse.urlparse(request['ResponseURL'])
            body = json.dumps(response)
            https = httplib.HTTPSConnection(url.hostname)
            https.request('PUT', url.path+'?'+url.query, body)

        return response

    def loadS3File(self, s3BucketName, s3FileName, proxy='', s3Format='utf8'):
        config_dict = {'connect_timeout': 10, 'read_timeout': 10}

        self.setProxy(proxy)

        _config = Config(**config_dict)
        self.loggger.log(DEBUG,"CONFIG " + str(_config))

        s3 = boto3.resource('s3')
        content_object = s3.Object(s3BucketName, s3FileName)
        self.loggger.debug("content_object: " + str(content_object))
        json_content = {"result": {}}
        try:
            file_content = content_object.get()['Body'].read().decode(s3Format)
            json_content = json.loads(file_content)
        except Exception as e:
            self.loggger.error("S3 File ERROR: {}".format(str(e)))
            # self.loggger.error("S3 File not found: {} {}".format(s3BucketName, s3FileName))
            raise e

        self.resetProxy()


        return json_content



    def invokeLambda(self, functionName='', invokationType='DryRun', payload={}, proxy='', timeout=10):

        # Request
        # Syntax
        #
        # response = client.invoke(
        #     FunctionName='string',
        #     InvocationType='Event' | 'RequestResponse' | 'DryRun',
        #     LogType='None' | 'Tail',
        #     ClientContext='string',
        #     Payload=b'bytes' | file,
        #     Qualifier='string'
        # )


        statusCodeOKPerInvokationType = dict(
            DryRun=204,
            Event=202,
            RequestResponse=200
        )

        payloadString = json.dumps(payload)
        self.loggger.debug("invokationType: {}, FunctionName: {}, Payload: {}, timeout: {}".format(invokationType, functionName, payloadString, timeout))

        config_dict = {'connect_timeout': timeout, 'read_timeout': timeout}
        _config = Config(**config_dict)

        LAMBDA = boto3.client('lambda', config=_config)


        self.setProxy(proxy)

        try:
            invokeResponse = LAMBDA.invoke(
                FunctionName =functionName,
                InvocationType =invokationType,
                Payload = payloadString,
                LogType = 'Tail',
                #clientContext = "",
                Qualifier = '',
            )
        except Exception as E:
            self.loggger.error("Exception {} on invokeLambda".format(str(E)))
            #traceback.print_exc()

        self.resetProxy()

        _ExecutedVersion  = invokeResponse.get('ExecutedVersion', '')
        _Payload          = invokeResponse.get('PayLoad', '?')
        _LogResult        = invokeResponse.get('LogResult', '')
        _FunctionError    = invokeResponse.get('FunctionError', '')
        _StatusCode       = invokeResponse.get('StatusCode', statusCodeOKPerInvokationType['DryRun'])

        self.loggger.debug('Resp: ' + json.dumps(invokeResponse, indent=4))

        if _StatusCode == statusCodeOKPerInvokationType[invokationType]:
            return True

        return False






