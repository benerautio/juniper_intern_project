#!/usr/bin/env python
import sys
if "/var/db/scripts/action" not in sys.path:
    sys.path.append("/var/db/scripts/action")
import yamlordereddictloader
from jnpr.junos.factory.factory_loader import FactoryLoader
import yaml
from jnpr.junos import Device
import importlib
import re
import datetime
from lxml import etree


from chip_agnostic_command_package.chip_agnostic_command.yamls.xm_li_error import CChipLiInterruptStatsTable as xm_li
from chip_agnostic_command_package.chip_agnostic_command.yamls.xm_wi_statistics import CChipWiStatsTable as xm_wi
from chip_agnostic_command_package.chip_agnostic_command.yamls.xm_wo_statistics import CChipWoStatsTable as xm_wo
from chip_agnostic_command_package.chip_agnostic_command.yamls.xm_fo_statistics import CChipFOStatsTable as xm_fo
from chip_agnostic_command_package.chip_agnostic_command.yamls.xm_fi_statistics import CChipFiStatsTable as xm_fi_stats
from chip_agnostic_command_package.chip_agnostic_command.yamls.xm_fi_error import CChipFiErrTable as xm_fi_err
from chip_agnostic_command_package.chip_agnostic_command.yamls.xm_lo_statistics import CChipLoStatsTable as xm_lo
from chip_agnostic_command_package.chip_agnostic_command.yamls.xm_host_drop import CChipHostDropTable as xm_host
from chip_agnostic_command_package.chip_agnostic_command.yamls.xm_drd_error import CChipDRDErrTable as xm_drd
from chip_agnostic_command_package.chip_agnostic_command.yamls.xm_pt_statistics import CChipPTStatTable as xm_pt

from chip_agnostic_command_package.chip_agnostic_command.yamls.ea_li_error import CChipLiInterruptStatsTable as ea_li
from chip_agnostic_command_package.chip_agnostic_command.yamls.ea_wi_statistics import CChipWiStatsTable as ea_wi
from chip_agnostic_command_package.chip_agnostic_command.yamls.ea_wo_statistics import CChipWoStatsTable as ea_wo
from chip_agnostic_command_package.chip_agnostic_command.yamls.ea_fo_statistics import CChipFOStatsTable as ea_fo
from chip_agnostic_command_package.chip_agnostic_command.yamls.ea_fi_statistics import CChipFiStatsTable as ea_fi_stats
from chip_agnostic_command_package.chip_agnostic_command.yamls.ea_fi_error import CChipFiErrTable as ea_fi_err
from chip_agnostic_command_package.chip_agnostic_command.yamls.ea_lo_statistics import CChipLoStatsTable as ea_lo
from chip_agnostic_command_package.chip_agnostic_command.yamls.ea_host_drop import CChipHostDropTable as ea_host
from chip_agnostic_command_package.chip_agnostic_command.yamls.ea_drd_error import CChipDRDErrTable as ea_drd
from chip_agnostic_command_package.chip_agnostic_command.yamls.ea_pt_statistics import CChipPTStatTable as ea_pt

path = "/var/db/scripts/action/chip_agnostic_command_package/chip_agnostic_command/yamls/"

#This method finds the eval code in the YAML files and replaces the jinja2 templating with variables that I created in this script so that the code can be executed properly. It return a list of the code that needs to be run when passed the data from the yaml file and the variables in xmItems that might need to be inserted into the code.
def findEval(d, xmItems):
    evals = []
    for key in d.keys():
        if "eval" in d[key].keys():
            for evalKey in d[key]["eval"].keys():
                if "{{ data }}" in d[key]["eval"][evalKey]:
                     evals.append(d[key]["eval"][evalKey].replace("{{ data }}", "eval_counters"))
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
                evalKeys.append({evalKey: d[key]["eval"][evalKey].replace("{{ data }}", "eval_counters")})

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

def parseOut(stats, stream, eval_counters):
    table_counters = {}
    d = yaml.safe_load(stream)
    for item in stats:
        #checks if the second element in the tuple of item is a dict. It must be handled differently if it is.
        if isinstance(item[1],dict):
            if "cchip" in str(item[0]):
                appstring = item[0]
            else:
                for ea_fo_key, ea_fo_val in item[1].items():
                    if "cchip" in str(ea_fo_key):
                        plane_num = int(item[0])
                        #table_counters.update({plane: plane_num})
                        ea_fo_total_packets_sent_label = str(ea_fo_key)+":"
                        ea_fo_total_packets_sent_num = str(ea_fo_val)
                        #table_counters.update({ea_fo_total_packets_sent_label:ea_fo_total_packets_sent_num})
                        table_counters.update({plane_num:{ea_fo_total_packets_sent_label:ea_fo_total_packets_sent_num}})
            #This loop iterates through the dict in item[1].items(), which contains the a dict of the keys and values from the Table
            for key,val in item[1].items():
                if "cchip" in str(item[0]):
                    appstring_counter_label = appstring+" "+str(key)+":"
                    appstring_counter_num = str(val)
                    table_counters.update({appstring_counter_label: appstring_counter_num})
        #if item doesn't contain a dict in item[1] of values, it contains just a singular key-value pair, and can simply be printed this way
        else:
            eval_key_list = findEvalKeys(d)
            if eval_key_list:
                if item[0] not in str(eval_key_list):
                    if "cchip" in str(item[0]):
                        special_eval_case_label = str(item[0])+":"
                        special_eval_case_num = str(item[1])
                        table_counters.update({special_eval_case_label:special_eval_case_num })
            else:
                if "cchip" in str(item[0]):
                    simple_case_counter_label = str(item[0])+":"
                    simple_case_counter_num = str(item[1])
                    table_counters.update({simple_case_counter_label:simple_case_counter_num})

    evals = findEval(d, eval_counters)
    evalKeys = findEvalKeys(d)
    for code in evals:
        for x in evalKeys:
            for k, v in x.items():
                if v in code:
                    eval_label=k
        exec "num="+code in globals(), locals()
        eval_label = str(eval_label)+":"
        eval_result = str(num)
        table_counters.update({eval_label:eval_result})

    return table_counters

def hardCodeOut(fpcList, fpcType):
    main_xml_list = []
    main_xml_dict = {}
    for fpc in fpcList:
        for key, val in fpc.items():
            fpc_cchip_xml_list = []
            for fpcKey, typeVal in fpcType.items():
                if fpcKey == key:
                    printFpcType = typeVal
            #This retrieves the chip type needed to run the correct YAML files, which is tested by the if-statements inside the for-loop.
            for chip, num in val["center_chip"].items():

                if chip == "xm":

                    with Device() as dev:

                        for i in range(num):

                            xm_li_stats = xm_li(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"xm_li_error.yml", 'r') as stream:
                                eval_counters = getEvalDicts(xm_li_stats.items())
                                xm_li_stats_data_dict = parseOut(xm_li_stats, stream, eval_counters)

                            xm_wi_stats = xm_wi(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"xm_wi_statistics.yml", 'r') as stream:
                                eval_counters = getEvalDicts(xm_wi_stats.items())
                                xm_wi_stats_data_dict = parseOut(xm_wi_stats, stream, eval_counters)

                            xm_wo_stats = xm_wo(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"xm_wo_statistics.yml", 'r') as stream:
                                eval_counters = getEvalDicts(xm_wo_stats.items())
                                xm_wo_stats_data_dict = parseOut(xm_wo_stats, stream, eval_counters)

                            xm_fo_stats = xm_fo(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"xm_fo_statistics.yml", 'r') as stream:
                                eval_counters = getEvalDicts(xm_fo_stats.items())
                                xm_fo_stats_data_dict = parseOut(xm_fo_stats, stream, eval_counters)

                            xm_fi_stats_data = xm_fi_stats(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"xm_fi_statistics.yml", 'r') as stream:
                                eval_counters = getEvalDicts(xm_fi_stats_data.items())
                                xm_fi_stats_data_dict = parseOut(xm_fi_stats_data, stream, eval_counters)

                            xm_fi_err_data = xm_fi_err(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"xm_fi_error.yml", 'r') as stream:
                                eval_counters = getEvalDicts(xm_fi_err_data.items())
                                xm_fi_err_data_dict = parseOut(xm_fi_err_data, stream, eval_counters)

                            xm_lo_stats = xm_lo(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"xm_lo_statistics.yml", 'r') as stream:
                                eval_counters = getEvalDicts(xm_lo_stats.items())
                                xm_lo_stats_data_dict = parseOut(xm_lo_stats, stream, eval_counters)

                            xm_host_drop_data = xm_host(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"xm_host_drop.yml", 'r') as stream:
                                eval_counters = getEvalDicts(xm_host_drop_data.items())
                                xm_host_drop_data_dict = parseOut(xm_host_drop_data, stream, eval_counters)

                            xm_drd_err = xm_drd(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"xm_drd_error.yml", 'r') as stream:
                                eval_counters = getEvalDicts(xm_drd_err.items())
                                xm_drd_err_data_dict = parseOut(xm_drd_err, stream, eval_counters)

                            xm_pt_stats = xm_pt(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"xm_pt_statistics.yml", 'r') as stream:
                                eval_counters = getEvalDicts(xm_pt_stats.items())
                                xm_pt_stats_data_dict = parseOut(xm_pt_stats, stream, eval_counters)

                            update_fpc_xml_list = [{"chip-instance":str(i)},\
                            {str(xm_host_drop_data):xm_host_drop_data_dict},\
                            {str(xm_lo_stats):xm_lo_stats_data_dict},\
                            {str(xm_li_stats):xm_li_stats_data_dict},\
                            {str(xm_wi_stats):xm_wi_stats_data_dict},\
                            {str(xm_wo_stats):xm_wo_stats_data_dict},\
                            {str(xm_fo_stats):xm_fo_stats_data_dict},\
                            {str(xm_fi_stats_data):xm_fi_stats_data_dict},\
                            {str(xm_fi_err_data):xm_fi_err_data_dict},\
                            {str(xm_drd_err):xm_drd_err_data_dict},\
                            {str(xm_pt_stats):xm_pt_stats_data_dict}]

                            fpc_xml_dict = {}

                            for xm_table_dict in update_fpc_xml_list:
                                fpc_xml_dict.update(xm_table_dict)

                            dict_for_main_xml_list = {"fpc-num":str(key),"fpc-type":printFpcType,"center-chip":fpc_xml_dict}

                            fpc_xml_dict = {}

                            fpc_cchip_xml_list.append(dict_for_main_xml_list)

                if chip == "mqss":

                    with Device() as dev:
                        for i in range(num):

                            ea_li_stats = ea_li(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"ea_li_error.yml", 'r') as stream:
                                eval_counters = getEvalDicts(ea_li_stats.items())
                                ea_li_stats_data_dict = parseOut(ea_li_stats, stream, eval_counters)

                            ea_wi_stats = ea_wi(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"ea_wi_statistics.yml", 'r') as stream:
                                eval_counters = getEvalDicts(ea_wi_stats.items())
                                ea_wi_stats_data_dict = parseOut(ea_wi_stats, stream, eval_counters)

                            ea_wo_stats = ea_wo(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"ea_wo_statistics.yml", 'r') as stream:
                                eval_counters = getEvalDicts(ea_wo_stats.items())
                                ea_wo_stats_data_dict = parseOut(ea_wo_stats, stream, eval_counters)

                            ea_fo_stats = ea_fo(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"ea_fo_statistics.yml", 'r') as stream:
                                eval_counters = getEvalDicts(ea_fo_stats.items())
                                ea_fo_stats_data_dict = parseOut(ea_fo_stats, stream, eval_counters)

                            ea_fi_stats_data = ea_fi_stats(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"ea_fi_statistics.yml", 'r') as stream:
                                eval_counters = getEvalDicts(ea_fi_stats_data.items())
                                ea_fi_stats_data_dict = parseOut(ea_fi_stats_data, stream, eval_counters)

                            ea_fi_err_data = ea_fi_err(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"ea_fi_error.yml", 'r') as stream:
                                eval_counters = getEvalDicts(ea_fi_err_data.items())
                                ea_fi_err_data_dict = parseOut(ea_fi_err_data, stream, eval_counters)

                            ea_lo_stats = ea_lo(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"ea_lo_statistics.yml", 'r') as stream:
                                eval_counters = getEvalDicts(ea_lo_stats.items())
                                ea_lo_stats_data_dict = parseOut(ea_lo_stats, stream, eval_counters)

                            ea_host_drop_data = ea_host(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"ea_host_drop.yml", 'r') as stream:
                                eval_counters = getEvalDicts(ea_host_drop_data.items())
                                ea_host_drop_data_dict = parseOut(ea_host_drop_data, stream, eval_counters)

                            ea_drd_err = ea_drd(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"ea_drd_error.yml", 'r') as stream:
                                eval_counters = getEvalDicts(ea_drd_err.items())
                                ea_drd_err_data_dict = parseOut(ea_drd_err, stream, eval_counters)

                            ea_pt_stats = ea_pt(dev).get(target = key, args = {'chip_instance': i})
                            with open(path+"ea_pt_statistics.yml", 'r') as stream:
                                eval_counters = getEvalDicts(ea_pt_stats.items())
                                ea_pt_stats_data_dict = parseOut(ea_pt_stats, stream, eval_counters)

                            update_fpc_xml_list = [{"chip-instance":str(i)},\
                            {str(ea_host_drop_data):ea_host_drop_data_dict},\
                            {str(ea_lo_stats):ea_lo_stats_data_dict},\
                            {str(ea_li_stats):ea_li_stats_data_dict},\
                            {str(ea_wi_stats):ea_wi_stats_data_dict},\
                            {str(ea_wo_stats):ea_wo_stats_data_dict},\
                            {str(ea_fo_stats):ea_fo_stats_data_dict},\
                            {str(ea_fi_stats_data):ea_fi_stats_data_dict},\
                            {str(ea_fi_err_data):ea_fi_err_data_dict},\
                            {str(ea_drd_err):ea_drd_err_data_dict},\
                            {str(ea_pt_stats):ea_pt_stats_data_dict}]

                            fpc_xml_dict = {}

                            for ea_table_dict in update_fpc_xml_list:
                                fpc_xml_dict.update(ea_table_dict)

                            dict_for_main_xml_list = {"fpc-num":str(key),"fpc-type":printFpcType,"center-chip":fpc_xml_dict}

                            fpc_xml_dict = {}

                            fpc_cchip_xml_list.append(dict_for_main_xml_list)

        main_xml_list.append(fpc_cchip_xml_list)

    now = datetime.datetime.now()

    for xml_elem in [{"date":now},{"fpcs":main_xml_list}]:
        main_xml_dict.update(xml_elem)

    create_xml_doc(main_xml_dict)

def create_xml_doc(xml_dict):
    top = etree.Element('all-data')
    for key, val in xml_dict.items():
        if key == "date":
            date = str(val)

    date_node = etree.SubElement(top, 'date')
    date_node.text = str(date)

    for key, value in xml_dict.items():
        if isinstance(value, list):
            for fpc_list in value:

                if fpc_list:

                    fpc_node = etree.SubElement(top, 'fpc')

                    fpc_num = etree.SubElement(fpc_node, "fpc-num")
                    fpc_num.text = str(fpc_list[0]["fpc-num"])

                    fpc_type = etree.SubElement(fpc_node, "fpc-type")
                    fpc_type.text = str(fpc_list[0]["fpc-type"])

                    center_chip = etree.SubElement(fpc_node, "center-chip")

                    for chip_instance in fpc_list:

                        chip_instance_list = etree.SubElement(center_chip, "chip-instance")

                        chip_instance_node = etree.SubElement(chip_instance_list, "chip-instance-num")
                        chip_instance_node.text = str(chip_instance["center-chip"]["chip-instance"])

                        tables_container = etree.SubElement(chip_instance_list, "tables")

                        for elem in sorted(chip_instance["center-chip"].items()):
                            if isinstance(elem[1], dict):
                                str_for_table_name = str(elem[0])
                                sep = ":"
                                clean_table_name = str_for_table_name.split(sep, 1)[0]
                                table_name = etree.SubElement(tables_container, clean_table_name)
                                for counter in sorted(elem[1].items(), key=lambda x: x[0]):
                                    if isinstance(counter[1], dict):
                                        plane = "plane-"+str(counter[0])

                                        for packets_sent_label, packets_sent_num in counter[1].items():
                                            plane_node = etree.SubElement(table_name, plane)
                                            plane_node.text = packets_sent_label+packets_sent_num

                                    else:
                                        str_for_counter_name = str(counter[0])
                                        clean_counter_name = str_for_counter_name.split(sep, 1)[0]
                                        clean_counter_name = clean_counter_name.replace(" ", "_")

                                        counter_node = etree.SubElement(table_name, clean_counter_name)
                                        counter_node.text = str(counter[0])+str(counter[1])

    etree.dump(top)

#Retrieves the online FPCs
fpcDicts = online_fpc()

#Uses the online fpcs to get the center chip type for each fpc
chips = onbox_chip_types(fpcDicts)

fpcType = get_fpc_type(fpcDicts)

#retrieves and prints data for each fpc center chip
hardCodeOut(chips, fpcType)
