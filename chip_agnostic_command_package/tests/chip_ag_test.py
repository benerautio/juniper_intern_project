#tested when ran out of action directory
#to test, run as op command: "op url /var/db/scripts/action/chip_agnostic_command_package/tests/chip_ag_test.py"
import sys
if "/var/db/scripts/op" not in sys.path:
    sys.path.append("/var/db/scripts/op")
from chip_agnostic_command_package.chip_agnostic_command.chassis_class import Chassis
from chip_agnostic_command_package.chip_agnostic_command.xml_builder import xml_builder

obj = Chassis()
xml = xml_builder(obj)

xml.print_xml()
