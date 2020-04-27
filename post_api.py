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
remove_type = lambda x: [{i: j[i]['S'] for i in list(j.keys())} for j in x]


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
                'AttributeType': 'S'
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
                    }
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                },
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 20,
            'WriteCapacityUnits': 20
        },
    )
    print("Create Table operation finished successfully")


tbs = client.list_tables()
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
    item = {i: {'S': kwargs.get(i)} for i in list(kwargs.keys()) if i != 'table_name'}
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
        putreq = {'PutRequest': {'Item': {i: {'S': item.get(i)} for i in list(item.keys()) if i != 'table_name'}}}
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
    init_table()
    # init_posts()
    init_posts_batch()


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
