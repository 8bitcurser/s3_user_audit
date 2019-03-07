from json import loads
from argparse import ArgumentParser

from boto3 import client

parser = ArgumentParser()
parser.add_argument('--bucket', help='S3 Bucket name')
parser.add_argument(
    '--full-access', help='Users that have full access at S3',
    action='store_true'
)
args = parser.parse_args()

iam = client('iam')
s3 = client('s3')

entity_names = [[], [],  [], []]


def name_obtainer(policies, entity_names):
    """Given a list of entities obtain the names of each one of them.
    policies -- list of policies.
    entity_names -- 4th dimension list
    """
    for pol in policies:
        res = iam.list_entities_for_policy(
            PolicyArn=pol[1],
            MaxItems=900
        )
        for pol in res:
            if 'Policy' in pol:
                for entity in res[pol]:
                    if 'Groups' in pol:
                        entity_names[0].append(entity['GroupName'])
                    elif 'Roles' in pol:
                        entity_names[1].append(entity['RoleName'])
                    elif 'Users' in pol:
                        entity_names[2].append(entity['UserName'])
                    else:
                        pass
    return entity_names


if args.full_access:
    policies_usr = iam.list_policies(Scope='All', MaxItems=1000)['Policies']
    policies = [(policy['PolicyName'], policy['Arn'])
                for policy in policies_usr]
    s3_policies = []
    for pol in policies:
        if 'S3FullAccess' in pol[0]:
            s3_policies.append(pol)
    s3_users = []
    users = iam.list_users()['Users']
    names = name_obtainer(s3_policies, entity_names)
    for group in names[0]:
        users = iam.get_group(
            GroupName=group,
            MaxItems=900,
        )['Users']
        for user in users:
            names[2].append(user['UserName'])

    print(('== Entities with s3 full access ==\nGroups: {}\n'
          'Roles: {}\nUsers: {}'.format(names[0], names[1], names[2])))
else:
    accounts = []
    bck_policy = s3.get_bucket_policy(Bucket=args.bucket)['Policy']
    policy = loads(bck_policy)

    for stm in policy['Statement']:
        if type(stm['Principal']['AWS']).__name__ == 'list':
            accounts.extend(stm['Principal']['AWS'])
        else:
            accounts.append(stm['Principal']['AWS'])
    accounts = list(set(accounts))

    for acc in accounts:
        if ':user/' in acc:
            entity_names[0].append(acc)
        elif ':role/' in acc:
            entity_names[1].append(acc)
        elif ':group/' in acc:
            entity_names[2].append(acc)
        else:
            entity_names[3].append(acc)

    for group in entity_names[2]:
        group_name = group.split('/')[-1]
        users = iam.get_group(
            GroupName=group_name,
            MaxItems=600,
        )['Users']
        for user in users:
            entity_names[0].append(user['Username'])

    users = list(set(entity_names[0]))

    print(
        ('== Bucket Name: {0} ==\nPolicy: {1}'
         '\nUsers: {2}\nRoles: {3}\nGroups: {4}\nOthers: {5}'
         .format(
             args.bucket, policy['Id'], users, entity_names[1],
             entity_names[2], entity_names[3]
            ))
    )
