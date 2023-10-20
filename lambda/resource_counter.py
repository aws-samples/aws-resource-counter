"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, NamedTuple, TypedDict, Final
from collections.abc import Callable

import boto3  # type: ignore

####

CONST_SERVICE_FILE: Final[str] = 'services.json'
CONST_MAX_METRIC_DATA: Final[int] = 1000
CONST_ELEMENT: Final[str] = 'element'
CONST_RESOURCES: Final[str] = 'resources'
CONST_COUNT: Final[str] = 'count'
CONST_GROUP_BY: Final[str] = 'groupBy'
CONST_IF_EXISTS: Final[str] = 'ifExists'
CONST_DEFAULT_NAMESPACE: Final[str] = 'defaultNamespace'
CONST_DEFAULT_DIMENSION_NAME: Final[str] = 'defaultDimensionName'
CONST_NEXT_IN_RESPONSE: Final[str] = 'next-in-response'

####### Get values from environment variables  ######

## Logging level options in less verbosity order. INFO is the default.
## If you enable DEBUG, it will log boto3 calls as well.
# CRITICAL
# ERROR
# WARNING
# INFO
# DEBUG

# Get logging level from environment variable
if (LOG_LEVEL := os.getenv('LOG_LEVEL', '').upper()) not in {'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'}:
    LOG_LEVEL = 'INFO'

# Set up logging. Set the level if the handler is already configured.
if len(logging.getLogger().handlers) > 0:
    logging.getLogger().setLevel(LOG_LEVEL)
else:
    logging.basicConfig(level=LOG_LEVEL)


cloudwatch_client = boto3.client('cloudwatch')


#======================================================================================================================
# Class and type alias
#======================================================================================================================

class MetricData(NamedTuple):
    """
    Metric data.
    """
    namespace: str
    dimension_name: str
    dimension_value: str
    metric_name: str
    metric_value: int
    timestamp: datetime
    def __iter__(self):
        yield self.namespace
        yield self.dimension_name
        yield self.dimension_value
        yield self.metric_name
        yield self.metric_value
        yield self.timestamp.isoformat()


class ResourceElement(TypedDict):
    """
    Resource element configuration
    """
    client: str
    method: str
    kwargs: dict
    iterateOver: list[str]
    nextInResponse: str
    nextInRequest: str
    mustExists: bool

class GroupByElement(TypedDict):
    """
    GroupBy element configuration
    """
    element: list[str]
    values: list[str]
    capitalize: bool
    customName: bool

class IfExistsElement(TypedDict):
    """
    IfExists element configuration
    """
    element: str
    existsSuffix: str
    notExistsSuffix: str

class CountElement(TypedDict):
    """
    Count element configuration
    """
    generateTotal: bool
    groupBy: GroupByElement
    ifExists: IfExistsElement

class MetricElement(TypedDict):
    """
    Metric element configuration
    """
    namespace: str
    dimensionName: str
    dimensionValue: str
    metricName: str

class ResourceConfiguration(TypedDict):
    """
    Resource configuration
    """
    index: int
    type: str
    resource: ResourceElement
    count: CountElement
    metric: MetricElement
    """
    Dictionary of boto3 client.
    :key Client resource name as defined on boto3
    :value boto3 client object
    """


Boto3Clients = dict[str, Any]
Metric = dict[str, MetricData]
Namespace = dict[str, Metric]
MetricCount = dict[str, int]
CloudWatchMetricData = dict[str, Any]
CloudWatchMetricDataList = list[CloudWatchMetricData]

#======================================================================================================================
# Recursive function to iterate over a list of resources
#======================================================================================================================

# Recursive function to iterate over a list of dictionaries
def list_from_paginator(clients: Boto3Clients, resources: list[Any], config_service: ResourceConfiguration) -> None:
    """
    List resources from a paginated service method.
    :param clients: Dictionary of boto3 clients
    :param resources: List of resources to be filled. It must be an initialized list.
    :param config_service: Dictionary of service config
    """
    if resources is None:
        raise ValueError('resources is not initialized')

    service_name: str = config_service['resource']['client']
    method: str = config_service['resource']['method']
    kwargs: dict[str, Any] = config_service['resource']['kwargs']
    iterate_over: list[str] = config_service['resource']['iterateOver']
    must_exists: bool = config_service['resource']['mustExists']
    client = clients[service_name]

    paginator = client.get_paginator(method)
    for page in paginator.paginate(**kwargs):
        logging.info('Page for service: %s, method: %s, iterate_over: %s', service_name, method, iterate_over)
        iterate_over_response_attribute(page, resources, iterate_over, must_exists)

# Recursive function to iterate over a list of dictionaries
def list_next_in_response(clients: Boto3Clients, resources: list[Any], config_service: ResourceConfiguration) -> None:
    """
    List resources from a service method that supports NextToken | NextHandler | NextMarker.
    :param clients: Dictionary of boto3 clients
    :param resources: List of resources
    :param config_service: Dictionary of service config
    """
    if resources is None:
        raise ValueError('resources is not initialized')

    service_name: str = config_service['resource']['client']
    method: str = config_service['resource']['method']
    kwargs: dict[str, Any] = config_service['resource']['kwargs']
    iterate_over: list[str] = config_service['resource']['iterateOver']
    must_exists: bool = config_service['resource']['mustExists']
    next_response: str = config_service['resource']['nextInResponse']
    next_request: str = config_service['resource']['nextInRequest']
    client = clients[service_name]

    # Call method with defined argument
    response = getattr(client, method)(**kwargs)
    while True:
        logging.info('Response for service: %s, method: %s, kwargs: %s, iterate_over: %s', service_name, method, kwargs, iterate_over)
        iterate_over_response_attribute(response, resources, iterate_over, must_exists)

        if next_response not in response:
            break

        kwargs[next_request] = response[next_response]
        logging.info('Found %s for service: %s, method: %s, kwargs: %s, iterate_over: %s', next_response, service_name, method, kwargs, iterate_over)
        response = getattr(client, method)(**kwargs)

# Recursive function to iterate over a list of dictionaries
def list_direct(clients: Boto3Clients, resources: list[Any], config_service: ResourceConfiguration) -> None:
    """
    List resources from a service method direct call without pagination or NextToken | NextHandler | NextMarker.
    :param clients: Dictionary of boto3 clients
    :param resources: List of resources
    :param config_service: Dictionary of service config
    """
    if resources is None:
        raise ValueError('resources is not initialized')

    service_name: str = config_service['resource']['client']
    method: str = config_service['resource']['method']
    kwargs: dict[str, Any] = config_service['resource']['kwargs']
    iterate_over: list[str] = config_service['resource']['iterateOver']
    must_exists: bool = config_service['resource']['mustExists']
    client = clients[service_name]

    # Call method with defined argument
    response = getattr(client, method)(**kwargs)
    logging.info('Response for service: %s, method: %s, kwargs: %s, iterate_over: %s', service_name, method, kwargs, iterate_over)
    iterate_over_response_attribute(response, resources, iterate_over, must_exists)

def iterate_over_response_attribute(dict_object: Any, resources: list[Any], iterate_over: list[str], must_exists: bool) -> None:
    """
    Recursive function to iterate over a list of dictionaries.
    :param dict_object: Dictionary to iterate over
    :param resources: List of resources
    :param iterate_over: List of attributes to iterate over
    :param must_exists: Bool to indicate if iterate_over attribute must exists or not
    """
    logging.info('iterate_over: %s', iterate_over)
    logging.info('Lenght of iterate_over: %s', len(iterate_over))

    if (iterate_attribute := iterate_over[0]) not in dict_object:
        if must_exists:
            logging.error('Attribute %s not found. It must exists.', iterate_attribute)
        else:
            logging.warning('Attribute %s not found. It is optional.', iterate_attribute)
        return

    logging.info('Length of dict_object: %s', len(dict_object[iterate_attribute]))
    logging.debug('dict_object: %s', dict_object[iterate_attribute])

    for item in dict_object[iterate_attribute]:
        if len(iterate_over) > 1:
            logging.info('Call recursively')
            iterate_over_response_attribute(item, resources, iterate_over[1:], must_exists)
        else:
            logging.info('Add item to resources')
            resources.append(item)


#======================================================================================================================
# Recursive function to group resources by dictionary attribute
#======================================================================================================================

def get_metric_count(resources: list[Any], config_service: ResourceConfiguration) -> Metric:
    """
    Count metric resources by the attributes defined on configuration.
    :param resources: List of resources
    :param config_service: Dictionary of service config
    :return: Dictionary of metric count for resources grouped by attribute
    """
    namespace: str = config_service['metric']['namespace']
    dimension_name: str = config_service['metric']['dimensionName']
    dimension_value: str = config_service['metric']['dimensionValue']
    metric_name: str = config_service['metric']['metricName']

    metric_data: Metric = {}

    # Total metric
    if config_service['count']['generateTotal']:
        metric_data[metric_name] = MetricData(namespace, dimension_name, dimension_value, metric_name, len(resources), timestamp=datetime.utcnow())

    metric_count: dict[str, int] = {}
    # Metrics from GroupBy configuration
    if has_group_by(config_service):
        logging.info('Has groupBy')
        metric_count.update(get_metric_count_from_group_by(resources, config_service))
    else:
        logging.info('No groupBy attribute for service: %s', config_service)

    # Metrics from IfExists configuration
    if has_if_exists(config_service):
        logging.info('Has ifExists')
        metric_count.update(get_metric_count_from_if_exists(resources, config_service))
    else:
        logging.info('No ifExists attribute for service: %s', config_service)

    # Add the metric count to the metric data
    for metric_to_add, metric_value in metric_count.items():
        metric_data[metric_to_add] = MetricData(namespace, dimension_name, dimension_value, metric_to_add, metric_value, timestamp=datetime.utcnow())
    return metric_data

def get_metric_count_from_group_by(resources: list[Any], config_service: ResourceConfiguration) -> MetricCount:
    """
    Group resources by dictionary attribute.
    :param resources: List of resources
    :param config_service: Dictionary of service config
    :return: Dictionary of metric count for resources grouped by attribute
    """
    metric_name: str = config_service['metric']['metricName']
    group_by: list[str] = config_service['count']['groupBy']['element']
    group_by_values: list[str] = config_service['count']['groupBy'].get('values', [])
    capitalize: bool = config_service['count']['groupBy']['capitalize']
    custom_name: bool = config_service['count']['groupBy']['customName']
    metric_count: MetricCount = {}

    for resource in resources:
        attribute_value = get_groupby_attribute_value(resource, group_by)
        logging.info('Attribute value: %s', attribute_value)

        # If group by values was defined and the attribute value is not in the group by values, ignore the resource
        if len(group_by_values) > 0:
            if attribute_value not in group_by_values:
                logging.info('Attribute value "%s" not in group_by_values "%s"', attribute_value, group_by_values)
                continue

        # Define the metric name to add based on groupBy attribute value and customName attribute
        # It captilize the attribute value if defined on configuration
        if not custom_name:
            metric_to_add = metric_name
        elif capitalize:
            metric_to_add = f'{metric_name}-{str(attribute_value).capitalize()}'
        else:
            metric_to_add = f'{metric_name}-{attribute_value}'
        #if (metric_to_add := f'{metric_name}-{str(attribute_value).capitalize()}' if capitalize else f'{metric_name}-{attribute_value}') not in metric_count:
        if metric_to_add not in metric_count:
            metric_count[metric_to_add] = 0
        metric_count[metric_to_add] += 1

    return metric_count

def get_metric_count_from_if_exists(resources: list[Any], config_service: ResourceConfiguration) -> MetricCount:
    """
    Group resources by dictionary attribute.
    :param resources: List of resources
    :param config_service: Dictionary of service config
    :return: Dictionary of metric count for resources grouped by attribute
    """
    metric_name: str = config_service['metric']['metricName']
    element: str = config_service['count']['ifExists']['element']
    exists_suffix: str = config_service['count']['ifExists']['existsSuffix']
    not_exists_suffix: str = config_service['count']['ifExists']['notExistsSuffix']


    metric_count: MetricCount = {}
    metric_to_add: str = ''
    for resource in resources:
        # Define the metric name to add based on ifExists attribute value
        # If the attribute exists, add the metric name with the suffix from "existsSuffix" attribute
        # If the attribute does not exists, add the metric name with the suffix from "notExistsSuffix" attribute
        if element in resource:
            if resource[element]:
                logging.info('Attribute "%s" exists in resource, will use suffix "%s"', element, exists_suffix)
                metric_to_add = f'{metric_name}-{exists_suffix}'
            else:
                logging.info('Attribute "%s" exists in resource, but it is empty, will use suffix "%s"', element, not_exists_suffix)
                metric_to_add = f'{metric_name}-{not_exists_suffix}'
        else:
            logging.info('Attribute "%s" does not exist in resource, will use suffix "%s"', element, not_exists_suffix)
            metric_to_add = f'{metric_name}-{not_exists_suffix}'

        if metric_to_add not in metric_count:
            metric_count[metric_to_add] = 0
        metric_count[metric_to_add] += 1
    return metric_count

def get_groupby_attribute_value(dict_object: Any, group_by: list[str]) -> Any:
    """
    Recursive function to get the value of dictionary attribute.
    :param dict_object: Dictionary to iterate over 
    :param group_by: List of attributes to iterate over
    :return: Any
    """
    logging.info('group_by: %s', group_by)
    logging.info('Lenght of group_by: %s', len(group_by))
    logging.info('dict_object: %s', dict_object[group_by[0]])

    item = dict_object[group_by[0]]
    if len(group_by) > 1:
        logging.info('Call recursively')
        return get_groupby_attribute_value(item, group_by[1:])

    logging.info('Return value %s', dict_object[group_by[0]])
    return dict_object[group_by[0]]

def has_group_by(service_config: ResourceConfiguration) -> bool:
    """
    Check if service configuration has group_by attribute.
    :param service_config: Dictionary of service configuration
    :return: True if service configuration has group_by attribute, otherwise False
    """
    if CONST_GROUP_BY in service_config['count']:
        if CONST_ELEMENT in service_config['count']['groupBy']:
            if service_config['count']['groupBy']['element']:
                return True
    return False

def has_if_exists(service_config: ResourceConfiguration) -> bool:
    """
    Check if service configuration has ifExists attribute.
    :param service_config: Dictionary of service configuration
    :return: True if service configuration has ifExists attribute, otherwise False
    """
    if CONST_IF_EXISTS in service_config['count']:
        if CONST_ELEMENT in service_config['count']['ifExists']:
            if service_config['count']['ifExists']['element']:
                return True
    return False


#======================================================================================================================
# Main logic and helper functions
#======================================================================================================================
CONST_SERVICE_TYPE: Final[dict[str, Callable]] = {
    'paginator': list_from_paginator,
    'next-in-response': list_next_in_response,
    'direct': list_direct
}

def get_service_configuration() -> list[ResourceConfiguration]:
    """
    Read config file to get service configurations.
    :return: List of Dictionary of service configurations, just the valid ones
    """
    valid_config_services : list[ResourceConfiguration] = []

    # Read config file to get service configurations
    logging.info('Reading file "services.json"')
    with open(CONST_SERVICE_FILE, 'r', encoding='utf-8') as services_file:
        config_services : dict[str, Any] = json.load(services_file)
    logging.info('Found services: %s', config_services)

    for attribute in (CONST_DEFAULT_NAMESPACE, CONST_DEFAULT_DIMENSION_NAME, CONST_RESOURCES):
        if attribute not in config_services:
            logging.error('Attribute "%s" not found. Will ignore this file configuration.', attribute)
            break
    else:
        default_namespace: str = config_services[CONST_DEFAULT_NAMESPACE]
        default_dimension_name: str = config_services[CONST_DEFAULT_DIMENSION_NAME]

        # Get the list of service name available to be used with boto3
        valid_service_names: set[str] = set(boto3.Session().get_available_services())

        count: int = 0
        for resource in config_services[CONST_RESOURCES]:
            count += 1

            if validate_resource_configuration(resource, valid_service_names):
                service_type: str = str(resource['type']).lower()

                resource_count_element = CountElement(
                    generateTotal=True,
                    groupBy=GroupByElement(element=[], values=[], capitalize=True, customName=True),
                    ifExists=IfExistsElement(element='', existsSuffix='', notExistsSuffix='')
                )
                if CONST_COUNT in resource:
                    resource_count_element['generateTotal'] = resource[CONST_COUNT].get('generateTotal', True)
                    if CONST_GROUP_BY in resource[CONST_COUNT]:
                        resource_count_element['groupBy'] = GroupByElement(
                            element=resource[CONST_COUNT][CONST_GROUP_BY]['element'],
                            values=resource[CONST_COUNT][CONST_GROUP_BY].get('values', []),
                            capitalize=resource[CONST_COUNT][CONST_GROUP_BY].get('capitalize', True),
                            customName=resource[CONST_COUNT][CONST_GROUP_BY].get('customName', True)
                        )
                    if CONST_IF_EXISTS in resource[CONST_COUNT]:
                        resource_count_element['ifExists'] = IfExistsElement(
                            element=resource[CONST_COUNT][CONST_IF_EXISTS]['element'],
                            existsSuffix=resource[CONST_COUNT][CONST_IF_EXISTS]['existsSuffix'],
                            notExistsSuffix=resource[CONST_COUNT][CONST_IF_EXISTS]['notExistsSuffix']
                        )

                resource_config = ResourceConfiguration(
                    index=count,
                    type=service_type,
                    resource=ResourceElement(
                        client=resource['resource']['client'],
                        method=resource['resource']['method'],
                        kwargs=resource['resource'].get('kwargs', {}),
                        iterateOver=resource['resource']['iterateOver'],
                        nextInResponse=resource['resource'].get('nextInResponse', ''),
                        nextInRequest=resource['resource'].get('nextInRequest', ''),
                        mustExists=resource['resource'].get('mustExists', True)
                    ),
                    count=resource_count_element,
                    metric=MetricElement(
                        namespace=resource['metric'].get('namespace', default_namespace),
                        dimensionName=resource['metric'].get('dimensionName', default_dimension_name),
                        dimensionValue=resource['metric']['dimensionValue'],
                        metricName=resource['metric']['metricName']
                    )
                )
                valid_config_services.append(resource_config)
    return valid_config_services

def validate_resource_configuration(resource: Any, valid_service_names: set[str]) -> bool:
    """
    Validate resource configuration elements to verify required one and valid values.
    :param resource: Dictionary of service configuration
    :param valid_service_names: List of valid services name for boto3
    :return: Boolean to indicate if it is valid or not
    """
    for attribute in ('type', 'resource', 'metric'):
        if attribute not in resource:
            logging.error('Attribute "%s" not found. Will ignore this service configuration.', attribute)
            return False

    # Check if service type is a valid one
    if (service_type := str(resource['type']).lower()) not in CONST_SERVICE_TYPE:
        logging.error('Service type "%s" not valid, expecting one of "%s". Will ignore this service configuration.', service_type, sorted(CONST_SERVICE_TYPE.keys()))
        return False

    # Check if "resource" element has all required attributes
    for attribute in ('client', 'method', 'iterateOver'):
        if attribute not in resource['resource']:
            logging.error('Attribute "%s" not found. Will ignore this service configuration.', attribute)
            return False
    # Check if client is a valid one for boto3
    if (service_name := resource['resource']['client']) not in valid_service_names:
        logging.error('Invalid service name "%s". Will ignore this service configuration.', service_name)
        return False
    if service_type == CONST_NEXT_IN_RESPONSE:
        for attribute in ('nextInResponse', 'nextInRequest'):
            if attribute not in resource['resource']:
                logging.error('Attribute "%s" not found. It is mandatory as type is configured as "next-in-response". Will ignore this service configuration.', attribute)
                return False

    # Check if "metric" element has all required attributes
    for attribute in ('dimensionValue', 'metricName'):
        if attribute not in resource['metric']:
            logging.error('Attribute "%s" not found. Will ignore this service configuration.', attribute)
            return False

    return True

def instantiate_boto3_client_for_service(config_services: list[ResourceConfiguration]) -> Boto3Clients:
    """
    Instantiate boto3 client for each service configuration.
    :param config_services: Dictionary of service configurations
    :return: Dictionary of boto3 clients
    """
    clients: Boto3Clients = {}

    # Instantiate boto3 client for each service configuration.
    # The client attribute, which is the service name, must be a valid one for boto3,
    # otherwise it will raise an exception.
    # The valid ones are defined on variable "valid_service_names".
    for resource in config_services:
        if (service_name := resource['resource']['client']) not in clients:
            logging.info('Creating client for service: %s', service_name)
            clients[service_name] = boto3.client(service_name)
    logging.debug('Clients: %s', clients)
    return clients

def initialize_metrics_by_namespace(config_services: list[ResourceConfiguration]) -> Namespace:
    """
    Initialize metrics_by_namespace dictionary.
    :param config_services: List of Dictionary of service configurations
    :return: Dictionary of metrics_by_namespace
    """
    metrics_by_namespace : Namespace = {}

    for resource in config_services:
        if (namespace := resource['metric']['namespace']) not in metrics_by_namespace:
            logging.info('Initializing namespace: %s', namespace)
            metrics_by_namespace[namespace] = {}

    return metrics_by_namespace

def set_metrics_by_namespace(resources: list[Any], config_service: ResourceConfiguration, metrics_by_namespace: Namespace) -> None:
    """
    Set metrics_by_namespace dictionary from each resource.
    :param resources: List of resources
    :param config_service: Service configuration
    :param metrics_by_namespace: Dictionary of metrics_by_namespace
    """
    if resources:
        namespace: str = config_service['metric']['namespace']
        metric_count: dict[str, MetricData] = get_metric_count(resources, config_service)
        for metric_name, metric_value in metric_count.items():
            metrics_by_namespace[namespace][metric_name] = metric_value

def add_metric_to_cloudwatch(namespace: str, metrics: Metric) -> None:
    """
    Add metric to CloudWatch.
    :param namespace: Namespace of the metric
    :param metrics: Dictionary of metrics where key is the metric name
    """
    metric_data_batch: list[CloudWatchMetricDataList] = []
    metric_data_list: CloudWatchMetricDataList = []

    # Each PutMetricData request is limited to 1 MB in size for HTTP POST requests.
    # You can send a payload compressed by gzip.
    # Each request is also limited to no more than 1000 different metrics.
    # So, it is required to batch the metrics in no more than 1000 metrics!
    count: int = 0
    for metric_name, metric_data in metrics.items():
        logging.info('Adding metric %s: %s', metric_name, metric_data)
        metric_data_list.append(
            {
                'MetricName': metric_name,
                'Dimensions': [ {'Name': metric_data.dimension_name, 'Value': metric_data.dimension_value} ],
                'Timestamp': metric_data.timestamp,
                'Value': metric_data.metric_value,
                'Unit': 'Count',
                'StorageResolution': 60
            }
        )
        count +=1
        if count == CONST_MAX_METRIC_DATA:
            logging.info('Adding batch of metric data, count: %s', count)
            metric_data_batch.append(metric_data_list)
            metric_data_list = []
            count = 0
    # Add the remaining metric data list as a batch
    if metric_data_list:
        metric_data_batch.append(metric_data_list)

    logging.info('Length of metric_data_batch: %s', len(metric_data_batch))
    for batch in metric_data_batch:
        kwargs: dict[str, Any] = {
            'Namespace': namespace,
            'MetricData': batch
        }
        logging.info('put_metric_data %s: %s metrics', namespace, len(batch))
        cloudwatch_client.put_metric_data(**kwargs)

def main() -> Namespace:
    """
    Main function. To be called by lambda entry point or main entry point.
    :return: Dictionary of metrics by namespace
    """
    # Read config file to get service configurations
    config_services : list[ResourceConfiguration] = get_service_configuration()

    # Instantiate boto3 client for each service configuration.
    clients: Boto3Clients = instantiate_boto3_client_for_service(config_services)

    metrics_by_namespace: Namespace = initialize_metrics_by_namespace(config_services)

    # Get the list of resources for each service configuration
    for config_service in config_services:
        logging.info('#######################')
        logging.info(' ')

        service_type: str = config_service['type']
        resource_client: str = config_service['resource']['client']
        resource_method: str = config_service['resource']['method']

        resources: list[Any] = []
        logging.info('Get resources from "%s", "%s", using type "%s"', resource_client, resource_method, service_type)
        CONST_SERVICE_TYPE[service_type](clients, resources, config_service)

        namespace: str = config_service['metric']['namespace']
        logging.info('Set metrics for namespace "%s"', namespace)
        set_metrics_by_namespace(resources, config_service, metrics_by_namespace)

    logging.info('#######################')
    logging.info(' ')

    # Add metric to CloudWatch for each namespace
    for namespace, metrics in metrics_by_namespace.items():
        logging.info('Add metric to CloudWatch for namespace: %s', namespace)
        add_metric_to_cloudwatch(namespace, metrics)

    return metrics_by_namespace


#======================================================================================================================
# Lambda entry point
#======================================================================================================================

def lambda_handler(event, context) -> Namespace:
    """Lambda function handler"""
    logging.info('lambda_handler start')
    logging.debug('Parameter event: %s', json.dumps(event))
    logging.debug('Parameter context: %s', context)

    try:
        return_value: Namespace = main()
    except Exception as error:
        logging.exception(error)
        raise error

    logging.info('Function return: %s', return_value)
    logging.info('lambda_handler end')
    return return_value


# Used to run and validate lambda locally
if __name__ == '__main__':
    print(lambda_handler({}, None))
