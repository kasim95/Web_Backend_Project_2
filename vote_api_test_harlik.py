import flask,redis
from flask import request, jsonify, g, current_app
# import sqlite3
import json

#config

DEBUG = True

app = flask.Flask(__name__)
app.config.from_object(__name__)

r = redis.StrictRedis(host='localhost', port=6379, db=1, decode_responses=True)

@app.cli.command('init')
def init_db():
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



@app.teardown_appcontext
def close_db(e=None):
	db = g.pop('db', None)
	if db is not None:
		db.close()


# home page
@app.route('/', methods=['GET'])
def home():
    return "<h1>Welcome to CSUF Discussions API</h1>" \
           "<p>Use /votes for votes api</p>"


@app.errorhandler(404)
def page_not_found(status_code=404):
    error_json = get_response(status_code=status_code, message="Resource not found")
    return jsonify(error_json), status_code


# function to retrieve all votes without any filters
#curl 'http://127.0.0.1:5000/all;
@app.route('/all', methods=['GET'])
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

"""
for uuid in all_id_sorted_by_score:
	d={}
	score = r.get(uuid,"score")
	published = r.get(uuid,"published")
	community_name = r.get(uuid,"community_name")

	d["uuid"]=uuid
	d["score"] = score
	d["published"] = published
	d["community_name"] = community_name

	json_.append(d)
    #published = r.hget("{}".format(uuid),"score")
"""
def main():
	app.run()


if __name__ == '__main__':
	main()
