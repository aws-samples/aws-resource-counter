# Route propagation metrics from AWS Direct Connect and AWS Site-to-Site VPN

On a hybrid environment customer announce route prefix from on-premise to AWS using AWS Direct Connect (DX) and/or AWS Site-to-Site VPN (VPN).  
Each service has BGP quotas, like [AWS Direct Connect](https://docs.aws.amazon.com/directconnect/latest/UserGuide/limits.html), [AWS Site-to-Site VPN](https://docs.aws.amazon.com/vpn/latest/s2svpn/vpn-limits.html).  
If customer announce more routes than it is allowed, BGP turns down.

With this solution you can have a Cloud Watch Metric for each type of BGP propagation and create alarm with some specific threshold to be aware when you are reaching the allowed quota.

As all configurations below requires some specific `route table id` that belong to customer environment, I did add if by default on this solution configuration.  
So, please, change the configuration to your specific `route table id`.

## VPN and Private VIF with Virtual Private Gateway (VGW)

With this configuration it will count all routes propagated inside route table that has [route propagation enable](https://docs.aws.amazon.com/vpc/latest/userguide/WorkWithRouteTables.html#EnableDisableRouteProp).

You will not be able to distinct routes propagated via VPN or via Direct Connect Private VIF, because they are all tied to VGW.

```yaml
- type: paginator
  resource:
    client: ec2
    method: describe_route_tables
    kwargs:
      RouteTableIds:
        - rtb-abcde12345
    iterateOver: [RouteTables, Routes]
  count:
    generateTotal: false
    groupBy:
      element: [Origin]
      values: [EnableVgwRoutePropagation]
      customName: false
  metric:
    dimensionValue: VPC
    metricName: RouteTable-Routes-VGW
```

## VPN and Transit VIF with AWS Transit Gateway (TGW)

With this configuration it will count all routes propagated inside specific TGW route table from Site-to-Site VPN.

```yaml
- type: direct
  resource:
    client: ec2
    method: search_transit_gateway_routes
    kwargs:
      TransitGatewayRouteTableId: tgw-rtb-abcde12345
      Filters:
        - Name: state
          Values:
            - active
            - blackhole
        - Name: type
          Values:
            - propagated
        - Name: attachment.resource-type
          Values:
            - vpn
    iterateOver: [Routes]
  metric:
    dimensionValue: VPC
    metricName: TransitGateway-Routes-VPN
```

With this configuration it will count all routes propagated inside specific TGW route table from Direct Connect Gateway, where Transit VIF is attached.

```yaml
- type: direct
  resource:
    client: ec2
    method: search_transit_gateway_routes
    kwargs:
      TransitGatewayRouteTableId: tgw-rtb-abcde12345
      Filters:
        - Name: state
          Values:
            - active
            - blackhole
        - Name: type
          Values:
            - propagated
        - Name: attachment.resource-type
          Values:
            - direct-connect-gateway
    iterateOver: [Routes]
  metric:
    dimensionValue: VPC
    metricName: TransitGateway-Routes-DX
```
