import datetime
import json
from flask import Flask, jsonify, request, send_from_directory


# flask globals
app = Flask(__name__)

# flask config variables
app.config['DEBUG'] = True


# 404 page
@app.errorhandler(404)
def page_not_found(status_code=404):
    error_json = get_response(status_code=status_code, message="Resource not found")
    return jsonify(error_json), status_code


# fix favicon 500 error (Reference used)
@app.route('/favicon.ico')
def favicon():
    return page_not_found(404)



@app.route('/get', methods=["GET"])
def get_recent_post():
    """
        This route tekes TWO argument only
        n: Number of Posts
        community_name : Name of community

    """
    params = request.args
    r = requests.get('https://127.0.0.1:5100/get')

    if params.get('community_name'):
        pass
    else:
        if params.get('n'):
            limit=int(params['n'])


    response= response['Items']
    response = remove_type(response)
    return jsonify(response), 200


    #return "hello"


if __name__ == "__main__":
    app.run()
