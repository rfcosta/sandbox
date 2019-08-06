
import boto3
import json
import time

class flipflop():

    _even = 0
    _odd  = 1
    _regions = {"us-east-1": _odd,
                "us-west-2": _even
               }

    @classmethod
    def thisMinute(cls):
        _nowUTC = int(time.time())
        _nowUTCMinute = int(_nowUTC) // 60 * 60
        return _nowUTCMinute

    @classmethod
    def getRegionName(cls):
        try:
            client = boto3.client('s3')
        except Exception as E:
            print("DEBUG>> Exception on Main getting region: " + str(E.message))
        return client.meta.region_name;

    @classmethod
    def mustRun(cls):
        _minuteParity = cls.thisMinute() // 60 % 60 % 2
        _regionParity = cls._regions.get(cls.getRegionName(), cls._odd)
        return ( _minuteParity == _regionParity )

    @classmethod
    def editedTime(cls, epoch):
        return time.strftime("%D %H:%M", time.gmtime(epoch))


if __name__ == "__main__":

    _thisMinute     = flipflop.thisMinute()
    _minute         = flipflop.editedTime(_thisMinute)
    _mustRun        = flipflop.mustRun()
    _region         = flipflop.getRegionName()
    _regionParity   = flipflop._regions[_region]

    _FMT  = "{} Minute {} Region {} Region Parity {}: Must Run = {}"
    _line = _FMT.format(_thisMinute,_minute,_region,_regionParity,_mustRun)
    print (_line)
