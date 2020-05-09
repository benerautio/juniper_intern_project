from jnpr.junos import Device
from __chip_types import chip_types_dict
from __parse_cchip_command_output import parse_command_output
from timer import profile, print_prof_data, clear_prof_data # used for execution time


# from xm_li_error import CChipLiInterruptStatsTable as xm_li
# from xm_wi_statistics import CChipWiStatsTable as xm_wi
# from xm_wo_statistics import CChipWoStatsTable as xm_wo
# from xm_fo_statistics import CChipFOStatsTable as xm_fo
# from xm_fi_statistics import CChipFiStatsTable as xm_fi_stats
# from xm_fi_error import CChipFiErrTable as xm_fi_err
# from xm_lo_statistics import CChipLoStatsTable as xm_lo
# from xm_host_drop import CChipHostDropTable as xm_host
# from xm_drd_error import CChipDRDErrTable as xm_drd
# from xm_pt_statistics import CChipPTStatTable as xm_pt
#
# from ea_li_error import CChipLiInterruptStatsTable as ea_li
# from ea_wi_statistics import CChipWiStatsTable as ea_wi
# from ea_wo_statistics import CChipWoStatsTable as ea_wo
# from ea_fo_statistics import CChipFOStatsTable as ea_fo
# from ea_fi_statistics import CChipFiStatsTable as ea_fi_stats
# from ea_fi_error import CChipFiErrTable as ea_fi_err
# from ea_lo_statistics import CChipLoStatsTable as ea_lo
# from ea_host_drop import CChipHostDropTable as ea_host
# from ea_drd_error import CChipDRDErrTable as ea_drd
# from ea_pt_statistics import CChipPTStatTable as ea_pt

from yamls.xm_li_error import CChipLiInterruptStatsTable as xm_li
from yamls.xm_wi_statistics import CChipWiStatsTable as xm_wi
from yamls.xm_wo_statistics import CChipWoStatsTable as xm_wo
from yamls.xm_fo_statistics import CChipFOStatsTable as xm_fo
from yamls.xm_fi_statistics import CChipFiStatsTable as xm_fi_stats
from yamls.xm_fi_error import CChipFiErrTable as xm_fi_err
from yamls.xm_lo_statistics import CChipLoStatsTable as xm_lo
from yamls.xm_host_drop import CChipHostDropTable as xm_host
from yamls.xm_drd_error import CChipDRDErrTable as xm_drd
from yamls.xm_pt_statistics import CChipPTStatTable as xm_pt

from yamls.ea_li_error import CChipLiInterruptStatsTable as ea_li
from yamls.ea_wi_statistics import CChipWiStatsTable as ea_wi
from yamls.ea_wo_statistics import CChipWoStatsTable as ea_wo
from yamls.ea_fo_statistics import CChipFOStatsTable as ea_fo
from yamls.ea_fi_statistics import CChipFiStatsTable as ea_fi_stats
from yamls.ea_fi_error import CChipFiErrTable as ea_fi_err
from yamls.ea_lo_statistics import CChipLoStatsTable as ea_lo
from yamls.ea_host_drop import CChipHostDropTable as ea_host
from yamls.ea_drd_error import CChipDRDErrTable as ea_drd
from yamls.ea_pt_statistics import CChipPTStatTable as ea_pt

path = "/var/db/scripts/action/chip_agnostic_command_package/chip_agnostic_command/yamls"

class Chassis(Device):
    '''
    Chassis class - extending jnpr.junos.Device to include FPCs component
        In reality we should also include fabric part
    '''

    def __init__(self):
        '''
        __init__ inherit from Device, except that it look for local
        v.s. remote
        '''
        Device.__init__(self)
        self.__set_fpc_online()


    def __set_fpc_online(self):
        '''
        set FPC status of a chassis inside the Chassis class
        '''
        self.open()
        op = self.rpc.get_fpc_information()
        online = op.xpath('./fpc[normalize-space(state) = "Online"]/slot')

        online_fpcs = []

        for i in online:
            if i.text is not None:
                online_fpcs.append('fpc'+i.text)

        chassis_components = []

        for online_fpc in online_fpcs:
            chassis_fpc = FPC(online_fpc)
            chassis_components.append(chassis_fpc)

        self.__online_fpcs = chassis_components

        self.close()

    def get_online_fpcs(self):
        return self.__online_fpcs

    def __repr__(self):
        return "Chassis(%r)" % self.__online_fpcs

class FPC:


    def __init__(self, fpc_num):

        if fpc_num in self.__get_fpcs_online():
            self.fpc_num = fpc_num
            self.set_fpc_type()
            self.set_center_chips()
        else:
            print "FPC isn't online"
            #raise ValueError("This FPC is not online")
            #del self

    #cache this in Chassis
    @staticmethod
    def __get_fpcs_online():
        dev = Device()
        dev.open()
        op = dev.rpc.get_fpc_information()
        online = op.xpath('./fpc[normalize-space(state) = "Online"]/slot')

        online_fpcs = []

        for i in online:
            if i.text is not None:
                online_fpcs.append('fpc'+i.text)

        dev.close()
        return online_fpcs


    def set_fpc_type(self):
        dev = Device()
        dev.open()

        #If xpath 1.0, must do lower case like this. If 2.0, can use lower-case()
        op = dev.rpc.get_chassis_inventory()
        chips = chip_types_dict()
        fpc = '"{}"'.format(self.fpc_num)
        desc = op.xpath('//chassis-module[translate(translate\
        (normalize-space(name), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", \
        "abcdefghijklmnopqrstuvwxyz"), " ","") = '+fpc+']/description')

        for i in desc:
            if i.text is not None:
                fpc_type = i.text

        self.fpc_type = fpc_type
        dev.close()


    def set_center_chips(self):
        dev = Device()
        dev.open()

        chips = chip_types_dict()
        op = dev.rpc.get_chassis_inventory()
        fpc = '"{}"'.format(self.fpc_num)
        desc = op.xpath('//chassis-module[translate(translate\
        (normalize-space(name), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", \
        "abcdefghijklmnopqrstuvwxyz"), " ","") = '+fpc+']/description')

        for i in desc:
            if i.text is not None:
                fpc_type = i.text

        center_chip_type = chips["ChipTypeMap"][fpc_type]["center_chip"]

        list_of_center_chips = []

        for key, val in center_chip_type.items():
            for i in range(val):
                chip_obj = center_chip(self.fpc_num, key, i)
                list_of_center_chips.append(chip_obj)

        self.center_chips = list_of_center_chips

        dev.close()

    def get_fpc_center_chip(self):
        #how to print this in human readable?
        return self.center_chips

    def get_fpc_num(self):
        return self.fpc_num

    def get_fpc_type(self):
        return self.fpc_type

    def __repr__(self):
        chips = chip_types_dict()
        #return str(self.fpc_num) + " model " + self.fpc_type +" center chip "+ str(chips["ChipTypeMap"][self.fpc_type]["center_chip"])
        return "FPC(%r, %r, %r)" % (self.fpc_num, self.fpc_type, self.center_chips)

class center_chip:
    def __init__(self, fpc_num, chip_type, chip_instance):
        self.__fpc_num = fpc_num
        self.chip_type = chip_type
        self.chip_instance = chip_instance

    def get_chip_type(self):
        return self.chip_type

    def get_chip_instance(self):
        return self.chip_instance


    def get_CChipLiInterruptStats(self):
        with Device() as dev:
            if self.chip_type == "xm":
                with open(path+"/xm_li_error.yml", "r") as stream:
                    xm_li_stats = xm_li(dev).get(target = self.__fpc_num , args = {'chip_instance': self.chip_instance})
                    xm_li_stats_data_dict = parse_command_output(xm_li_stats, stream)
                    return {self.__table_name(xm_li_stats):xm_li_stats_data_dict}
            elif self.chip_type == "mqss":
                with open(path+"/ea_li_error.yml", "r") as stream:
                    ea_li_stats = ea_li(dev).get(target = self.__fpc_num , args = {'chip_instance': self.chip_instance})
                    ea_li_stats_data_dict = parse_command_output(ea_li_stats, stream)
                    return {self.__table_name(ea_li_stats):ea_li_stats_data_dict}
            else:
                print "This chip type does not have a YAML file for the command"
                return None


    def get_CChipWiStats(self):
        with Device() as dev:
            if self.chip_type == "xm":
                with open(path+"/xm_wi_statistics.yml", "r") as stream:
                    xm_wi_stats = xm_wi(dev).get(target = self.__fpc_num , args = {'chip_instance': self.chip_instance})
                    xm_wi_stats_data_dict = parse_command_output(xm_wi_stats, stream)
                    return {self.__table_name(xm_wi_stats):xm_wi_stats_data_dict}
            elif self.chip_type == "mqss":
                with open(path+"/ea_wi_statistics.yml", "r") as stream:
                    ea_wi_stats = ea_wi(dev).get(target = self.__fpc_num , args = {'chip_instance': self.chip_instance})
                    ea_wi_stats_data_dict = parse_command_output(ea_wi_stats, stream)
                    return {self.__table_name(ea_wi_stats):ea_wi_stats_data_dict}
            else:
                print "This chip type does not have a YAML file for the command"
                return None


    def get_CChipWoStats(self):
        with Device() as dev:
            if self.chip_type == "xm":
                with open(path+"/xm_wo_statistics.yml", "r") as stream:
                    xm_wo_stats = xm_wo(dev).get(target = self.__fpc_num , args = {'chip_instance': self.chip_instance})
                    xm_wo_stats_data_dict = parse_command_output(xm_wo_stats, stream)
                    return {self.__table_name(xm_wo_stats):xm_wo_stats_data_dict}
            elif self.chip_type == "mqss":
                with open(path+"/ea_wo_statistics.yml", "r") as stream:
                    ea_wo_stats = ea_wo(dev).get(target = self.__fpc_num , args = {'chip_instance': self.chip_instance})
                    ea_wo_stats_data_dict = parse_command_output(ea_wo_stats, stream)
                    return {self.__table_name(ea_wo_stats):ea_wo_stats_data_dict}
            else:
                print "This chip type does not have a YAML file for the command"
                return None


    def get_CChipFOStats(self):
        with Device() as dev:
            if self.chip_type == "xm":
                with open(path+"/xm_fo_statistics.yml", "r") as stream:
                    xm_fo_stats = xm_fo(dev).get(target = self.__fpc_num , args = {'chip_instance': self.chip_instance})
                    xm_fo_stats_data_dict = parse_command_output(xm_fo_stats, stream)
                    return {self.__table_name(xm_fo_stats):xm_fo_stats_data_dict}
            elif self.chip_type == "mqss":
                with open(path+"/ea_fo_statistics.yml", "r") as stream:
                    ea_fo_stats = ea_fo(dev).get(target = self.__fpc_num , args = {'chip_instance': self.chip_instance})
                    ea_fo_stats_data_dict = parse_command_output(ea_fo_stats, stream)
                    return {self.__table_name(ea_fo_stats):ea_fo_stats_data_dict}
            else:
                print "This chip type does not have a YAML file for the command"
                return None


    def get_CChipFiStats(self):
        with Device() as dev:
            if self.chip_type == "xm":
                with open(path+"/xm_fi_statistics.yml", "r") as stream:
                    xm_fi_stat = xm_fi_stats(dev).get(target = self.__fpc_num , args = {'chip_instance': self.chip_instance})
                    xm_fi_stats_data_dict = parse_command_output(xm_fi_stat, stream)
                    return {self.__table_name(xm_fi_stat):xm_fi_stats_data_dict}
            elif self.chip_type == "mqss":
                with open(path+"/ea_fi_statistics.yml", "r") as stream:
                    ea_fi_stat = ea_fi_stats(dev).get(target = self.__fpc_num , args = {'chip_instance': self.chip_instance})
                    ea_fi_stats_data_dict = parse_command_output(ea_fi_stat, stream)
                    return {self.__table_name(ea_fi_stat):ea_fi_stats_data_dict}
            else:
                print "This chip type does not have a YAML file for the command"
                return None


    def get_CChipFiErr(self):
        with Device() as dev:
            if self.chip_type == "xm":
                with open(path+"/xm_fi_error.yml", "r") as stream:
                    xm_fi_error = xm_fi_err(dev).get(target = self.__fpc_num , args = {'chip_instance': self.chip_instance})
                    xm_fi_error_data_dict = parse_command_output(xm_fi_error, stream)
                    return {self.__table_name(xm_fi_error):xm_fi_error_data_dict}
            elif self.chip_type == "mqss":
                with open(path+"/ea_fi_error.yml", "r") as stream:
                    ea_fi_error = ea_fi_err(dev).get(target = self.__fpc_num , args = {'chip_instance': self.chip_instance})
                    ea_fi_error_data_dict = parse_command_output(ea_fi_error, stream)
                    return {self.__table_name(ea_fi_error):ea_fi_error_data_dict}
            else:
                print "This chip type does not have a YAML file for the command"
                return None

    def get_CChipLoStats(self):
        with Device() as dev:
            if self.chip_type == "xm":
                with open(path+"/xm_lo_statistics.yml", "r") as stream:
                    xm_lo_statistics = xm_lo(dev).get(target = self.__fpc_num , args = {'chip_instance': self.chip_instance})
                    xm_lo_statistics_data_dict = parse_command_output(xm_lo_statistics, stream)
                    return {self.__table_name(xm_lo_statistics):xm_lo_statistics_data_dict}
            elif self.chip_type == "mqss":
                with open(path+"/ea_lo_statistics.yml", "r") as stream:
                    ea_lo_statistics = ea_lo(dev).get(target = self.__fpc_num , args = {'chip_instance': self.chip_instance})
                    ea_lo_statistics_data_dict = parse_command_output(ea_lo_statistics, stream)
                    return {self.__table_name(ea_lo_statistics):ea_lo_statistics_data_dict}
            else:
                print "This chip type does not have a YAML file for the command"
                return None

    def get_CChipHostDrop(self):
        with Device() as dev:
            if self.chip_type == "xm":
                with open(path+"/xm_host_drop.yml", "r") as stream:
                    xm_host_drop = xm_host(dev).get(target = self.__fpc_num , args = {'chip_instance': self.chip_instance})
                    xm_host_drop_data_dict = parse_command_output(xm_host_drop, stream)
                    return {self.__table_name(xm_host_drop):xm_host_drop_data_dict}
            elif self.chip_type == "mqss":
                with open(path+"/ea_host_drop.yml", "r") as stream:
                    ea_host_drop = ea_host(dev).get(target = self.__fpc_num , args = {'chip_instance': self.chip_instance})
                    ea_host_drop_data_dict = parse_command_output(ea_host_drop, stream)
                    return {self.__table_name(ea_host_drop):ea_host_drop_data_dict}
            else:
                print "This chip type does not have a YAML file for the command"
                return None


    def get_CChipDRDErr(self):
        with Device() as dev:
            if self.chip_type == "xm":
                with open(path+"/xm_drd_error.yml", "r") as stream:
                    xm_drd_stats = xm_drd(dev).get(target = self.__fpc_num , args = {'chip_instance': self.chip_instance})
                    xm_drd_stats_data_dict = parse_command_output(xm_drd_stats, stream)
                    return {self.__table_name(xm_drd_stats):xm_drd_stats_data_dict}
            elif self.chip_type == "mqss":
                with open(path+"/ea_drd_error.yml", "r") as stream:
                    ea_drd_stats = ea_drd(dev).get(target = self.__fpc_num , args = {'chip_instance': self.chip_instance})
                    ea_drd_stats_data_dict = parse_command_output(ea_drd_stats, stream)
                    return {self.__table_name(ea_drd_stats):ea_drd_stats_data_dict}
            else:
                print "This chip type does not have a YAML file for the command"
                return None


    def get_CChipPTStat(self):
        with Device() as dev:
            if self.chip_type == "xm":
                with open(path+"/xm_pt_statistics.yml", "r") as stream:
                    xm_pt_stats = xm_pt(dev).get(target = self.__fpc_num , args = {'chip_instance': self.chip_instance})
                    xm_pt_stats_data_dict = parse_command_output(xm_pt_stats, stream)
                    return {self.__table_name(xm_pt_stats):xm_pt_stats_data_dict}
            elif self.chip_type == "mqss":
                with open(path+"/ea_pt_statistics.yml", "r") as stream:
                    ea_pt_stats = ea_pt(dev).get(target = self.__fpc_num , args = {'chip_instance': self.chip_instance})
                    ea_pt_stats_data_dict = parse_command_output(ea_pt_stats, stream)
                    return {self.__table_name(ea_pt_stats):ea_pt_stats_data_dict}
            else:
                print "This chip type does not have a YAML file for the command"
                return None

    @staticmethod
    def __table_name(table_name):
        str_for_table_name = str(table_name)
        sep = ":"
        clean_table_name = str_for_table_name.split(sep, 1)[0]
        return clean_table_name

    def __repr__(self):
        return "center_chip(%r, %r)" % (self.chip_type, self.chip_instance)

'''
Testing block after this
'''

def create_chassis():
    obj = Chassis()
    return obj

if __name__ == "__main__":
    obj = create_chassis()

    print obj

    for i in obj.get_online_fpcs():
        print i.get_fpc_num()
        for chip in i.get_fpc_center_chip():
            print chip.get_chip_type()
            print chip.get_chip_instance()
            print chip.get_CChipLiInterruptStats()
            print chip.get_CChipWiStats()
            print chip.get_CChipWoStats()
            print chip.get_CChipFOStats()
            print chip.get_CChipFiStats()
            print chip.get_CChipFiErr()
            print chip.get_CChipLoStats()
            print chip.get_CChipHostDrop()
            print chip.get_CChipDRDErr()
            print chip.get_CChipPTStat()
            print "\n"
    print_prof_data()
