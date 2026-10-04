import edq.config.common

class BaseApplicationConfig(edq.config.common.InternalApplicationConfig):
    """
    A representation of the configuration options for an application, project, or use case.
    The key use of this class is to provide typing for config options.
    When creating a TieredConfigInfo, this class (or a subclass) will be constructed with from_dict() using the resulting raw config values.
    Users of this library can extend this class (and pass that class along (usually in edq.core.argparse.get_default_parser())
    to get config typed specifically for their application.
    """

edq.config.common._DEFAULT_APPLICATION_CONFIG_CLASS = BaseApplicationConfig
edq.config.common._application_config_class = edq.config.common._DEFAULT_APPLICATION_CONFIG_CLASS
