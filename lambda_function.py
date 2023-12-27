import json
import os
import urllib3
import boto3


http = urllib3.PoolManager()


HOOK_URL=os.getenv('HOOK_URL')
CHANNEL_NAME=os.getenv('CHANNEL_NAME')
SESSION_KEY={
    "aws_access_key_id":"",
        "aws_secret_access_key":"",
        "aws_session_token":""
    
}

def get_ssm_parameters(accountId):
    ssm_client = boto3.client('ssm');
    svc_name=ssm_client.get_parameters(Names=['SERVICE_NAME'])['Parameters'];
    
    value=svc_name[0]['Value']
# using json.loads()
# convert dictionary string to dictionary
    res = json.loads(value)
    
    return res[accountId]

def get_ssm_parameters_role(accountId):
    ssm_client = boto3.client('ssm');
    chnl_name=ssm_client.get_parameters(Names=['CW_IAM_ROLE_ARN'])['Parameters'];
    value=chnl_name[0]['Value']
    # using json.loads()
    # convert dictionary string to dictionary
    res = json.loads(value)
    print("IAM_ROLE_ARN : "+res[accountId])
    return res[accountId]
    

def get_session(accountId):
    sts_client=boto3.client('sts');
    #get session to target aws account.
    response = sts_client.assume_role(
        RoleArn=get_ssm_parameters_role(accountId),
        RoleSessionName="temp-session"
        )
    #set aws access config
    SESSION_KEY["aws_access_key_id"]=response['Credentials']['AccessKeyId']
    SESSION_KEY["aws_secret_access_key"]=response['Credentials']['SecretAccessKey']
    SESSION_KEY["aws_session_token"]=response['Credentials']['SessionToken']


def get_ec2_name(accountId, instanceId):
    get_session(accountId);
    

    ec2_client=boto3.client('ec2',  aws_access_key_id=SESSION_KEY["aws_access_key_id"],
        aws_secret_access_key=SESSION_KEY["aws_secret_access_key"],
        aws_session_token=SESSION_KEY["aws_session_token"]
    )
    
    
    ec2_info=ec2_client.describe_instances(InstanceIds=[instanceId.split("/")[-1]])
    for tags in ec2_info['Reservations'][0]['Instances'][0]['Tags']:
            if tags['Key'] == 'Name':
                print(tags['Value'])
                return tags['Value']
    


def lambda_handler(event, context):

  print(json.dumps(event));
  
  #resource_name=get_ec2_name(event['account'],event['detail']['resourceArn'].split(":")[-1]);
  #msg=json.loads(event['Records'][0]['Sns']['Message'])
  #print(resource_name)

  if event['detail']['state'] == "FAILED":
      slack_msg= {
            'attachments': [
                {
                'color' : "danger",
                    'title': ":AWS Backup FAILED :",
                    'fields': [
                        {
                            "title": "Account",
                            "value": get_ssm_parameters(event['account'])
                        },

                        {
                            "title": "Resource Type",
                            "value": event['detail']['resourceType']
                        },

                        {
                            "title": "Resource ID",
                            "value": event['detail']['resourceArn'].split(":")[-1]
                        },
                        {
                            "title": "Resource Name",
                            "value": get_ec2_name(event['account'],event['detail']['resourceArn'].split(":")[-1])
                        },                                                
                        {
                            "title": "State",
                            "value": event['detail']['state']
                        },
                        {
                            "title": "Desc",
                            "value": event['detail']['statusMessage']
                        }                        
                    ]
                }
            ]
        }
  elif event['detail']['state'] == "COMPLETED":
      slack_msg= {
            'attachments': [
                {
                    'color' : "good",
                    'title': ":AWS Backup COMPLETED :",
                    'fields': [
                        {
                            "title": "Account",
                            "value": get_ssm_parameters(event['account'])
                        },

                        {
                            "title": "Resource Type",
                            "value": event['detail']['resourceType']
                        },

                        {
                            "title": "Resource ID",
                            "value": event['detail']['resourceArn'].split(":")[-1]
                        },
                        {
                            "title": "Resource Name",
                            "value": get_ec2_name(event['account'],event['detail']['resourceArn'].split(":")[-1])
                        },                        
                        {
                            "title": "State",
                            "value": event['detail']['state']
                        },
                        {
                            "title": "CompletionDate",
                            "value": event['detail']['completionDate']
                        }                        
                    ]
                }
            ]
        }

  encoded_msg = json.dumps(slack_msg).encode("utf-8")
  
  print(encoded_msg)
  resp = http.request("POST", HOOK_URL, body=encoded_msg)



  return {
		'body': encoded_msg
	}
