'''
Takes Chassis instance, Builds XML document to be used in the chip-agnostic command
'''

#import extend_device
from lxml import etree
import datetime
from  chassis_class import Chassis

class xml_builder:

    def __init__(self, chassis_instance):
        if isinstance(chassis_instance, Chassis):
            self.chassis_instance = chassis_instance
            self.__create_xml()
        else:
            raise ValueError("Must pass instance of Chassis to xml_builder")

    def __create_xml(self):
        top = etree.Element('all-data')

        self.__xml = top

        date_node = etree.SubElement(top, 'date')
        now = datetime.datetime.now()
        date_node.text = str(now)

        for fpc in self.chassis_instance.get_online_fpcs():
            fpc_node = etree.SubElement(top, 'fpc')

            fpc_num = etree.SubElement(fpc_node, "fpc-num")
            fpc_num.text = fpc.get_fpc_num()

            fpc_type = etree.SubElement(fpc_node, "fpc-type")
            fpc_type.text = fpc.get_fpc_type()

            center_chip = etree.SubElement(fpc_node, "center-chip")

            for chip in fpc.get_fpc_center_chip():
                chip_instance_list = etree.SubElement(center_chip, "chip-instance")

                chip_instance_node = etree.SubElement(chip_instance_list, "chip-instance-num")
                chip_instance_node.text = str(chip.get_chip_instance())

                tables_container = etree.SubElement(chip_instance_list, "tables")

                #run all cchip commands
                self.__build_chip_data_xml(tables_container, chip.get_CChipLiInterruptStats())
                self.__build_chip_data_xml(tables_container, chip.get_CChipWiStats())
                self.__build_chip_data_xml(tables_container, chip.get_CChipWoStats())
                self.__build_chip_data_xml(tables_container, chip.get_CChipFOStats())
                self.__build_chip_data_xml(tables_container, chip.get_CChipFiStats())
                self.__build_chip_data_xml(tables_container, chip.get_CChipFiErr())
                self.__build_chip_data_xml(tables_container, chip.get_CChipLoStats())
                self.__build_chip_data_xml(tables_container, chip.get_CChipHostDrop())
                self.__build_chip_data_xml(tables_container, chip.get_CChipDRDErr())
                self.__build_chip_data_xml(tables_container, chip.get_CChipPTStat())

    def update_xml(self):
        self.__create_xml()

    def print_xml(self):
        etree.dump(self.__xml)

    @staticmethod
    def __build_chip_data_xml(tables_container, chip_data):
        if chip_data is not None:
            for table, data in chip_data.items():
                table_name = etree.SubElement(tables_container, table)
                for counter_label, counter_data in data.items():
                    if isinstance(counter_data, dict):
                        plane = "plane_"+str(counter_label)
                        for packets_label, packets_num in counter_data.items():
                            plane_node = etree.SubElement(table_name, plane)
                            packets_node = etree.SubElement(plane_node, packets_label.replace(":",""))
                            packets_node.text = packets_label+str(packets_num)

                    else:
                        str_for_counter_name = counter_label.split(":", 1)[0].replace(" ", "_")
                        counter_node = etree.SubElement(table_name, str_for_counter_name)
                        counter_node.text = str_for_counter_name + ":" + str(counter_data)
