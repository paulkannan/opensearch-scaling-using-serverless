# opensearch-scaling-using-serverless
Scaling of Opensearch cluster using AWS Serverless services
This is a reference code to scale managed OpenSearch AWS clusters using CloudWatch, Eventbridge and Lambda. Based on the CPU utilisation threshold, Cloudwatch alarm will get triggered which will in turn trigger Eventbridge rule. If the event pattern matches, eventbridge rule will trigger Lambda which will scaleup/down OpenSearch clusters.
