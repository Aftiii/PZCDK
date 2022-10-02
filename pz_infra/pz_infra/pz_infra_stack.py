from aws_cdk import (
    # Duration,
    Stack,
    aws_ec2
    # aws_sqs as sqs,
)
from constructs import Construct
import boto3

class PzInfraStack(Stack):


    public_key_name = 'ec2_rsa'
    instance_name = 'pz_instance' 
    instance_type = 't3.large'
    ssm_param = '/aws/service/canonical/ubuntu/server/jammy/stable/current/amd64/hvm/ebs-gp2/ami-id'

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        with open('ec2_rsa.pub') as file:
            public_key = file.read()

        ec2 = boto3.client('ec2')
        existingKeyPairs = ec2.describe_key_pairs(KeyNames=[self.public_key_name])

        #Only create the key if it doesn't exist
        if len(existingKeyPairs.keys()) == 0:
            ec2.import_key_pair(KeyName=self.public_key_name,PublicKeyMaterial=public_key,TagSpecifications=[{'ResourceType':'key-pair','Tags':[{'Key':'purpose','Value':'ec2_auth'}]}])

        image = aws_ec2.MachineImage.from_ssm_parameter(parameter_name=self.ssm_param,os=aws_ec2.OperatingSystemType.LINUX)

        vpc = aws_ec2.Vpc(self, 'pz-cdk-vpc',
            cidr='10.0.0.0/16',
            nat_gateways=0,
            subnet_configuration=[aws_ec2.SubnetConfiguration(name='public', cidr_mask=24, subnet_type=aws_ec2.SubnetType.PUBLIC)])

        sshIngress = aws_ec2.SecurityGroup(self, id='ssh-sg', security_group_name='ssh-sg', vpc=vpc, allow_all_outbound=True)
        sshIngress.add_ingress_rule(aws_ec2.Peer.any_ipv4(), aws_ec2.Port.tcp(22), 'ssh')

        pzIngress = aws_ec2.SecurityGroup(self, id='pz-sg', security_group_name='pz-sg', vpc=vpc, allow_all_outbound=True)
        pzIngress.add_ingress_rule(aws_ec2.Peer.any_ipv4(), aws_ec2.Port.udp(8766), 'PZ Connect 1')
        pzIngress.add_ingress_rule(aws_ec2.Peer.any_ipv4(), aws_ec2.Port.udp(16261), 'PZ Connect 2')

        instance_type = aws_ec2.InstanceType(self.instance_type)

        ec2_instance = aws_ec2.Instance(self, 'pz_instance', instance_name=self.instance_name, instance_type=instance_type, machine_image = image, vpc=vpc, key_name=self.public_key_name)
        ec2_instance.add_security_group(sshIngress)
        ec2_instance.add_security_group(pzIngress)

