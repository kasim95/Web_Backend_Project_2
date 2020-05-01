import datetime
import redis
from flask import Flask, jsonify, request
import json


#config
app = Flask(__name__)
app.config['DEBUG'] = True




def init_db():
    db = redis.StrictRedis(host='localhost',
    port=6379,
    db=1,
    decode_responses=True)
    return db

def fill_db():
    r.flushdb()
    with open('votes.json') as data_file:
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

"""

with open('votes.json', 'rb') as f:
    votes = json.loads(f.read())['data']
for v in votes:
    r.set(v['uuid'], v['score'])
"""

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



@app.route('/get_all', methods=['GET'])
def get_posts_all():
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


# http://127.0.0.1:5000/get?n=25&community_name=csuf&sorted=True
# http://127.0.0.1:5000/get?n=25&community_name=csuf
# http://127.0.0.1:5000/get?n=25
# http://127.0.0.1:5000/get?n=25&sorted=True
# http://127.0.0.1:5000/get?uuid=CUJCJWC6NZGR1A781OSPMNKPJ
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
            return jsonify(get_response(404, "uuid not found"))
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


# format for POST Request:
# {'uuid':[1234, 123, 123, 123]}
# example curl command in test_scripts/v01_getlist.sh
# sorted = True for uuids sorted in descending order by score
# n = 25 to return top 25 posts from the requested uuids
@app.route('/getlist', methods=['POST'])
def get_score_list():
    params = request.json
    if params.get('uuid') is None:
        return jsonify(get_response(status_code=404, message='uuid attribute not found'))
    uuids = params.get('uuid')
    json_ = []
    for i in uuids:
        score = r.hget(i,"score")
        if score is not None:
            json_.append({'uuid': i, 'score': score})
    if len(json_) > 0:
        if bool(params.get('sorted')):
            json_ = sorted(json_, key=lambda x: int(x['score']), reverse=True)

        if params.get('n') is not None:
            json_ = json_[:int(params.get('n'))]
        return jsonify(json_), 200
    else:
        return jsonify([]), 200

@app.route('/upvotes',methods=['POST'])
def get_upvotes():
    params = request.get_json()
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



@app.route('/downvotes',methods=['POST'])
def get_downvotes():
    params = request.get_json()
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


def main():

    app.run()


if __name__ == '__main__':
    main()
