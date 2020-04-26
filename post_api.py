from flask import Flask, jsonify, request
# from flask import request, jsonify, g, current_app

# fix for local dynamodb creating duplicate tables at once cause of UTC timezone issues
import os

os.environ["TZ"] = "UTC"

import boto3
import datetime
import json
# from flask_dynamo import Dynamo
from boto3.dynamodb.conditions import Key, Attr

######################
# References

######################
# GLOBALS
TABLENAME = 'posts'
app = Flask(__name__)

# flask config variables
app.config['DEBUG'] = True

# dynamodb config variables
app.config['AWS_ACCESS_KEY_ID'] = 'fakeMyKeyId'
app.config['AWS_SECRET_ACCESS_KEY'] = 'fakeSecretAccessKey'
app.config['AWS_REGION'] = 'us-west-2'
app.config['DYNAMO_ENABLE_LOCAL'] = True
app.config['DYNAMO_LOCAL_HOST'] = 'localhost'
app.config['DYNAMO_LOCAL_PORT'] = 8000
#

# dynamodb using boto3
# boto3 client (low level api)
# boto3 resource (high level api)
# using a high level api is preferred
######################
# boto3 globals
client = boto3.client('dynamodb', endpoint_url='http://localhost:8000')

######################
# remove attribute type from json
remove_type = lambda x: [{i: j[i]['S'] for i in list(j.keys())} for j in x]

# sort json using a key
sort_json = lambda x: sorted(x, key=lambda y: y['published'])


# helper function to generate a response with status code and message
def get_response(status_code, message):
    return {"status_code": str(status_code), "message": str(message)}


# create table using boto3 client
def init_table():
    response = client.create_table(
        TableName=TABLENAME,
        AttributeDefinitions=[
            {
                'AttributeName': 'username',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'published',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'community_name',
                'AttributeType': 'S'
            }
        ],
        KeySchema=[
            {
                'AttributeName': 'username',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'published',
                'KeyType': 'RANGE'
            },
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'community_name-index',
                'KeySchema': [
                    {
                        'AttributeName': 'community_name',
                        'KeyType': 'HASH',
                    }
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                },
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 1,
                    'WriteCapacityUnits': 1
                }
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 10,
            'WriteCapacityUnits': 10
        },
    )


tbs = client.list_tables()


# print(tbs)


# function to put items in dynamodb table
# DO NOT CHANGE table_name to TABLENAME
def put_item_ddb(**kwargs):
    # raise error if table name is not in function args
    table_name = kwargs.get('table_name')
    if not table_name:
        raise ValueError("table name does not exist")

    # ensure primary keys are included as args
    req_keys = client.describe_table(TableName='posts')['Table']['KeySchema'] + \
               [i['KeySchema'] for i in client.describe_table(TableName='posts')['Table']['GlobalSecondaryIndexes']][0]
    req_keys = [i['AttributeName'] for i in req_keys]
    for i in req_keys:
        if i not in list(kwargs.keys()):
            print(kwargs)
            raise ValueError(f"Required key '{i}' not included in args")

    # put item in table
    item = {i: {'S': kwargs.get(i)} for i in list(kwargs.keys()) if i != 'table_name'}
    client.put_item(TableName=table_name, Item=item)


# call this function to put initial items in posts
def init_posts():
    # read initial posts values from dynamo_init.json
    with open('dynamo_init.json', 'rb') as f:
        data = json.loads(f.read())['data']

    for i in data:
        kwargs = i.copy()
        kwargs['table_name'] = TABLENAME
        kwargs['published'] = str(datetime.datetime.utcnow().isoformat())
        put_item_ddb(**kwargs)


def print_table_names():
    print("Tables in dynamodb:")
    print(client.list_tables())


# $flask init
# use flask init to create posts table and fill demo data
@app.cli.command('init')
def init_db():
    init_table()
    init_posts()


# 404 page
@app.errorhandler(404)
def page_not_found(status_code=404):
    error_json = get_response(status_code=status_code, message="Resource not found")
    return jsonify(error_json), status_code


# this function is for test only. Will be deleted later
@app.route('/all', methods=['GET'])
def get_all_posts():
    posts = client.scan(TableName=TABLENAME)['Items']
    for post in posts:
        for key in list(post.keys()):
            if type(post[key]) not in [str, int, float, bool]:
                print('Key:', key, 'Value:', post[key], 'Type:', type(post[key]), sep=' ')
    posts = remove_type(posts)
    # posts = sorted(posts, key=lambda x: x['published'])
    posts = sort_json(posts)
    return jsonify(posts), 200


@app.route('/get', methods=["GET"])
def get_post_filtered():
    """
    This route takes TWO arguments only
    n : Number of posts
    community_name : Name of community
    """
    params = request.args

    """
    # retrieve a single item with PK and SK
    response = client.get_item(
        TableName=TABLENAME,
        Key={
            'username':'math_guy_1',
            'published':'2020-04-26T12:55:29.742357'
        }
    )
    #
    """
    if params.get('community_name'):
        kwargs = dict(
            TableName=TABLENAME,
            IndexName='community_name-index',
            KeyConditionExpression='community_name = :community_name',
            ExpressionAttributeValues={
                ':community_name': {'S': params['community_name']},
            },
        )
        if params.get('n'):
            n = params['n']
            try:
                n = int(n)
            except e:
                return page_not_found(404)
            kwargs['Limit'] = n
        response = client.query(**kwargs)
    else:
        kwargs = dict(
            TableName=TABLENAME
        )
        if params.get('n'):
            kwargs['Limit'] = int(params['n'])
        response = client.scan(**kwargs)
    response = response['Items']
    response = remove_type(response)
    return jsonify(response), 200


# verify if it works
@app.route('/create', methods=['GET'])
def create_post():
    params = request.get_json()
    kwargs = params.copy()
    kwargs['table_name'] = TABLENAME
    try:
        put_item_ddb(**kwargs)
    except e:
        return page_not_found(404)
    return get_response(status_code=201, message="Post Created")


# fix this one (not working)
@app.route('/delete', methods=['GET'])
def delete_post():
    key = {}
    params = request.args
    # if not params.get('username') or not params.get('community_name') or not params.get('title'):
    #    return page_not_found(404)
    if not params.get('username'):
        return page_not_found(404)
    key['username'] = {'S': params['username'], }
    if params.get('published'):
        key["published"] = {'S': params["published"], }
    elif params.get('community_name') and params.get('title'):
        key['community_name'] = {'S': params['community_name'], }
        key['title'] = {'S': params['title'], }
    else:
        return page_not_found(404)

    response = client.delete_item(
        TableName=TABLENAME,
        Key=key,
        ConditionExpression='string',
    )
    return 200


def main():
    app.run()


if __name__ == '__main__':
    main()
