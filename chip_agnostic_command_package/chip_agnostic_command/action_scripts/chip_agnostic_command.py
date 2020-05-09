from chip_agnostic_command_package.chip_agnostic_command.chassis_class import Chassis
from chip_agnostic_command_package.chip_agnostic_command.xml_builder import xml_builder

obj = Chassis()
xml = xml_builder(obj)

xml.print_xml()
