import os
import boto3
import requests

REGION = os.getenv('ES_REGION')  # Replace with your ES region
ES_DOMAIN_NAME = os.getenv('ES_DOMAIN_NAME')  # Replace with your ES domain name
ES_URI = os.getenv('ES_URI')  # Replace with your ES URI
es_client = boto3.client('es', REGION)
min_instance_count = 3
max_instance_count = 6
min_replicas_count = 1


def change_number_of_index_replicas(index_alias: str, replicas_count: int, elastic_uri: str):
    try:
        response = requests.put(
            f'{elastic_uri}/{index_alias}/_settings',
            json={"index": {
                "number_of_replicas": replicas_count
            }})
        response.raise_for_status()
    except Exception as e:
        raise Exception(
            f'An error occurred while increasing {index_alias} replicas', e)


def change_instance_and_replicas_count(instance_count: int, scale_type: str):
    instance_change_value = 1 if (instance_count <= 4 or instance_count % 2 == 0) else 2
    if scale_type == 'scale_up':
        new_instance_count = max_instance_count
    else:
        new_instance_count = instance_count - instance_change_value
        new_instance_count = min(new_instance_count, max_instance_count)  # Ensure it doesn't go below min_instance_count
    balanced_replicas_count = int((new_instance_count / 2) - 1)
    new_replicas_count = min_replicas_count if balanced_replicas_count < min_replicas_count else balanced_replicas_count
    return new_instance_count, new_replicas_count


def get_ebs_config(ebs_options):
    if ebs_options['EBSEnabled'] == False:
        return {'EBSEnabled': False}
    else:
        return ebs_options


def scale_cluster_instance_count(domain_config: dict, dry_run: bool) -> dict:
    vpc_options = domain_config.get('VPCOptions', {}).get('Options', {})
    print(f"VPC Options: {vpc_options}")
    return es_client.update_elasticsearch_domain_config(
        DomainName=ES_DOMAIN_NAME,
        ElasticsearchClusterConfig=domain_config['ElasticsearchClusterConfig']['Options'],
        EBSOptions=get_ebs_config(domain_config['EBSOptions']['Options']),
        SnapshotOptions=domain_config['SnapshotOptions']['Options'],
        VPCOptions={
            'SubnetIds': vpc_options.get('SubnetIds', []),
            'SecurityGroupIds': vpc_options.get('SecurityGroupIds', [])
        },
        # ... other options ...
        DryRun=dry_run
    )


def scale_es_domain_and_replicas(scale_type: str):
    try:
        domain_config = es_client.describe_elasticsearch_domain_config(
            DomainName=ES_DOMAIN_NAME)['DomainConfig']
        domain_state = domain_config['ElasticsearchVersion']['Status']['State']
        
        if domain_state == 'Active':
            instance_count = domain_config['ElasticsearchClusterConfig']['Options']['InstanceCount']
            
            # Check if VPCOptions is present in domain_config and contains 'Options'
            vpc_options = domain_config.get('VPCOptions', {}).get('Options', {})
            
            if not vpc_options:
                print("VPC Options not present. Ensure your domain is created with VPC options.")
                return "VPC Options not present. Ensure your domain is created with VPC options."
            
            print(f"VPC Options: {vpc_options}")
            
            if instance_count <= min_instance_count and scale_type == 'scale_down':
                print(f'Cannot scale down to fewer than {min_instance_count} nodes.')
                return f'Cannot scale down to fewer than {min_instance_count} nodes.'
            else:
                if scale_type == 'scale_up':
                    new_instance_count, new_replicas_count = change_instance_and_replicas_count(instance_count, scale_type)
                else:
                    # Scale down to 3 instances
                    new_instance_count, new_replicas_count = 3, min_replicas_count
                
                domain_config['ElasticsearchClusterConfig']['Options']['InstanceCount'] = new_instance_count
                # Test config with dry run
                dry_run_response = scale_cluster_instance_count(domain_config, dry_run=True)
                print(f'Dry run completed: {dry_run_response}')
                
                if dry_run_response['DryRunResults']['DeploymentType'] != 'None':
                    # Scale number of data nodes
                    scale_cluster_instance_count(domain_config, dry_run=False)
                    # Comment out or remove the following line
                    # scale_all_index_replicas(new_replicas_count)
                else:
                    raise Exception('Dry run error', dry_run_response['DryRunResults']['Message'])
        else:
            print(f'Skipping scaling because domain state is {domain_state}')
            return f'Skipping scaling because domain state is {domain_state}'
    except Exception as e:
        raise Exception(f'An error occurred while running cluster {scale_type}', e)
        return f'An error occurred while running cluster {scale_type}: {e}'


# Add the following handler
def lambda_handler(event, context):
    scale_type = event.get('scale_type', 'scale_up')  # default to 'scale_up' if not provided in event
    
    if scale_type not in ['scale_up', 'scale_down']:
        print(f'Invalid scale_type: {scale_type}. Valid values are "scale_up" or "scale_down".')
        return f'Invalid scale_type: {scale_type}. Valid values are "scale_up" or "scale_down".'
    
    result = scale_es_domain_and_replicas(scale_type)
    print(result)
    return result
