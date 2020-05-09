#Date: 9/23/19
#Email: brautio@juniper.net
#Department: Escalation Engineering
#Description: This module is used in order to create custom CLI commands to do chip agnostic debugging.

#This module requires these extensions:
#pip install -U git+https://github.com/vnitinv/py-junos-eznc.git@iAgent
#pip install -U git+https://github.com/vnitinv/ncclient.git@junos-sax-parser

#This module also requires PyYaml 5.1
#Or if using outdated PyYAML, copy the files load.pyc and constructor.pyc from PyYAML 5.1 and put them on the router in /opt/lib/python2.7/site-packages/yaml

#All of the YAML files used in this module must be located in the same directory that this script is run from.
#YAML files used:
# xm_li_error.yml
# xm_wi_statistics.yml
# xm_wo_statistics.yml
# xm_fo_statistics.yml
# xm_fi_statistics.yml
# xm_fi_error.yml
# xm_lo_statistics.yml
# xm_host_drop.yml
# xm_drd_error.yml
# xm_pt_statistics.yml
# ea_li_error.yml
# ea_wi_statistics.yml
# ea_wo_statistics.yml
# ea_fo_statistics.yml
# ea_fi_statistics.yml
# ea_fi_error.yml
# ea_lo_statistics.yml
# ea_host_drop.yml
# ea_drd_error.yml
# ea_pt_statistics.yml

#These YAML files can be found in https://github.com/Juniper/healthbot-rules/tree/master/juniper_official/Linecard
#The dashes in the names of these YAML files must be changed to underscores, or else the imports don't work correctly

#For the YAML files to be imported into this module, each one must have a python module of the same exact name (For example, xm_li_error.py) in the same directory as the YAML files, which has these four lines in them:

#from jnpr.junos.factory import loadyaml
#from os.path import splitext
#_YAML_ = splitext(__file__)[0] + '.yml'
#globals().update(loadyaml(_YAML_))

#This script can then be run by using an op command: op url /path/to/script or can be run with a CLI command once you add the yang package to the router

#The output in this script is formatted in XML for the YANG module.

import yamlordereddictloader
from jnpr.junos.factory.factory_loader import FactoryLoader
import yaml
from jnpr.junos import Device
import importlib
import string
import itertools
import re
import datetime

path = "/var/db/scripts/action/chip_agnostic_command_package/chip_agnostic_command/yamls"

#This method finds the eval code in the YAML files and replaces the jinja2 templating with variables that I created in this script so that the code can be executed properly. It return a list of the code that needs to be run when passed the data from the yaml file and the variables in xmItems that might need to be inserted into the code.
def findEval(d, xmItems):
    evals = []

    for key in d.keys():
        if "eval" in d[key].keys():
            for evalKey in d[key]["eval"].keys():
                if "{{ data }}" in d[key]["eval"][evalKey]:
                     evals.append(d[key]["eval"][evalKey].replace("{{ data }}", "counterDict"))
                else:
                    yamlVars = re.findall("\{ (.*?) \}", d[key]["eval"][evalKey])
                    for yamlVar in yamlVars:
                        if yamlVar in d[key]["eval"][evalKey]:
                            for k,v in xmItems.items():
                                if yamlVar == k:
                                    newStr = d[key]["eval"][evalKey].replace("{{ "+yamlVar+" }}", v)
                                    d[key]["eval"][evalKey]=newStr
                    evals.append(newStr)

    return evals

#This method returns a list of the labels of eval counters
def findEvalKeys(d):
    evalKeys = []
    for key in d.keys():
        if "eval" in d[key].keys():
            for evalKey in d[key]["eval"].keys():
                evalKeys.append({evalKey: d[key]["eval"][evalKey].replace("{{ data }}", "counterDict")})

    return evalKeys

#This method returns a dictionary containing the data needed to execute each eval statement for a YAML file
def getEvalDicts(xmItems):
    evalDicts1 = {}
    evalDicts2 = {}
    for k,v in xmItems:
        if isinstance(v, dict):
            evalDicts1.update({k: v})
        else:
            evalDicts2.update({str(k): str(v)})

    if evalDicts1:
        return evalDicts1
    else:
        return evalDicts2


#----

#This method is DEPRECATED

#Why would you need this? UDF may have different method name or do different things. Does it always get fpcs that are online? If so, why would you need to look in this file for the script? I created a separate method online_fpc() inthis module to do this.

#this function looks for the UDF in online_fpc.yml to gather the online fpc's


def findFilename():
    with open("/var/db/scripts/op/online_fpc.yml") as f:
        for x in f:
            if x.find("udf:")>=0:
                fileName = x
                fileName = fileName.replace(" ","")
                fileName = fileName.replace("udf:","")
                break

    #This formats the filename correctly and imports it as a module so you can run the run() method in the file, which gathers  the online FPCs
    fileName = " ".join(fileName.split())
    mod1 = importlib.import_module(fileName)
    fpcDicts = mod1.run() #this line is sketchy, what if no run() method?

#----

# this function collects online fpc and updates dependent sensor tables
# rpc command: get-fpc-information

def online_fpc():
    """

    """
    dev = Device()
    dev.open()
    op = dev.rpc.get_fpc_information()
    online = op.xpath('./fpc[normalize-space(state) = "Online"]/slot')
    ret = []
    for i in online:
        if i.text is not None:
            ret.append({'target': 'fpc'+i.text})
    return ret

#This function uses the get-chassis-inventory rpc command and the chip type mapping from _chips() to create a list of dictionaries containing the center chip type that is used by hardCodeOut() to import the correct YAML files

def onbox_chip_types(fpcDicts):
    dev = Device()
    dev.open()
    op = dev.rpc.get_chassis_inventory()
    types = []
    ret = []
    chips = _chips()
    for fpcDict in fpcDicts:
        for key,val in fpcDict.items():
            #The fpc must be contained within quotes in order for the xpath statement to work
            fpc = '"{}"'.format(val)
            desc = op.xpath('//chassis-module[translate(translate(normalize-space(name), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), " ","") = '+fpc+']/description')
            for i in desc:
                if i.text is not None:
                    types.append({val: i.text})

    for type in types:
        for key, val in type.items():
            #This retrieves the correct center chip type so the correct YAML files can be used to gather data
            ret.append({key: chips["ChipTypeMap"][val]})
    return ret

def get_fpc_type(fpcDicts):
    dev = Device()
    dev.open()
    op = dev.rpc.get_chassis_inventory()
    types = []
    ret = {}
    chips = _chips()
    for fpcDict in fpcDicts:
        for key,val in fpcDict.items():
            #The fpc must be contained within quotes in order for the xpath statement to work
            fpc = '"{}"'.format(val)
            desc = op.xpath('//chassis-module[translate(translate(normalize-space(name), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), " ","") = '+fpc+']/description')
            for i in desc:
                if i.text is not None:
                    types.append({val: i.text})

    for type in types:
        for key, val in type.items():
            #This retrieves the correct center chip type so the correct YAML files can be used to gather data
            ret.update({key: val})
    return ret


#returns a dictionary mapping each model to their chip type

def _chips():
    return {'ChipTypeMap': {'MPC 3D 16x 10GE': {'PFEs': 4,
                                                'center_chip': {'mq': 1},
                                                'lookup_chip': {'lu': 1}},
                            'MPC Type 1 3D': {'PFEs': 1,
                                              'center_chip': {'mq': 1},
                                              'lookup_chip': {'lu': 1}},
                            'MPC2E NG HQoS': {'PFEs': 1,
                                              'center_chip': {'xm': 1},
                                              'lookup_chip': {'xl': 1}},
                            'MPC4E 3D 32XGE': {'PFEs': 2,
                                               'center_chip': {'xm': 1},
                                               'lookup_chip': {'lu': 2}},
                            'MPCE Type 1 3D': {'PFEs': 1,
                                               'center_chip': {'mq': 1},
                                               'lookup_chip': {'lu': 1}},
                            'MS-MPC': {'PFEs': 1,
                                       'center_chip': {'xm': 1},
                                       'lookup_chip': {'lu': 1}},
                            'MPC Type 2 3D': {'PFEs': 2,
                                              'center_chip': {
                                                  'mq': 2},
                                              'lookup_chip': {
                                                  'lu': 2}},
                            'MPC Type 2 3D Q': {'PFEs': 2,
                                                'center_chip': {'mq':2},
                                                'lookup_chip': {'lu':2}},
                            'MPC Type 2 3D EQ': {'PFEs': 2,
                                                 'center_chip': {'mq': 2},
                                                 'lookup_chip': {'lu': 2}},
                            'MPCE Type 3 3D': {'PFEs': 1,
                                               'center_chip': {'xm': 1},
                                               'lookup_chip': {'lu': 4}},
                            'MPC5E 3D 24XGE+6XLGE': {'PFEs':1,
                                                  'center_chip':{'xm':2},
                                                  'lookup_chip': {'xl':1}},
                            'MPC7E 3D MRATE-12xQSFPP-XGE-XLGE-CGE': {'PFEs':2,
                                                    'center_chip':{'mqss':2},
                                                    'lookup_chip': {'luss':2}},
                            'MPC6E 3D': {'PFEs':2,
                                                    'center_chip':{'xm':4},
                                                    'lookup_chip': {'xl':2}},
                            'MPC8E 3D': {'PFEs':4,
                                                    'center_chip':{'mqss':4},
                                                    'lookup_chip': {'luss':4}},
                            'MPC9E 3D': {'PFEs':4,
                                                    'center_chip':{'mqss':4},
                                                    'lookup_chip': {'luss':4}},
                            'MPC4E 3D 32XGE': {'PFEs':2,
                                                    'center_chip':{'xm':2},
                                                    'lookup_chip': {'lu':4}},
                            'MPC4E 3D 32XGE': {'PFEs':2,
                                                    'center_chip':{'xm':2},
                                                    'lookup_chip': {'lu':4}},
                            'MPC7E 3D 40XGE': {'PFEs':2,
                                                    'center_chip':{'mqss':2},
                                                    'lookup_chip': {'luss':2}},
                            'MPC5E 3D Q 2CGE+4XGE': {'PFEs':2,
                                                    'center_chip':{'xm':2},
                                                    'lookup_chip': {'xl':1}}
                           }}


#This method creates a nested dictionary with each fpc as a key to a dictionary containing another dictionary of the YAML filenames that need to be imported and ran. These filenames are gathered from the table pointers in online_fpc.yml. The table pointer and chip type is then used to find the correct YAML files that need to be ran by looking them up in chip.yml

#Additionaly, all of the YAML files being used (and their corresponding py files) are saved in the same directory as this action script when it is ran.

def findYamls(fpcDicts):
    mega = {}
    for fpcDict in fpcDicts:
        #The FPC and files to be run that are added to mega{}
        dictOfYamls = {}
        for key,val in fpcDict.items():
            #Gets all of the table pointers that point to their corresponding YAML files in chip.yml
            with open("/var/db/scripts/op/online_fpc.yml") as f:
                for _ in range(3):
                    next(f)
                for x in f:
                    if x.find("-")>=0:
                        tablesPointer = x
                        tablesPointer = tablesPointer.replace(" ","")
                        tablesPointer = tablesPointer.replace("-","")
                        tablesPointer = " ".join(tablesPointer.split())
                        #find the YAML files that need to be ran using the table pointer and chip type
                        with open("/var/db/scripts/op/chip.yml") as c:
                            for a in c:
                                if a.find(tablesPointer)>=0:
                                    break
                            for b in c:
                                if len(b.strip())!=0:
                                    for chip in chips:
                                        if val in chip:
                                             #If the file for the corresponding tablepointer is for the correct FPC chip, add it to the dict

                                            if b.find(chip[val]['center_chip'].keys()[0]+":")>=0:
                                                dictOfYamls.update({tablesPointer: b})
                                else:
                                    break
        #adds all of the YAML files for the fpc to mega{}
        mega.update({val: dictOfYamls})
    return mega

#---

#This method is DEPRECATED

#Originally used to format the yaml filenames from the findYamls() method so that they can be run as modules dynamically, but that is impossible to do. To my knowledge, Yamls cannot be run dynamically like regular python modules.

def parseYamlNames(mega):
    for key in mega:
        print key
        for key, val in mega[key].items():
            val = val.replace(" ","")
            val = " ".join(val.split())
            val = val.replace("xm:","") # fix this, more general

            print val

#---

#This method is used to create a nested list containing the data for each YAML file that is then returned and added to a dictionary with the data under the its table-name as the keyword. Only Chip agnostic data is needed, so only counters with "cchip" in its label is collected.

def parseOut(stats, stream, counterDict):
    i = 0
    toPrint = []
    d = yaml.safe_load(stream)
    for item in stats:
        rows = []
        #checks if the second element in the tuple of item is a dict. It must be handled differently if it is.
        if isinstance(item[1],dict):
            #if item[0] is a tuple rather than a single value, iterate through the tuple to print
            if isinstance(item[0], tuple):
                #print(stats.keys())
                #convert tuple to list to make formatting and printing look nicer
                tList = list(item[0])
                # iterate through the list and print
            #if item[0] is not a tuple, just print the value
            else :
                #if not isinstance(item[0], int):
                if "cchip" in str(item[0]):
                    #rows.append("1 "+str(item[0]))
                    appString = item[0]
                    #rows.append("<everything>{}</everything>".format(str(item[0]))
                else:
                    for kval, vval in item[1].items():
                        if "cchip" in str(kval):
                            kvList = []
                            kvList.append("plane_"+str(i))
                            #kvList.append(str(item[0]))
                            toPrint.append(kvList)
                            kvList = []
                            kvList.append("    "+str(kval)+":")
                            kvList.append(str(vval))
                            toPrint.append(kvList)
                            i=i+1
            #This loop iterates through the dict in item[1].items(), which contains the a dict of the keys and values from the Table
            for key,val in item[1].items():
                #This checks each element in item[1] for nested dicts, they must be iterated through differently in order to format the data correctly
                if isinstance(item[1][key], dict):
                    #print the key for each nested dict
                    print(str(key))
                    #iterate and print each element of the nested dict's keys and corresponding values
                    for key,val in item[1][key].items():
                        print(str(key)+": "+str(val))
                #If there aren't nested dicts, iterate over the dict regularly, printing the keys and corresponding values
                else:
                    if "cchip" in str(item[0]):
                        numValPair = []
                        numValPair.append(appString+" "+str(key)+":")
                        numValPair.append(str(val))
                        toPrint.append(numValPair)
                        #rows.append(str(key)+": "+str(val))
        #if item doesn't contain a dict in item[1] of values, it contains just a singular key-value pair, and can simply be printed this way
        else:
            evKeyList = findEvalKeys(d)
            if evKeyList:
                if item[0] not in str(evKeyList):
                    if "cchip" in str(item[0]):
                        rows.append(str(item[0])+":")
                        rows.append(str(item[1]))

            else:
                if "cchip" in str(item[0]):
                    rows.append(str(item[0])+":")
                    rows.append(str(item[1]))

        if rows:
            toPrint.append(rows)

    evals = findEval(d, counterDict)
    evalKeys = findEvalKeys(d)
    for code in evals:
        evalRow = []
        for x in evalKeys:
            for k, v in x.items():
                if v in code:
                    evalToPrint=k
        exec "num="+code in globals(), locals()
        evalRow.append(str(evalToPrint)+":")
        evalRow.append(str(num))
        toPrint.append(evalRow)

    return toPrint


#This method uses the list of data containing online fpc's and their center chip types in order to import the correct YAML files and their tables, and then uses the data from the tables to print the retrieved data for each center chip.

def hardCodeOut(fpcList, fpcType):
    for fpc in fpcList:
        print("<fpc>")
        for key, val in fpc.items():
            #print key
            #print val
            #This retrieves the chip type needed to run the correct YAML files, which is tested by the if-statements inside the for-loop.
            for chip, num in val["center_chip"].items():

                if chip == "xm":
                    #The tables had to be imported conditionally because although there are separate YAML files and tables for each chip type, the tables have the same exact name, so the tables cannot be imported all at the same time

                    from chip_agnostic_command_package.chip_agnostic_command.yamls.xm_li_error import CChipLiInterruptStatsTable
                    from chip_agnostic_command_package.chip_agnostic_command.yamls.xm_wi_statistics import CChipWiStatsTable
                    from chip_agnostic_command_package.chip_agnostic_command.yamls.xm_wo_statistics import CChipWoStatsTable
                    from chip_agnostic_command_package.chip_agnostic_command.yamls.xm_fo_statistics import CChipFOStatsTable
                    from chip_agnostic_command_package.chip_agnostic_command.yamls.xm_fi_statistics import CChipFiStatsTable
                    from chip_agnostic_command_package.chip_agnostic_command.yamls.xm_fi_error import CChipFiErrTable
                    from chip_agnostic_command_package.chip_agnostic_command.yamls.xm_lo_statistics import CChipLoStatsTable
                    from chip_agnostic_command_package.chip_agnostic_command.yamls.xm_host_drop import CChipHostDropTable
                    from chip_agnostic_command_package.chip_agnostic_command.yamls.xm_drd_error import CChipDRDErrTable
                    from chip_agnostic_command_package.chip_agnostic_command.yamls.xm_pt_statistics import CChipPTStatTable

                    with Device() as dev:

                        for i in range(num):
                            print("<fpc-num>{}</fpc-num>".format(key+" "+"chip instance "+str(i)))
                            for fpcKey, typeVal in fpcType.items():
                                if fpcKey == key:
                                    printFpcType = typeVal
                            print("<fpc-type>fpc type {}</fpc-type>".format(str(printFpcType)))
                            print("<chip-instance>")

                            #Since there are multiple instances for some center chips and multiple fpcs online, the fpc name and instance must be passed as variables to each YAML file by giving arguments to the get() method
                            dataPrint = {}
                            xm = CChipLiInterruptStatsTable(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"/xm_li_error.yml", 'r') as stream:
                                counterDict = getEvalDicts(xm.items())
                                dataList = parseOut(xm, stream, counterDict)
                                dataPrint.update({xm: dataList})

                            xm = CChipWiStatsTable(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"/xm_wi_statistics.yml", 'r') as stream:
                                counterDict = getEvalDicts(xm.items())
                                dataList = parseOut(xm, stream, counterDict)
                                dataPrint.update({xm: dataList})

                            xm = CChipWoStatsTable(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"/xm_wo_statistics.yml", 'r') as stream:
                                counterDict = getEvalDicts(xm.items())
                                dataList = parseOut(xm, stream, counterDict)
                                dataPrint.update({xm: dataList})

                            xm = CChipFOStatsTable(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"/xm_fo_statistics.yml", 'r') as stream:
                                counterDict = getEvalDicts(xm.items())
                                dataList = parseOut(xm, stream, counterDict)
                                dataPrint.update({xm: dataList})

                            xm = CChipFiStatsTable(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"/xm_fi_statistics.yml", 'r') as stream:
                                counterDict = getEvalDicts(xm.items())
                                dataList = parseOut(xm, stream, counterDict)
                                dataPrint.update({xm: dataList})

                            xm = CChipFiErrTable(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"/xm_fi_error.yml", 'r') as stream:
                                counterDict = getEvalDicts(xm.items())
                                dataList = parseOut(xm, stream, counterDict)
                                dataPrint.update({xm: dataList})

                            xm = CChipLoStatsTable(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"/xm_lo_statistics.yml", 'r') as stream:
                                counterDict = getEvalDicts(xm.items())
                                dataList = parseOut(xm, stream, counterDict)
                                dataPrint.update({xm: dataList})

                            xm = CChipHostDropTable(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"/xm_host_drop.yml", 'r') as stream:
                                counterDict = getEvalDicts(xm.items())
                                dataList = parseOut(xm, stream, counterDict)
                                dataPrint.update({xm: dataList})

                            xm = CChipDRDErrTable(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"/xm_drd_error.yml", 'r') as stream:
                                counterDict = getEvalDicts(xm.items())
                                dataList = parseOut(xm, stream, counterDict)
                                dataPrint.update({xm: dataList})

                            xm = CChipPTStatTable(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"/xm_pt_statistics.yml", 'r') as stream:
                                counterDict = getEvalDicts(xm.items())
                                dataList = parseOut(xm, stream, counterDict)
                                dataPrint.update({xm: dataList})

                            col_width = 0
                            for k,v in dataPrint.items():
                                if v:
                                    if col_width == 0 or col_width < (max(len(word) for row in v for word in row) + 2):
                                        col_width = max(len(word) for row in v for word in row) + 2

                            print("<cchip>")
                            print("<outputs>")
                            for k,v in dataPrint.items():

                                strXM = str(k)
                                sep = ":"
                                rest = strXM.split(sep, 1)[0]
                                print("<cchip-table>")
                                print("<table-name>{}</table-name>".format(rest))
                                print("<cchip-table-data>")
                                for row in v:
                                    print("<counter-list>")
                                    print("<counter>{}</counter>".format("".join(word.ljust(col_width) for word in row)))
                                    print("<nested-counter></nested-counter>")
                                    print("</counter-list>")
                                print("</cchip-table-data>")
                                print("</cchip-table>")

                            print("</outputs>")
                            print("</cchip>")

                            print("</chip-instance>")

                if chip == "mqss":

                    from chip_agnostic_command_package.chip_agnostic_command.yamls.ea_li_error import CChipLiInterruptStatsTable
                    from chip_agnostic_command_package.chip_agnostic_command.yamls.ea_wi_statistics import CChipWiStatsTable
                    from chip_agnostic_command_package.chip_agnostic_command.yamls.ea_wo_statistics import CChipWoStatsTable
                    from chip_agnostic_command_package.chip_agnostic_command.yamls.ea_fo_statistics import CChipFOStatsTable
                    from chip_agnostic_command_package.chip_agnostic_command.yamls.ea_fi_statistics import CChipFiStatsTable
                    from chip_agnostic_command_package.chip_agnostic_command.yamls.ea_fi_error import CChipFiErrTable
                    from chip_agnostic_command_package.chip_agnostic_command.yamls.ea_lo_statistics import CChipLoStatsTable
                    from chip_agnostic_command_package.chip_agnostic_command.yamls.ea_host_drop import CChipHostDropTable
                    from chip_agnostic_command_package.chip_agnostic_command.yamls.ea_drd_error import CChipDRDErrTable
                    from chip_agnostic_command_package.chip_agnostic_command.yamls.ea_pt_statistics import CChipPTStatTable

                    with Device() as dev:
                        for i in range(num):
                            dataPrint = {}
                            print("<fpc-num>{}</fpc-num>".format(key+" "+"chip instance "+str(i)))
                            for fpcKey, typeVal in fpcType.items():
                                if fpcKey == key:
                                    printFpcType = typeVal
                            print("<fpc-type>fpc type {}</fpc-type>".format(str(printFpcType)))
                            print("<chip-instance>")

                            ea = CChipLiInterruptStatsTable(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"/ea_li_error.yml", 'r') as stream:
                                counterDict = getEvalDicts(ea.items())
                                dataList = parseOut(ea, stream, counterDict)
                                dataPrint.update({ea: dataList})

                            ea = CChipWiStatsTable(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"/ea_wi_statistics.yml", 'r') as stream:
                                counterDict = getEvalDicts(ea.items())
                                dataList = parseOut(ea, stream, counterDict)
                                dataPrint.update({ea: dataList})

                            ea = CChipWoStatsTable(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"/ea_wo_statistics.yml", 'r') as stream:
                                counterDict = getEvalDicts(ea.items())
                                dataList = parseOut(ea, stream, counterDict)
                                dataPrint.update({ea: dataList})

                            ea = CChipFOStatsTable(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"/ea_fo_statistics.yml", 'r') as stream:
                                counterDict = getEvalDicts(ea.items())
                                dataList = parseOut(ea, stream, counterDict)
                                dataPrint.update({ea: dataList})

                            ea = CChipFiStatsTable(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"/ea_fi_statistics.yml", 'r') as stream:
                                counterDict = getEvalDicts(ea.items())
                                dataList = parseOut(ea, stream, counterDict)
                                dataPrint.update({ea: dataList})

                            ea = CChipFiErrTable(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"/ea_fi_error.yml", 'r') as stream:
                                counterDict = getEvalDicts(ea.items())
                                dataList = parseOut(ea, stream, counterDict)
                                dataPrint.update({ea: dataList})

                            ea = CChipLoStatsTable(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"/ea_lo_statistics.yml", 'r') as stream:
                                counterDict = getEvalDicts(ea.items())
                                dataList = parseOut(ea, stream, counterDict)
                                dataPrint.update({ea: dataList})

                            ea = CChipHostDropTable(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"/ea_host_drop.yml", 'r') as stream:
                                counterDict = getEvalDicts(ea.items())
                                dataList = parseOut(ea, stream, counterDict)
                                dataPrint.update({ea: dataList})

                            ea = CChipDRDErrTable(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"/ea_drd_error.yml", 'r') as stream:
                                counterDict = getEvalDicts(ea.items())
                                dataList = parseOut(ea, stream, counterDict)
                                dataPrint.update({ea: dataList})

                            ea = CChipPTStatTable(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"/ea_pt_statistics.yml", 'r') as stream:
                                counterDict = getEvalDicts(ea.items())
                                dataList = parseOut(ea, stream, counterDict)
                                dataPrint.update({ea: dataList})

                            col_width = 0
                            for k,v in dataPrint.items():
                                if v:
                                    if col_width == 0 or col_width < (max(len(word) for row in v for word in row) + 2):
                                        col_width = max(len(word) for row in v for word in row) + 2

                            print("<cchip>")
                            print("<outputs>")
                            i = 0
                            for k,v in dataPrint.items():

                                strXM = str(k)
                                sep = ":"
                                rest = strXM.split(sep, 1)[0]
                                print("<cchip-table>")
                                print("<table-name>{}</table-name>".format(rest))
                                print("<cchip-table-data>")
                                for row in v:
                                    i = i+1
                                    #if "plane" not in str(row) and "cchip-fo-total-packets-sent" not in str(row):
                                    print("<counter-list>")
                                    print("<counter>{}</counter>".format("".join(word.ljust(col_width) for word in row)))
                                    print("<nested-counter></nested-counter>")
                                    print("</counter-list>")

                                    #else:
                                        #if "plane" in str(row):
                                        #    print("<counter-list>")
                                            #print("<counter>{}</counter>".format("".join(word.ljust(col_width) for word in row)))
                                        #    print("<counter>{}".format("".join(word.ljust(col_width) for word in row))+str(i)+"</counter>")

                                        #if "cchip-fo-total-packets-sent" in str(row):
                                            #print("<nested-counter>{}</nested-counter>".format("".join(word.ljust(col_width) for word in row)))
                                        #    print("<nested-counter>{}".format("".join(word.ljust(col_width) for word in row))+str(i)+"</nested-counter>")
                                        #    print("</counter-list>")

                                print("</cchip-table-data>")
                                print("</cchip-table>")

                            print("</outputs>")
                            print("</cchip>")

                            print("</chip-instance>")

        print("</fpc>")

print("<all-data>")

now = datetime.datetime.now()
print("<date>time now is {}</date>".format(str(now)))

#Retrieves the online FPCs
fpcDicts = online_fpc()

#Uses the online fpcs to get the center chip type for each fpc
chips = onbox_chip_types(fpcDicts)

fpcType = get_fpc_type(fpcDicts)

#print chips

#retrieves and prints data for each fpc center chip
hardCodeOut(chips, fpcType)
print("</all-data>")
