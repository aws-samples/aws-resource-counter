# Lambda configuration

To configure which resource lambda function should count, you need to change the file `services.json`.  
JSON file doesn't support comments, so you can use YAML file `services.yaml` to configure your resources to count and convert it to JSON using the command below.

Convert YAML file to JSON:

```shell
# YAML to JSON
cat lambda/services.yaml | python3 -c 'import sys, yaml, json; json.dump(yaml.safe_load(sys.stdin), sys.stdout, indent=4)' >lambda/services.json
```

> **ATTENTION**  
> Lambda function only works with `services.json` file. It doesn't support YAML file directly.  
> YAML file only exists to facilitate configuration and documentation, as you can comment on it.  
> You always need to convert YAML file to JSON after you change your configuration on YAML file.

See below the file structure commented. Please check `lambda/services.yaml` file for a comprehensive example of configuration for several services.

```yaml
# CloudWatch namespace to be used by all metrics.
# This namespace can be overwiten by each resource configuration below. If it is not configured on resource, it will use this one.
# It is mandatory! If this attribute is missing on file it will ignore the entire file.
defaultNamespace: ResourceCounter

# CloudWatch dimension name to be used by all metrics.
# This dimension name can be overwiten by each resource configuration below. If it is not configured on resource, it will use this one.
# It is mandatory! If this attribute is missing on file it will ignore the entire file.
defaultDimensionName: Per-Service Metrics

# List of AWS resources to count.
# It is mandatory! If this attribute is missing on file it will ignore the entire file.
resources:

# The type of this AWS resource configuration. The value can be one of: 'paginator', 'next-in-response', 'direct'.
# Value is not case sensitive!
# It is mandatory! If this attribute is missing on file it will ignore just this resource configuration, not the entire file.
- type: paginator

  # The resource configuration related with the type above.
  # It is mandatory! If this attribute is missing on file it will ignore just this resource configuration, not the entire file.
  resource:

    # Boto3 service name to be used to instantiate a client for this specifi service. It must be a valid one for boto3.
    # You can use boto3 to get the complete list of valid service names, or check the file "lambda/services.txt".
    # Value is case sensitive!
    # It is mandatory! If this attribute is missing on file, or has the wrong value, it will ignore just this resource configuration, not the entire file.
    client: ec2

    # Boto3 method from service defined on "client" above. The result of this method is the one that will be counter, based on the rules defined on "count" element below.
    # Please, use boto3 documentation to get the correct method name.
    # Value is case sensitive!
    # It is mandatory! If this attribute is missing on file, or empty, it will ignore just this resource configuration, not the entire file.
    #
    # If "type" above is defined as "paginator", you can only use boto3 methods that supports pagination.
    # If "type" above is defined as "next-in-response", you can only use boto3 methods that supports "next" attribute on request and response.
    #    Attributes "nextInResponse" and "nextInRequest" are mandatory with this type configuration. Otherwise they are optional.
    # If "type" above is defined as "direct", you can use any boto3 method. It will consider only the resources returned in one request to this boto3 method.
    method: describe_instances

    # Boto3 method arguments to be informed. It doesn't support dynamic arguments, only static ones.
    # Value is case sensitive!
    # Use the correct arguments to the method defined above. Please check boto3 documentation.
    # It is optional! But it cannot be null, so define it as empty dictionary, like "{}" or just remove it from configuration.
    kwargs: {}

    # List of strings with attributes from Boto3 method response to be used to iterate and count.
    # It must be an List attribute to interate over. It will iterate on the order specified.
    # Value is case sensitive!
    iterateOver: [Reservations, Instances]

    # Boto3 "next" attribute inside method response to check if there is more resources to fetch.
    # If "type" is defined as "next-in-response" and method response has this attribute defined with a non-empty value, it will perform "next" requests until this attribute is missing or have an empty value.
    # Value is case sensitive!
    # It is mandatory if type is defined as "next-in-response"! Otherwise it is optional.
    # If it is required and this attribute is missing on file, or has empty value, it will ignore just this resource configuration, not the entire file.
    nextInResponse: 'NextMarker'

    # Boto3 "next" attribute inside method request to fetch more resources if required.
    # If "type" is defined as "next-in-response" and method response has attribute "nextInResponse" defined above, it will perform "next" requests with this argument appended to "kwargs" ones.
    # Value is case sensitive!
    # It is mandatory if type is defined as "next-in-response"! Otherwise it is optional.
    # If it is required and this attribute is missing on file, or has empty value, it will ignore just this resource configuration, not the entire file.
    nextInRequest: 'NextMarker'

    # Boolena value to indicate if Boto3 "iterateOver" attributes inside method response must exists or not.
    # Some boto3 methods doesn't return anything when there is no resources available. When the common behavior is to have an empty return.
    # It is optional! The default value is "true".
    mustExists: false

  # The count configuration related with the "resource" above.
  # It is optional! If it is not defined it will assume all default values.
  count:

    # Boolean value to indicate if it shoud generate a total count metric for this resource or not.
    # It is optional! The default value is "true".
    generateTotal: true

    # Configuration to indicate if it should generate count metric based on group of attributes and/or values.
    # It is optional! If it is not defined it will assume the default values.
    groupBy:

      # List of strings with attribute names inside "method" response to group and generate metric.
      # It will group only on values from the last element from this list. All the other ones previously must represent and response object.
      # Value is case sensitive!
      # It is mandatory if "groupBy" element above is defined
      #
      # The metric name will be the one defined on attribute "metricName" below with a suffix that is the value from this "element" attribute.
      # Like, "element: [State]" and "metricName: Instance"  has a value "running", metric name will be "Instance-Running".
      element: [State, Name]

      # List of strings with attribute values from "method" response "element" above.
      # It will group only on values defined in this list.
      # If this configuration in non-empty, it will group based on the values defined and count them, otherwise it will ignore the resource and will not count it.
      # Value is case sensitive!
      # It is optional! If not defined it will group and count based on all values from "element" above.
      values: [running, terminated, stopped]

      # Boolean value to indicate if it shoud capitalize the attribute value define above on "element".
      # It is optional! The default value is "true".
      # Examples: "AVAILABLE" -> "Available", "in-use" -> "In-use"
      capitalize: true

    # Configuration to indicate if it should generate count metric based if some attribute exists or not.
    # It is optional! If it is not defined it will assume the default values.
    ifExists:

      # Attribute names inside "method" response to generate metric and count.
      # If this attribute exists in the "method" response and the value is the one that Python checks as "True" in a "IF" condition, than it will count.
      # Value is case sensitive!
      # It is mandatory if "ifExists" element above is defined
      #
      # If Python understand the attribute value as "True", metric name will be the one defined on attribute "metricName" below with "existsSuffix" suffix.
      # If Python understand the attribute value as "False", metric name will be the one defined on attribute "metricName" below with "notExistsSuffix" suffix.
      element: EbsOptimized

      # Suffix to be used on "metricName" if "element" above exists on "method" response.
      # It is mandatory if "ifExists" element above is defined
      existsSuffix: EBS-optimized

      # Suffix to be used on "metricName" if "element" above doesn't exists on "method" response.
      # It is mandatory if "ifExists" element above is defined
      notExistsSuffix: EBS-not-optimized

  # The metric configuration related with the "resource" above.
  # It is mandatory! If this attribute is missing on file it will ignore just this resource configuration, not the entire file.
  metric:

    # CloudWatch metric namespace to be used when create/update metric.
    # It is optional! If not defined it will use "defaultNamespace" above.
    namespace: 'ResourceCounter'

    # CloudWatch metric dimension name to be used when create/update metric.
    # It is optional! If not defined it will use "defaultDimensionName" above.
    dimensionName: 'Per-Service Metrics'

    # CloudWatch metric dimension value to be used when create/update metric.
    # It is mandatory! If this attribute is missing on file, or empty, it will ignore just this resource configuration, not the entire file.
    dimensionValue: EC2

    # CloudWatch metric name to be used when create/update metric.
    # It is mandatory! If this attribute is missing on file, or empty, it will ignore just this resource configuration, not the entire file.
    metricName: Instance
```

Example:

```yaml
defaultNamespace: ResourceCounter
defaultDimensionName: Per-Service Metrics
resources:
## EC2
- type: paginator
  resource:
    client: ec2
    method: describe_instances
    iterateOver: [Reservations, Instances]
  count:
    groupBy:
      element: [State, Name]
      values: [running, terminated, stopped]
  metric:
    dimensionValue: EC2
    metricName: Instance

- type: paginator
  resource:
    client: ec2
    method: describe_images
    kwargs:
      Owners:
        - self
    iterateOver: [Images]
  count:
    groupBy:
      element: [State]
  metric:
    dimensionValue: EC2
    metricName: Image

- type: direct
  resource:
    client: ec2
    method: describe_addresses
    iterateOver: [Addresses]
  count:
    ifExists:
      element: AssociationId
      existsSuffix: In-use
      notExistsSuffix: Available
  metric:
    dimensionValue: EC2
    metricName: Elastic-IP

## WAFv2
- type: next-in-response
  resource:
    client: wafv2
    method: list_web_acls
    kwargs:
      Scope: REGIONAL
    iterateOver: [WebACLs]
    nextInRequest: NextMarker
    nextInResponse: NextMarker
  metric:
    dimensionValue: WAFv2
    metricName: WebACL
```
