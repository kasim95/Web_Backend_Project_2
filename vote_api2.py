import datetime
import redis
from flask import Flask, jsonify, request
import json

r = redis.Redis(host='localhost', port=6379, db=1)
# load data
with open('votes.json', 'rb') as f:
    votes = json.loads(f.read())['data']
for v in votes:
    r.set(v['uuid'], v['score'])


# helper function to generate a response with status code and message
def get_response(status_code, message):
    return {"status_code": str(status_code), "message": str(message)}


app = Flask(__name__)
app.config['DEBUG'] = True


@app.cli.command('init')
def init():
    with open('votes.json', 'rb') as f:
        json_ = json.loads(f.read())['data']
    for i in json_:
        r.set(i['uuid'], i['score'])


@app.route('/get', methods=['GET'])
def get_score():
    params = request.args
    if params.get('uuid') is not None:
        score = r.get(params.get('uuid'))
        if score is not None:
            json_ = [
                {
                    'uuid': params.get('uuid'),
                    'score': score.decode('utf-8')
                }
            ]
            return jsonify(json_), 200
        else:
            return jsonify(get_response(404, "uuid not found"))
    elif params.get('n') is not None:
        keys = r.keys()
        json_ = []
        for i in keys:
            score = r.get(i).decode('utf-8')
            if score is not None:
                json_.append({'uuid': i.decode('utf-8'), 'score':score})
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
        score = r.get(i)
        if score is not None:
            json_.append({'uuid': i, 'score': score.decode('utf-8')})
    if len(json_) > 0:
        if bool(params.get('sorted')):
            json_ = sorted(json_, key=lambda x: int(x['score']), reverse=True)

        if params.get('n') is not None:
            json_ = json_[:int(params.get('n'))]
        return jsonify(json_), 200
    else:
        return jsonify([]), 200


def main():

    app.run(port=5001)


if __name__ == '__main__':
    main()
