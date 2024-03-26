## AWS resource counter

This project creates Amazon CloudWatch metric for configured resources using AWS Lambda that is scheduled recurrence.  
You can configure which resources you would like to count and Lambda function will generate the metric based on your current resources count.  
It will allow you to keep track of your resource numbers and also generate alarm using CloudWatch alarm.  
Including [anomaly detection](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Anomaly_Detection.html) alarm, which can be used to alarm you when your AWS resources usage is different from your baseline.

Metrics are created in the region where the CloudFormation stack is created.

![CloudWatch metrics Custom Namespace](/doc/ResourceCounter-CustomNamespace.png)

![CloudWatch metrics dimension](/doc/ResourceCounter-Dimension.png)

![CloudWatch metrics](/doc/ResourceCounter-Metrics.png)

## Overview

The CloudFormation template `cloudformation/template.yml` creates a stack with the following resources:

1. AWS Lambda function with customizable config file called `services.json`. The function's code is in `lambda/resource_counter.py` and is written in Python compatible with version 3.12.
1. Lambda function's execution role.
1. Amazon EventBridge schedule to execute Lambda function.

![Architecture](/doc/ResourceCounter.png)

## Supported resources

It supports all resources that can be used via [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/index.html)

> **NOTE**  
> If you miss some AWS resource that should be supported, feel free to open an issue or contribute with a pull request.  
> 
> It will create CloudWatch metrics, but it will NEVER remove it after it is created.  
> As soon it is created it can only be removed waiting CloudWatch metrics retention policy.
>
> Check question **Q: What is the retention period of all metrics?** on link below.  
> https://aws.amazon.com/cloudwatch/faqs/


### Considerations

* Lambda code MUST have a config file called `services.json` in the root path. See below more details about file format.
* It will only create metrics for AWS services that has some resource. It will NOT create metrics with zero value!


> **NOTE ABOUT REGIONS DEPLOY**  
> There is no reason to deploy this solution twice inside the same region.  
> If you have a reason for doing it, please open an issue and let's talk about it.

## Lambda configuration

To configure which resource lambda function should count, you need to change the file `services.json`.

This repository already has a file configured with 50+ resources to count.
You don't need to change the file to just see the project deployed and metrics on CloudWatch.

For more details, check [how to use `services.json`](/configuration.md) configuration file.

**ROUTE PROPAGATION**  
If you want to monitor and alarm route propagation from AWS Direct Connect and/or AWS Site-to-Site VPN, check [how to configure it](/route-propagation.md).


## Setup

These are the overall steps to deploy:

**Setup using CloudFormation**
1. Validate CloudFormation template file.
1. Create the CloudFormation stack.
1. Package the Lambda code into a `.zip` file.
1. Update Lambda function with the packaged code.

**After setup**
1. Trigger a test Lambda invocation.
1. Clean-up





## Setup using CloudFormation
To simplify setup and deployment, assign the values to the following variables. Replace the values according to your deployment options.

```bash
export AWS_REGION="sa-east-1"
export CFN_STACK_NAME="resource-counter"
```

> **IMPORTANT:** Please, use AWS CLI v2

### 1. Validate CloudFormation template

Ensure the CloudFormation template is valid before use it.

```bash
aws cloudformation validate-template --template-body file://cloudformation/template.yml
```

### 2. Create CloudFormation stack

At this point it will create Lambda function with a dummy code.  
You will update it later.

```bash
aws cloudformation create-stack --stack-name "${CFN_STACK_NAME}" \
  --capabilities CAPABILITY_IAM \
  --template-body file://cloudformation/template.yml && {
    ### Wait for stack to be created
    aws cloudformation wait stack-create-complete --stack-name "${CFN_STACK_NAME}"
}
```

If the stack creation fails, troubleshoot by reviewing the stack events. The typical failure reasons are insufficient IAM permissions.

### 3. Create the packaged code

Before you package it, please change `lambda/services.json` file according to your requirement. For more information read the section `Lambda configuration` above.

```bash
zip --junk-paths lambda.zip lambda/resource_counter.py lambda/services.json
```

### 4. Update lambda package code

```bash
FUNCTION_NAME=$(aws cloudformation describe-stack-resources --stack-name "${CFN_STACK_NAME}" --query "StackResources[?LogicalResourceId=='LambdaFunction'].PhysicalResourceId" --output text)
aws lambda update-function-code --function-name "${FUNCTION_NAME}" --zip-file fileb://lambda.zip --publish
```

> **NOTE**  
> Every time you change Lambda function configuration file `services.json` you need to execute steps 3 and 4 again.  
> You also need to confirm if Lambda execution role has the correct permission to execute the methods defined on configuration file.


## After setup

### 1a. Trigger a test Lambda invocation with the AWS CLI

After the stack is created, AWS resources are not created or updated until a new SNS message is received. To test the function and create or update AWS resources with the current IP ranges for the first time, do a test invocation with the AWS CLI command below:

**CloudFormation**
```bash
aws lambda invoke --function-name "${FUNCTION_NAME}" lambda_return.json
```

After successful invocation, you should receive the response below with no errors.

```json
{
    "StatusCode": 200,
    "ExecutedVersion": "$LATEST"
}
```

The content of the `lambda_return.json` will list all CloudWatch metrics created/updated.

### 1b. Trigger a test Lambda invocation with the AWS Console

Alternatively, you can invoke the test event in the AWS Lambda console with sample event below.

```json
{ }
```

### 2. Clean-up

Remove the temporary files and remove CloudFormation stack.

**CloudFormation**  
```bash
rm lambda.zip
rm lambda_return.json
aws cloudformation delete-stack --stack-name "${CFN_STACK_NAME}"
unset AWS_REGION
unset CFN_STACK_NAME
```


> **ATTENTION**  
> When you remove CloudFormation stack, it will NOT remove CloudWatch metrics created by this solution.  
> If you want to remove it, you need to wait until CloudWatch metrics retention policy time.

## Lambda function customization

After the stack is created, you can customize the Lambda function's execution log level by editing the function's [environment variables](https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html).

* `LOG_LEVEL`: **Optional**. Set log level to increase or reduce verbosity. The default value is `INFO`. Possible values are:
  * CRITICAL
  * ERROR
  * WARNING
  * INFO
  * DEBUG

## Troubleshooting

**Wrong WAF IPSet Scope**

> An error occurred (WAFInvalidParameterException) when calling the ListIPSets operation: Error reason: The scope is not valid., field: SCOPE_VALUE, parameter: CLOUDFRONT

Scope name `CLOUDFRONT` is correct, but it MUST be running on North Virginia (us-east-1) region. If it runs outside North Virginia, you will see the error above.  
Please make sure it is running on North Virginia (us-east-1) region.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
