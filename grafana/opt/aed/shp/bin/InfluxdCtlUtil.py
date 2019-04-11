#!/usr/bin/python
import re
import subprocess

class InfluxdCtlUtil:
    def __init__(self, *args):
        if len(args) > 0:
            self.debug = args[0]
            print ("DEBUG: debug set to True")

        self.mIP = re.compile('(\d+[.]\d+[.]\d+[.]\d+)[:](\d+)')
        self.m3col = re.compile('^\s*(\S+)\s+(\S+)\s+(\S+)\s*')
        self.m2col = re.compile('^\s*(\S+)\s+(\S+)\s*')
        self.m1col = re.compile('^\s*(\S+)\s*')
        self.mnumb = re.compile('(\d+)')
        self.response = ""


    def do_command(self, command):
        self.results = []
        if  self.emul:
            self.emulFile = command
            myfile = open(self.emulFile)
            self.response = myfile.read()
            if self.debug:
                print("DEBUG: show emulated from file " + self.emulFile)
        else:
            self.response = subprocess.check_output(command).decode('utf-8')

        self.responses = self.response.splitlines()
        return self.responses

    def getResponses(self):
        return self.responses

    def getResponse(self):
        return self.response

    def show(self, *args):
        command = ['influxd-ctl', 'show']
        if len(args) > 0:
            command = args[0]
            self.emul = True

        responses = self.do_command(command)

        data_nodes = []
        meta_nodes = []



        for line in responses:

            response = self.m1col.match(line)
            if not response:
                continue
            ID = response.group(1)

            if ID == "ID" or ID == "TCP" or ID[0] == "=" or ID == "":
                continue

            if ID == "Data":
                data_nodes = []
                is_data = True
                continue
            elif ID == "Meta":
                meta_nodes = []
                is_data = False
                continue

            if is_data:
                data_version = ""
                TCP_Address = ""
                TCP_Port = ""
                response = self.m2col.match(line)
                if response:
                    IP_PORT = response.group(2)
                    IP_result = self.mIP.match(IP_PORT)
                    if IP_result:
                        TCP_Address = IP_result.group(1)
                        TCP_Port = IP_result.group(2)
                    response = self.m3col.match(line)
                    if response:
                        data_version = response.group(3)
                data_node_data = {"id": str(ID), "ip": str(TCP_Address), "port": str(TCP_Port),
                                  "version": str(data_version)}
                data_nodes.append(data_node_data)
            else:
                TCP_Address = ""
                TCP_Port = ""
                meta_version = ""
                IP_result = self.mIP.match(ID)
                if IP_result:
                    TCP_Address = IP_result.group(1)
                    TCP_Port = IP_result.group(2)
                response = self.m2col.match(line)
                if response:
                    meta_version = response.group(2)
                meta_node_data = {"ip": str(TCP_Address), "port": str(TCP_Port), "version": str(meta_version)}
                meta_nodes.append(meta_node_data)

        cluster_node_data = {"data": data_nodes, "meta": meta_nodes}
        return cluster_node_data

