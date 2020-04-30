import datetime
import json
from flask import Flask, jsonify, request, send_from_directory

# fix for local dynamodb creating duplicate tables at once because of UTC timezone issues
import os
os.environ["TZ"] = "UTC"
#
import boto3


######################
# References

######################
# GLOBALS
TABLENAME = 'posts'
DATABASE_DATA = 'posts.json'

# flask globals
app = Flask(__name__)

# flask config variables
app.config['DEBUG'] = True

# dynamodb config variables (delete later)
app.config['AWS_ACCESS_KEY_ID'] = 'fakeMyKeyId'
app.config['AWS_SECRET_ACCESS_KEY'] = 'fakeSecretAccessKey'
app.config['AWS_REGION'] = 'us-west-2'
app.config['DYNAMO_ENABLE_LOCAL'] = True
app.config['DYNAMO_LOCAL_HOST'] = 'localhost'
app.config['DYNAMO_LOCAL_PORT'] = 8000
#

# Dynamodb globals
client = boto3.client('dynamodb', endpoint_url='http://localhost:8000')

# dynamodb using boto3
# boto3 client (low level api)
# boto3 resource (high level api)


######################
# Helpers
# remove attribute type from json
# remove_type = lambda x: [{i: j[i]['S'] for i in list(j.keys())} for j in x]
remove_type = lambda x: \
    [{i: j[i][list(j[i].keys())[0]] for i in list(j.keys())} for j in x]


"""
def remove_type(resp):
    for j in resp:
        for i in list(j.keys()):
            if i ==  'published':
                attr = {i: j[i]['N']}
            else:
                attr = {i: j[i]['S']}
"""


# sort json using a key
sort_json = lambda x: sorted(x, key=lambda y: y['published'])


# helper function to generate a response with status code and message
def get_response(status_code, message):
    return {"status_code": str(status_code), "message": str(message)}


######################
# Dynamodb functions
# create table using boto3 client
def init_table():
    response = client.create_table(
        TableName=TABLENAME,
        AttributeDefinitions=[
            {
                'AttributeName': 'uuid',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'published',
                'AttributeType': 'N'
            },
            {
                'AttributeName': 'community_name',
                'AttributeType': 'S'
            }
        ],
        KeySchema=[
            {
                'AttributeName': 'uuid',
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
                    },
                    {
                        'AttributeName': 'published',
                        'KeyType': 'RANGE'
                    },
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                },
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 25,
                    'WriteCapacityUnits': 25
                }
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 50,
            'WriteCapacityUnits': 50
        },
    )
    print("Create Table operation finished successfully")


# tbs = client.list_tables()
# print(tbs)


# function to put a single item in dynamodb
# DO NOT CHANGE table_name to TABLENAME
def put_item_ddb(**kwargs):
    # raise error if table name is not in function args
    table_name = kwargs.get('table_name')
    if not table_name:
        raise ValueError("table name not specified")

    # ensure primary keys are included as args
    req_keys = client.describe_table(TableName=table_name)['Table']['KeySchema'] + \
               [i['KeySchema'] for i in client.describe_table(TableName=table_name)['Table']['GlobalSecondaryIndexes']][0]
    req_keys = [i['AttributeName'] for i in req_keys]
    for i in req_keys:
        if i not in list(kwargs.keys()):
            # print(kwargs)
            raise ValueError(f"Required key '{i}' not included in args")
    #

    # put item in table
    # item = {i: {'S': kwargs.get(i)} for i in list(kwargs.keys()) if i != 'table_name'}
    item = {}
    for i in list(kwargs.keys()):
        if i != 'table_name':
            if i == 'published':
                item[i] = {"N": str(kwargs.get(i))}
            else:
                item[i] = {"S": kwargs.get(i)}
    #
    client.put_item(TableName=table_name, Item=item)


# function to put items in batch in dynamodb
# all items in batch should belong to the same table
def put_item_batch(items):
    table_name = items[0].get('table_name')
    if not table_name:
        raise ValueError('table name not specified')

    # get required keys (Partition key, Sorting Key, Secondary index Key)
    req_keys = client.describe_table(TableName=table_name)['Table']['KeySchema'] + \
               [i['KeySchema'] for i in
                client.describe_table(TableName=table_name)['Table']['GlobalSecondaryIndexes']][0]
    req_keys = [i['AttributeName'] for i in req_keys]

    putreq_list = []
    for item in items:
        # ensure required keys are included as args
        for i in req_keys:
            if i not in list(item.keys()):
                # print(item)
                raise ValueError(f"Required key '{i}' not included in args")
        #

        # Write items in batch
        # putreq = {'PutRequest': {'Item': {i: {'S': item.get(i)} for i in list(item.keys()) if i != 'table_name'}}}
        it = {}
        for i in list(item.keys()):
            if i != 'table_name':
                if i == 'published':
                    it[i] = {"N": str(item[i])}
                else:
                    it[i] = {"S": item[i]}

        putreq = {'PutRequest': {"Item": it}}
        #

        putreq_list.append(putreq)
    req_items = {table_name: putreq_list}

    # write in batch
    # print(req_items)
    response = client.batch_write_item(RequestItems=req_items)


# call this function to put initial items in posts
# this function takes around 30 mins for ~5000 records
def init_posts():
    # read initial posts values from DATABASE_DATA file
    with open(DATABASE_DATA, 'rb') as f:
        data = json.loads(f.read())['data']

    for i in data:
        kwargs = i.copy()
        kwargs['table_name'] = TABLENAME
        # if published key is not present, default it to right now since it is a Sorting Key
        kwargs.setdefault('published', str(datetime.datetime.utcnow().isoformat()))
        #
        # delete kwargs with values as empty strings or None
        for j in list(kwargs.keys()):
            if kwargs[j] is None or kwargs[j] == "":
                _ = kwargs.pop(j, None)
        #
        # write item to db
        put_item_ddb(**kwargs)
    print("Create Posts Operation finished successfully")


# init posts in batch (for faster db initialization)
def init_posts_batch():
    # read initial posts values from DATABASE_DATA file
    with open(DATABASE_DATA, 'rb') as f:
        data = json.loads(f.read())['data']
    #
    count = 0
    # batch_size cannot exceed 25 (gives an error)
    batch_size = 25     # decrease this value if fn gives Throughput error
    while True:
        if count >= len(data):
            break
        if count != 0 and count % 500 == 0:
            print(f"{count} items written to db")
        items = data[count:count+batch_size]
        batch = []
        for i in items:
            kwargs = i.copy()
            kwargs['table_name'] = TABLENAME
            # if published key is not present, default it to right now since it is a Sorting Key
            kwargs.setdefault('published', str(datetime.datetime.utcnow().isoformat()))
            #
            # delete kwargs with values as empty strings or None
            for j in list(kwargs.keys()):
                if kwargs[j] is None or kwargs[j] == "":
                    _ = kwargs.pop(j, None)
            batch.append(kwargs)
            #

        put_item_batch(batch)
        # increment counter
        count += batch_size
    print("Batch Create Posts Operation finished successfully")


def print_table_names():
    print("Tables in dynamodb:")
    print(client.list_tables())


######################
# Flask Routes
# $flask init
# use flask init to create posts table and fill it with data
@app.cli.command('init')
def init_db():
    table_names = client.list_tables()['TableNames']
    if len(client.list_tables()['TableNames']) > 0:
        for i in table_names:
            response = client.delete_table(TableName=i)
        print("Existing tables purged")
    print('*' * 30)
    print(f"Creating new table {TABLENAME}")
    init_table()
    print('*'*30)
    print(f"Posts Batch writing Operation started")
    # init_posts()
    init_posts_batch()
    print('*' * 30)


# 404 page
@app.errorhandler(404)
def page_not_found(status_code=404):
    error_json = get_response(status_code=status_code, message="Resource not found")
    return jsonify(error_json), status_code


# fix favicon 500 error (Reference used)
@app.route('/favicon.ico')
def favicon():
    return page_not_found(404)


# this function is for test only. Will be deleted later
@app.route('/all', methods=['GET'])
def get_all_posts():
    posts = client.scan(TableName=TABLENAME)['Items']
    """
    for post in posts:
        for key in list(post.keys()):
            if type(post[key]) not in [str, int, float, bool]:
                print('Key:', key, 'Value:', post[key], 'Type:', type(post[key]), sep=' ')
    """
    posts = remove_type(posts)
    posts = sort_json(posts)
    return jsonify(posts), 200


@app.route('/get', methods=["GET"])
def get_post_filtered():
    """
            This route takes the following arguments
            n : Number of posts
            community_name : Name of community
            uuid : uuid (also requires published (shoould be used for a single post retrieval))
            if params contains uuid, all other params are ignored except published
    """
    params = request.args
    if params.get('uuid') is not None:
        # got uuid, return a single post (Ignore all other params)
        kwargs = dict(
            TableName=TABLENAME,
            KeyConditionExpression='#uuid_key = :uuid',
            ExpressionAttributeValues={
                ':uuid': {'S': f'{str(params["uuid"])}'}
            },
            ExpressionAttributeNames={
                '#uuid_key': 'uuid',
            }
        )
        response = client.query(**kwargs)
        if 'Items' in response:
            response = response['Items']
        else:
            response = []
    else:
        if params.get('community_name'):
            # got community_name, filter posts from community_name (ignore uuid and published)
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
            #
            if params.get('recent') is not None:
                kwargs['ScanIndexForward'] = not params['recent']
            #
            response = client.query(**kwargs)
            response = response['Items']
        else:
            # no community name, return all results with limit (ignore uuid and published
            kwargs = dict(
                TableName=TABLENAME
            )
            # Scan whole table and sort it
            result = []
            response = client.scan(TableName='posts')
            for i in response['Items']:
                result.append(i)
            while 'LastEvaluatedKey' in response:
                response = client.scan(TableName='posts', ExclusiveStartKey=response['LastEvaluatedKey'])
                for i in response["Items"]:
                    result.append(i)

            # sort on published
            if params.get('recent') is not None:
                result = sorted(result, key=lambda x: x['published']['N'], reverse=True)

            # return n posts
            if params.get('n'):
                result = result[:int(params['n'])]

            response = result
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
