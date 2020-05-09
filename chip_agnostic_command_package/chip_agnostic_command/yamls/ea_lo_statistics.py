#from jnpr.junos.factory import loadyaml
#from os.path import splitext
#_YAML_ = splitext(__file__)[0] + '.yml'
#globals().update(loadyaml(_YAML_))
import yaml
import yamlordereddictloader
from jnpr.junos.factory.factory_loader import FactoryLoader
from jnpr.junos.factory import loadyaml
from os.path import splitext
_YAML_ = splitext(__file__)[0] + '.yml'
#print loadyaml(_YAML_)
#globals().update(loadyaml(_YAML_))
globals().update(FactoryLoader().load(yaml.load(open(_YAML_),\
                                                  Loader=yamlordereddictloader.Loader)))
