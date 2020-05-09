import yaml
import re

def parse_command_output(stats, stream):
    eval_counters = __get_eval_dict(stats.items())

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
                        ea_fo_total_packets_sent_label = str(ea_fo_key)+":"
                        ea_fo_total_packets_sent_num = str(ea_fo_val)
                        table_counters.update({plane_num:{ea_fo_total_packets_sent_label:ea_fo_total_packets_sent_num}})
            #This loop iterates through the dict in item[1].items(), which contains the a dict of the keys and values from the Table
            for key,val in item[1].items():
                if "cchip" in str(item[0]):
                    appstring_counter_label = appstring+" "+str(key)+":"
                    appstring_counter_num = str(val)
                    table_counters.update({appstring_counter_label: appstring_counter_num})
        #if item doesn't contain a dict in item[1] of values, it contains just a singular key-value pair, and can simply be printed this way
        else:
            eval_key_list = __find_eval_keys(d)
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

    evals = __find_eval(d, eval_counters)
    evalKeys = __find_eval_keys(d)
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

def __find_eval(d, eval_counters):
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
                            for k,v in eval_counters.items():
                                if yamlVar == k:
                                    newStr = d[key]["eval"][evalKey].replace("{{ "+yamlVar+" }}", v)
                                    d[key]["eval"][evalKey]=newStr
                    evals.append(newStr)
    return evals

def __find_eval_keys(d):
    evalKeys = []
    for key in d.keys():
        if "eval" in d[key].keys():
            for evalKey in d[key]["eval"].keys():
                evalKeys.append({evalKey: d[key]["eval"][evalKey].replace("{{ data }}", "eval_counters")})

    return evalKeys

def __get_eval_dict(stats):
    evalDicts1 = {}
    evalDicts2 = {}
    for k,v in stats:
        if isinstance(v, dict):
            evalDicts1.update({k: v})
        else:
            evalDicts2.update({str(k): str(v)})

    if evalDicts1:
        return evalDicts1
    else:
        return evalDicts2
