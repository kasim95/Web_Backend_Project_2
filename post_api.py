from flask import Flask, jsonify
#from flask import request, jsonify, g, current_app

# fix for local dynamodb creating duplicate tables at once cause of UTC timezone issues
import os
os.environ["TZ"] = "UTC"

# import boto3
from flask_dynamo import Dynamo
import datetime
from pprint import pprint


######################
# API USAGE
# Caddy Web server route for this API: localhost:$PORT/posts/
# Caddy Web server PORT is set to 2015
# --------------------
# Create a new post: Send a POST request to route of create_post() fn
# Example request:
#   curl -i -X POST -H 'Content-Type:application/json' -d
#   '{"title":"Test post", "description":"This is a test post", "username":"some_guy_or_gal", "community_name":"449"}'
#   http://localhost:2015/posts/create;
# --------------------
# Delete an existing post: Send a GET request to route of delete_post() fn
# Example request:
# curl -i -X DELETE http://localhost:2015/posts/delete?post_id=4;
# --------------------
# Retrieve an existing post: Send a GET request to route of get_post() fn
# Example request:
#   curl -i http://localhost:2015/posts/get?post_id=2;
# --------------------
# List the n most recent posts to a particular community:
#   Send a GET request to route of get_posts_filter() fn with args (community_name and n)
# Example request:
# curl -i http://localhost:2015/posts/filter?n=2&community_name=algebra;
# --------------------
# List the n most recent posts to any community:
#   Send a GET request to route of get_posts_filter() fn with args (n)
# Example request:
# curl -i http://localhost:2015/posts/filter?n=2

######################
# References Used:
# https://alvinalexander.com/android/sqlite-autoincrement-insert-value-primary-key
#   Use SELECT last_insert_rowid() in SQL to get last autoincremented value

# https://stackoverflow.com/questions/22669447/how-to-return-a-relative-uri-location-header-with-flask
#   Return location header in a response (Answer by Martijn Pieters)

# new
# https://stackoverflow.com/questions/38918668/dynamodb-create-table-calls-fails'
# Change _naive_is_dst in tz.py to fix negative UTC offset

# https://stackoverflow.com/questions/27894393/is-it-possible-to-save-datetime-to-dynamodb
# Entering datetime as an attribute in dynamodb
######################
app = Flask(__name__)

# app.config.from_object(__name__)

# flask config variables
app.config['DEBUG'] = True

# dynamodb config variables
app.config['AWS_ACCESS_KEY_ID']       = 'fakeMyKeyId'
app.config['AWS_SECRET_ACCESS_KEY']   = 'fakeSecretAccessKey'
app.config['AWS_REGION']              = 'us-west-2'
app.config['DYNAMO_ENABLE_LOCAL']     = True
app.config['DYNAMO_LOCAL_HOST']       = 'localhost'
app.config['DYNAMO_LOCAL_PORT']       = 8000
#

# dynamodb using boto3
"""
# boto3 client (low level api)
# boto3 resource (high level api)
# using a high level api is preferred

dynamodb = boto3.resource(
    'dynamodb',
    region_name='us-west-2',
    endpoint_url="http://localhost:8000")


def init_tables():
    all_tables = list(dynamodb.tables.all())
    table_names = []

    # get list of table names
    if len(all_tables) > 0:
        for i in all_tables:
            table_names.append(i.table_name)
    # create posts table if it does not exist
    if 'posts' not in table_names:
        table = dynamodb.create_table(
            TableName='posts',
            KeySchema=[
                {
                    'AttributeName': 'post_id',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'username',
                    'KeyType': 'RANGE'
                },
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'post_id',
                    'AttributeType': 'N'
                },
                {
                    'AttributeName': 'username',
                    'AttributeType': 'S'
                },
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 1,
                'WriteCapacityUnits': 1
            },
        )
        table.meta.client.get_waiter('table_exists').wait(TableName='posts')
        table.put_item(
            Item={
                'post_id':  1,
                'username': 'math_guy_1',
                'community_name': 'algebra',
                'title': 'Algebra Post 1',
                'description': 'Some quadratic formula',
                'resource_url': 'http://fullerton.edu',
            },
        )
    else:
        table = dynamodb.Table("posts")
    print("Table 'posts' status: ", table.table_status)
    print("No of items in 'posts' table: ", table.item_count)
"""


######################
# create dynamodb table: posts
# dynamodb using flask-dynamo (easier)
app.config['DYNAMO_TABLES'] = [
    dict(
        TableName='posts',
        KeySchema=[
            {
                'AttributeName': 'post_id',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'username',
                'KeyType': 'RANGE'
            },
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'post_id',
                'AttributeType': 'N'
            },
            {
                'AttributeName': 'username',
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 1,
            'WriteCapacityUnits': 1
        },
    )
]

dynamo = Dynamo(app)    # this line should be called after declaring all config variables
with app.app_context():
    dynamo.create_all()


######################
# function to put items in dynamodb table
def put_item_ddb(**kwargs):
    # raise error if table name is not in function args
    table_name = kwargs.get('table_name')
    if not table_name:
        raise ValueError("table name does not exist")

    # ensure primary keys are included as args
    req_keys = [i['AttributeName'] for i in dynamo.tables[table_name].key_schema]
    for i in req_keys:
        if i not in list(kwargs.keys()):
            raise ValueError(f"Required key '{i}' not included in args")

    # put item in table
    item = {i: kwargs.get(i) for i in list(kwargs.keys()) if i != 'table_name'}
    dynamo.tables[table_name].put_item(Item=item)


# call this function to put initial items in posts
def init_posts():
    put_item_ddb(table_name='posts',
                 post_id=1,
                 username='math_guy_1',
                 community_name='algebra',
                 title='Algebra Post 1',
                 description='Some quadratic formula',
                 resource_url='http://fullerton.edu',
                 published=str(datetime.datetime.utcnow().isoformat()),
                 )

    put_item_ddb(table_name='posts',
                 post_id=2,
                 username='math_guy_1',
                 community_name='calculus',
                 title='Calculus Post 1',
                 description='Steps to integrate',
                 published=str(datetime.datetime.utcnow().isoformat()),
                 )

    put_item_ddb(table_name='posts',
                 post_id=3,
                 username='math_guy_2',
                 community_name='algebra',
                 title='Algebra Post 1',
                 description='Some quadratic formula',
                 resource_url='http://fullerton.edu',
                 published=str(datetime.datetime.utcnow().isoformat()),
                 )

    put_item_ddb(table_name='posts',
                 post_id=4,
                 username='some_math_guy',
                 community_name='algebra',
                 title='Algebra Post 1',
                 description='Some quadratic formula',
                 resource_url='http://fullerton.edu',
                 published=str(datetime.datetime.utcnow().isoformat()),
                 )


init_posts()


def print_table_names():
    print("Tables in dynamodb:")
    for table_name, table in dynamo.tables.items():
        print(table_name)


# print_table_names()


def delete_all_tables():
    dynamo.destroy_all()

# print whole posts table
# pprint(dynamo.tables['posts'].scan()['Items'])


@app.route('/all', methods=['GET'])
def get_all_posts():
    posts = dynamo.tables['posts'].scan()['Items']
    for post in posts:
        for key in list(post.keys()):
            if key =='post_id':
                post[key] = int(post[key])
            if type(post[key]) not in [str, int, float, bool]:
                print('Key:', key,'Value:', post[key],'Type:', type(post[key]), sep=' ')
    posts = sorted(posts, key=lambda x: x['post_id'])
    return jsonify(posts), 200


# old code
"""
# initiate db with
# $FLASK_APP=post_api.py
# $flask init
@app.cli.command('init')
def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('data.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


# close db connection
@app.teardown_appcontext
def close_db(e=None):
    if e is not None:
        print(f'Closing db: {e}')
    db = g.pop('db', None)
    if db is not None:
        db.close()


# home page
@app.route('/', methods=['GET'])
def home():
    return jsonify(get_response(status_code=200, 
        message="Welcome to CSUF Discussions Post API."))


# 404 page
@app.errorhandler(404)
def page_not_found(status_code=404):
    error_json = get_response(status_code=status_code, message="Resource not found")
    return jsonify(error_json), status_code


# function to execute a single query at once
def query_db(query, args=(), one=False, commit=False):
    # one=True means return single record
    # commit = True for post and delete query (return boolean)
    conn = get_db()
    try:
        rv = conn.execute(query, args).fetchall()
        if commit:
            conn.commit()
    except sqlite3.OperationalError as e:
        print(e)
        return False
    close_db()
    if not commit:
        return (rv[0] if rv else None) if one else rv
    return True


# function to execute multiple queries at once (also fn commits the transaction)
def transaction_db(query, args, return_=False):
    # return_=True if the transaction needs returns a result
    conn = get_db()
    if len(query) != len(args):
        raise ValueError('arguments dont match queries')
    try:
        rv = []
        conn.execute('BEGIN')
        for i in range(len(query)):
            rv.append(conn.execute(query[i], args[i]).fetchall())
        conn.commit()
    except (sqlite3.OperationalError, sqlite3.ProgrammingError) as e:
        conn.execute('rollback')
        print('Transaction failed. Rolled back')
        print(e)
        return False
    close_db()
    return True if not return_ else rv


# function to retrieve a single post with post_id
@app.route('/get', methods=['GET'])
def get_post():
    params = request.args
    post_id = params.get('post_id')
    if not post_id:
        return page_not_found(404)
    query = 'SELECT post_id, title, description, resource_url, published, username, community_name FROM posts ' \
            'INNER JOIN community ON posts.community_id=community.community_id WHERE post_id=?'
    args = (post_id,)
    q = query_db(query, args, one=True)
    if q:
        return jsonify(q), 200
    return page_not_found(404)


# function to retrieve posts with filters for a number of posts n (default value of n is 100)
@app.route('/filter', methods=['GET'])
def get_posts_filter():
    params = request.args
    query = 'SELECT post_id, title, published, username, community_name FROM posts ' \
             'INNER JOIN community ON posts.community_id=community.community_id WHERE'
    args = []

    post_id = params.get('post_id')
    filters = 0
    if post_id:
        query += ' post_id=? AND'
        args.append(post_id)
        filters += 1

    username = params.get('username')
    if username:
        query += ' username=? AND'
        args.append(username)
        filters += 1

    published = params.get('published')
    if published:
        query += ' published=? AND'
        args.append(published)
        filters += 1

    title = params.get('title')
    if title:
        query += ' title=? AND'
        args.append(title)
        filters += 1

    community_name = params.get('community_name')
    if community_name:
        query += ' community_name=? AND'
        args.append(community_name)
        filters += 1

    if filters > 0:
        query = query[:-4]
    else:
        query = query[:-6]

    number = params.get('n')
    if not number:
        number = 100
    count_query = 'SELECT COUNT(post_id) FROM '
    query += ' ORDER BY published DESC LIMIT ?;'
    args.append(number)

    q = query_db(query, tuple(args))
    if q:
        return jsonify(q), 200
    return page_not_found(404)


# function to add a new post to db
@app.route('/create', methods=['POST'])
def create_post():
    params = request.get_json()
    community_name = params.get('community_name')
    title = params.get('title')
    username = params.get('username')
    description = params.get('description')
    resource_url = params.get('resource_url')

    if not title or not username or not community_name:
        return jsonify(get_response(status_code=409, message="username / title / community_name does not in request"))
    query1 = 'INSERT INTO votes (upvotes, downvotes) VALUES (?, ?)'
    args1 = (0, 0)

    query_community = 'SELECT community_id FROM community WHERE community_name=?'
    args_community = (community_name,)
    community_id = query_db(query_community, args_community, one=True, commit=False)
    query4 = 'SELECT last_insert_rowid();'
    args4 = ()
    if community_id is not None:
        if type(community_id) == list:
            id_ = community_id[0]['community_id']
        else:
            id_ = community_id['community_id']

        query3 = 'INSERT INTO posts (community_id, title, description, resource_url, username, vote_id) ' \
                 'VALUES (?,?,?,?,?,(SELECT MAX(vote_id) FROM votes))'
        args3 = (id_, title, description, resource_url, username)
        q = transaction_db(query=[query1, query3, query4], args=[args1, args3, args4], return_=True)
    else:
        query2 = 'INSERT INTO community (community_name) VALUES (?)'
        args2 = (community_name,)
        query3 = 'INSERT INTO posts (community_id, title, description, resource_url, username, vote_id) ' \
                 'VALUES ((SELECT community_id FROM community WHERE community_name=?),?,?,?,?,' \
                 '(SELECT MAX(vote_id) FROM votes))'
        args3 = (community_name, title, description, resource_url, username)
        q = transaction_db(query=[query1, query2, query3, query4], args=[args1, args2, args3, args4], return_=True)
    if not q:
        return page_not_found(404)
    rowid = q[-1][0]["last_insert_rowid()"]
    response = jsonify(get_response(status_code=201, message="Post created"))
    response.status_code = 201
    response.headers['location'] = "http://localhost:2015/posts/get?post_id=" + str(rowid)
    response.autocorrect_location_header = False
    return response


# function to delete an existing post from db
@app.route('/delete', methods=['DELETE'])
def delete_post():
    params = request.args

    post_id = params.get('post_id')
    if not post_id:
        return page_not_found(404)

    query1 = 'SELECT * FROM posts WHERE post_id=?'
    args1 = (post_id,)
    if not query_db(query1, args1):
        return jsonify(get_response(status_code=404, message="Post does not exist")), 404

    query2 = 'DELETE FROM votes WHERE vote_id=(SELECT vote_id FROM posts WHERE post_id=?)'
    args2 = (post_id,)

    query3 = 'DELETE FROM posts WHERE post_id=?'
    args3 = (post_id,)

    q = transaction_db([query2, query3], [args2, args3])
    if not q:
        return page_not_found(404)
    return jsonify(get_response(status_code=200, message="Post deleted")), 200
"""


def main():
    app.run()
    # init_tables() # boto3
    # pass


if __name__ == '__main__':
    main()
