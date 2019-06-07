import sqlite3 as lite
import json
import sys

print("Module version: " + lite.version)         # '2.6.0'
print("Sqlite version: " + lite.sqlite_version)  # '3.24.0'

_getTableNamesSQL = 'select tbl_name from sqlite_master where type = "table"'
_dbname = 'grafana.db'
if (len(sys.argv) > 1):
    _dbname  = sys.argv[1]


con = None

# Get Table names
try:
    con = lite.connect(_dbname)

    cur = con.cursor()
    cur.execute(_getTableNamesSQL)

    _result = cur.fetchone()
    while _result:
        _table_name = str(_result[0])
        # print ("DEBUG1: " + _table_name )

        _statement = "select count(*) as ROWS, '%s' as TNAME from %s" % (_table_name, _table_name)
        tbl = con.cursor()
        tbl.execute(_statement)
        _countResult = tbl.fetchone()
        while _countResult:
            (_count, _tableName) = _countResult
            if _count > 0:
                print("%8d %s" % (_count, _tableName))
            _countResult = tbl.fetchone()
        _result = cur.fetchone()

except lite.Error, e:
    print "Error {}:".format(e.args[0])
    sys.exit(1)

finally:
    if con:
        con.close()
