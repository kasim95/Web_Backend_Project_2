import datetime
import redis
from flask import Flask, jsonify, request
import json

"""
---------------------Dev 2 - Porting to the voting microservice to Redis---------------------------
1. Upvote a post
curl -i -X POST -H 'Content-Type:application/json' -d '{"uuid":"QWERTYMXW3TICIOQBCND86Z0D3"}' http://localhost:5200/upvotes

2. Downvote a post
curl -i -X POST -H 'Content-Type:application/json' -d '{"uuid":"QWERTYMXW3TICIOQBCND86Z0D3"}' http://localhost:5200/downvotes

3. Report the number of scores (downvotes-upvotes) for a post:
curl -i -X GET 'http://localhost:5200/get?uuid=HARLIKMXW3TICIOQBCND86Z0D3'

4. List the n top-scoring posts to any community:
curl -i -X GET 'http://localhost:5200/get?n=25&community_name=csuf'

5. Given a list of post identifiers, return the list sorted by score.:
curl -i -X POST -H 'Content-Type:application/json' -d '{"n":3, "sorted":"True", "uuid":["HARLIKMXW3TICIOQBCND86Z0D3", "C59OGYZWADQVRCCOREWSOUP3R", "ASD3C3PH204FAQ2EEHZY8IG7R"]}' http://localhost:5200/getlist;

6. Create operation
curl -i -X POST -H 'Content-Type:application/json' -d '{"uuid":"HARLIKMXW3TICIOQBCND86Z0D3", "community_name":"csuf", "score":"0", "published":"15058265108"}' http://localhost:5200/create_vote

7. Delete operation
curl -i -X DELETE 'http://localhost:5200/delete_vote?uuid=CAEPJIPK49FSWZ4K02JBAFYJB'

8. Retrieve all operations
curl -i -X GET 'http://localhost:5200/get_all'

"""

#flask globals
app = Flask(__name__)
#flask config variables
app.config['DEBUG'] = True

# Init the Redis database
def init_db():
    db = redis.StrictRedis(host='localhost',
    port=6379,
    db=1,
    decode_responses=True)
    return db

def fill_db():
    r.flushdb()
    with open('data/votes.json') as data_file:
        test_data = json.load(data_file)

    length = (len(test_data["data"]))
    for i in range(0,length):
        d = test_data["data"][i]
        uuid = d["uuid"]
        published = d["published"]
        score = d["score"]
        community_name = d["community_name"]

        #--adding in redis
        r.hset(uuid, "community_name" ,community_name)
        r.sadd(community_name,  uuid)
        r.hset(uuid, "score" ,score)
        r.hset(uuid, "published" ,published)
        r.zadd("score",{uuid : score })
        r.zadd("published",{ uuid: published })


# initiaize redis database
r = init_db()

# load data in redis database
fill_db()


# helper function to generate a response with status code and message
def get_response(status_code, message):
    return {"status_code": str(status_code), "message": str(message)}


# home page
@app.route('/', methods=['GET'])
def home():
    return "<h1>Welcome to CSUF Discussions API</h1>" \
           "<p>Use /votes for votes api</p>"


@app.errorhandler(404)
def page_not_found(status_code=404):
    error_json = get_response(status_code=status_code, message="Resource not found")
    return jsonify(error_json), status_code


# It will return all the rows from the database
@app.route('/get_all', methods=['GET'])
def get_votes_all():
    all_id_sorted_by_score = r.zrange("score", 0, -1, desc=True)
    json_ = []

    for uuid in all_id_sorted_by_score:
        d={}
        score = r.hget(uuid,"score")
        published = r.hget(uuid,"published")
        community_name = r.hget(uuid,"community_name")
        d["uuid"]=uuid
        d["score"] = score
        d["published"] = published
        d["community_name"] = community_name
        json_.append(d)

    return jsonify(json_), 200


# This will return a list of rows of corresponding uuids sorted by score
@app.route('/getlist', methods=['POST'])
def get_score_list():
    params = request.json
    if params.get('uuid') is None:
        return jsonify(get_response(status_code=404, message='uuid attribute not found'))
    uuids = params.get('uuid')
    json_ = []
    for i in uuids:
        score = r.hget(i,"score")
        community_name = r.hget(i,"community_name")
        published = r.hget(i,"published")
        if score is not None:
            json_.append({'uuid': i, 'community_name':community_name, 'score': score, 'published':published})
    if len(json_) > 0:
        if bool(params.get('sorted')):
            json_ = sorted(json_, key=lambda x: int(x['score']), reverse=True)

        if params.get('n') is not None:
            json_ = json_[:int(params.get('n'))]
        return jsonify(json_), 200
    else:
        return jsonify([]), 200


"""
http://127.0.0.1:5000/get?n=25&community_name=csuf&sorted=True
http://127.0.0.1:5000/get?n=25&community_name=csuf
http://127.0.0.1:5000/get?n=25
http://127.0.0.1:5000/get?n=25&sorted=True
http://127.0.0.1:5000/get?uuid=CUJCJWC6NZGR1A781OSPMNKPJ

It will return the rows as per parameters passed
"""
@app.route('/get', methods=['GET'])
def get_score():
    params = request.args
    if params.get('uuid') is not None:
        score = r.hget(params.get('uuid'),"score")
        published = r.hget(params.get('uuid'),"published")
        community_name = r.hget(params.get('uuid'),"community_name")
        if score is not None:
            json_ = [
                {
                    'uuid': params.get('uuid'),
                    'score': score ,
                    'published': published,
                    'community_name': community_name
                }
            ]
            return jsonify(json_), 200
        else:
            return jsonify(get_response(404, "score not found"))
    elif params.get('n') is not None:

        if params.get('community_name') is not None:

            community_id_set = r.smembers( params.get('community_name') )
            json_=[]
            for uuid in community_id_set:
                score = r.hget(uuid,"score")
                published = r.hget(uuid,"published")
                community_name = r.hget(uuid,"community_name")

                if score is not None:
                    json_.append({'uuid': uuid, 'score':score , 'published': published , 'community_name':community_name })

            if bool(params.get('sorted')):
                json_ = sorted(json_, key=lambda x: int(x['score']), reverse=True)
            return jsonify(json_[:int(params.get('n'))])

        keys = r.zrange("published", 0, -1, desc=True)
        json_ = []
        for uuid in keys:

            score = r.hget(uuid,"score")
            published = r.hget(uuid,"published")
            community_name = r.hget(uuid,"community_name")
            if score is not None:
                json_.append({'uuid': uuid, 'score':score , 'published': published , 'community_name':community_name })
        if bool(params.get('sorted')):
            json_ = sorted(json_, key=lambda x: int(x['score']), reverse=True)
        return jsonify(json_[:int(params.get('n'))])


"""
    http://127.0.0.1:5000/create_vote?uuid=QWERTYWC6NZGR1A781OSPMNKPJ&community_name=csuf&score=548789&published=1521027928.0

It will create a new entry into the database with all the columns details mentioned in the url
"""
@app.route('/create_vote',methods=['POST'])
def create_vote():
    params = request.json
    if params.get('uuid') is not None:

        uuid = params["uuid"]
        community_name = params["community_name"]
        score = params["score"]
        published = params["published"]

        if not r.exists(uuid):
            r.hset(uuid, "community_name" ,community_name)
            r.sadd(community_name,  uuid)
            r.hset(uuid, "score" ,score)
            r.hset(uuid, "published" ,published)
            r.zadd("score",{uuid : score })
            r.zadd("published",{ uuid: published })
            return jsonify(status_code=201,message="New row created")

        return jsonify(status_code=409, message='uuid already exists')
    else:
        return jsonify(get_response(status_code=404, message='uuid attribute not found'))

# It will increment (upvote) the score column into the database
@app.route('/upvotes',methods=['POST'])
def get_upvotes():
    params = request.json
    uuid=params.get('uuid')
    if uuid is None:
        return jsonify(get_response(status_code=404, message='uuid attribute not found'))

    r.hincrby( uuid ,"score",1)
    score = r.hget(uuid,"score")
    published = r.hget(uuid,"published")
    community_name = r.hget(uuid,"community_name")
    json_ = [
        {
            'uuid': uuid,
            'score': score ,
            'published': published,
            'community_name': community_name
        }
    ]
    return jsonify(json_), 200

# It will decrement (downvote) the score column into the database
@app.route('/downvotes',methods=['POST'])
def get_downvotes():
    params = request.json
    if params.get('uuid') is None:
        return jsonify(get_response(status_code=404, message='uuid attribute not found'))
    uuid = params.get('uuid')
    r.hincrby( uuid ,"score",-1)
    score = r.hget(uuid,"score")
    published = r.hget(uuid,"published")
    community_name = r.hget(uuid,"community_name")
    json_ = [
        {
            'uuid': params.get('uuid'),
            'score': score ,
            'published': published,
            'community_name': community_name
        }
    ]
    return jsonify(json_), 200

# It will delete the entry from the database
@app.route('/delete_vote',methods=['DELETE'])
def delete_vote():
    params = request.args
    if params.get('uuid') is not None:
        uuid = params["uuid"]
        if r.exists(uuid):
            r.delete(uuid)
            return jsonify(get_response(status_code=200, message='Vote deleted'))
    else:
        return jsonify(get_response(status_code=404, message='Delete vote requires uuid attribute'))


def main():
    app.run()

if __name__ == '__main__':
    main()
