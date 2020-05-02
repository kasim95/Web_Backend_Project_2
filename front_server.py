import math, json, requests
from flask import Flask, jsonify, request, send_from_directory,make_response
from rfeed import *
from datetime import datetime

# flask globals
app = Flask(__name__)

# flask config variables
app.config['DEBUG'] = True


# static values
POST_PORT_NO=5100 #set port number for post_api
VOTE_PORT_NO=5200 #set port number for vote_api


# n not found error
def custom_error(message, status_code):
    return make_response(jsonify(message), status_code)

# 404 page
@app.errorhandler(404)
def page_not_found(status_code=404):
    error_json = get_response(status_code=status_code, message="Resource not found")
    return jsonify(error_json), status_code

# fix favicon 500 error (Reference used)
@app.route('/favicon.ico')
def favicon():
    return page_not_found(404)

# helper function to generate a response with status code and message
def get_response(status_code, message):
    return {"status_code": str(status_code), "message": str(message)}




class APIError(Exception):
    """throws API error exception"""

    def __init__(self, status):
        self.status = status

    def __str__(self):
        return {"APIError: status": str(self.status)}



# 1) The 25 most recent posts to a particular community
# http://localhost:5000/get?n=25&community_name=csuf
#2) The 25 most recent posts to any community
#http://localhost:5000/get?n=25
@app.route('/get', methods=["GET"])
def get_recent_post():
    """
        This route takes ONE or TWO arguments
        n: Number of Posts (mandatory or required)
        community_name : Name of community

    """

    params = request.args

    if params.get('n') is not None:

        no_of_post=int(params['n'])
        # got number of post, now fetching data using post API

        if params.get('community_name') is not None:
            community_name=str(params['community_name'])
            post_resp = requests.get('http://127.0.0.1:{}/get?n={}&community_name={}&recent=True'.format(POST_PORT_NO,no_of_post,community_name))
        else:
            post_resp = requests.get('http://127.0.0.1:{}/get?n={}&recent=True'.format(POST_PORT_NO,no_of_post))

        if post_resp.status_code != 200:
        # This means something went wrong.
            raise APIError(post_resp.status_code)
        data=post_resp.json() # convert fetch data to python list of dict

        # generate RSS
        rss_list=[]
        for dic in data:
            date = datetime.fromtimestamp(int(dic['published']))

            item1 = Item(
                title = dic.get('title',"") or "", # get title form dict or empty string
                link = dic.get('url',"") or "",
                description = dic.get('description',"") or "",
                author = dic.get('username',"") or "",
                guid = Guid(dic.get('url',"") or ""),
                categories= dic.get('community_name',"") or "",
                pubDate = date)
            rss_list.append(item1)

        feed = Feed(
            title = "Reddit clone RSS Feed",
            link = "http://www.example.com/rss",
            description = "This is project-2 for CPSC-449 an RSS 2.0 feed",
            language = "en-US",
            lastBuildDate = datetime.now(),
            items = rss_list)

        response = make_response(feed.rss())
        response.headers.set('Content-Type', 'application/rss+xml')
        return response


    else:
        return custom_error("Enter value of n",404)


# 3) The top 25 posts to a particular community, sorted by score
# http://localhost:5000/get_sorted?n=25&community_name=csuf
# 4) The top 25 posts to any community, sorted by score
# http://localhost:5000/get_sorted?n=25
@app.route('/get_sorted', methods=["GET"])
def get_recent_post_scorted():
    """
        This route takes ONE or TWO arguments
        n: Number of Posts (mandatory or required)
        community_name : Name of community

    """
    params = request.args
    if params.get('n') is not None:
        no_of_post=int(params['n'])

        # got number of post, now fetching data using votes_api
        if params.get('community_name') is not None:
            community_name=str(params['community_name'])
            vote_resp = requests.get('http://127.0.0.1:{}/get?n={}&community_name={}&sorted=True'.format(VOTE_PORT_NO,no_of_post,community_name))

        else:
            vote_resp = requests.get('http://127.0.0.1:{}/get?n={}&sorted=True'.format(VOTE_PORT_NO,no_of_post))

        if vote_resp.status_code != 200:
            # This means something went wrong.
            raise APIError(vote_resp.status_code)

        vote_data=vote_resp.json()
        vote_scoted_list=[]  # store uuid in scorted form
        for dic in vote_data:
            vote_scoted_list.append(dic["uuid"])
        del vote_data
        # use these uuids to retrieve posts from post_api
        data={"uuid": vote_scoted_list}
        header = {"Content-type": "application/json",}
        post_resp = requests.post('http://localhost:{}/get_uuids'.format(POST_PORT_NO), data=json.dumps(data), headers=header)

        dict_post_resp = (post_resp.json())

        # generate RSS
        rss_list=[]
        for dic in dict_post_resp:
            date = datetime.fromtimestamp(int(dic['published']))

            item1 = Item(
                title = dic.get('title',"") or "", # get title form dict or empty string
                link = dic.get('url',"") or "",
                description = dic.get('description',"") or "",
                author = dic.get('username',"") or "",
                guid = Guid(dic.get('url',"") or ""),
                categories= dic.get('community_name',"") or "",
                pubDate = date)
            rss_list.append(item1)

        feed = Feed(
            title = "Reddit clone RSS Feed",
            link = "http://www.example.com/rss",
            description = "This is project-2 for CPSC-449 an RSS 2.0 feed",
            language = "en-US",
            lastBuildDate = datetime.now(),
            items = rss_list)

        response = make_response(feed.rss())
        response.headers.set('Content-Type', 'application/rss+xml')
        return response
    else:
        return custom_error("Enter value of n",404)



#5) The hot 25 posts to any community, ranked using Reddit’s “hot ranking” algorithm.
# http://localhost:5000/get_hot?n=25
def hot(score, date):
    """
        Calculate hot score
        score: Score of a given post (upvote-downvote)
        date : Time stamp
    """
    order = math.log(max(abs(score), 1), 10)
    sign = 1 if score > 0 else -1 if score < 0 else 0
    seconds = (date) - 1134028003
    return round(sign * order + seconds / 45000, 7)


@app.route('/get_hot', methods=["GET"])
def get_hot_post():
    """
        This route takes ONE arguments
        n: Number of Posts (mandatory or required)

    """
    params = request.args
    if params.get('n') is not None:
        no_of_post=int(params['n'])

        # got number of post, now fetching data using votes_api
        vote_resp = requests.get('http://127.0.0.1:{}/get_all'.format(VOTE_PORT_NO))
        if vote_resp.status_code != 200:
            # This means something went wrong.
            raise APIError(vote_resp.status_code)

        vote_data=vote_resp.json()

        hot_algo_dict={} # dict with key uuid and value hot_score
        for dic in vote_data:
            hot_score = hot( float(dic["score"]) , float(dic["published"])) # get hot score using hot method
            hot_algo_dict[dic["uuid"]]=hot_score

        uuid_list_to_post = sorted(hot_algo_dict, key=hot_algo_dict.get , reverse=True)
        uuid_list_to_post=uuid_list_to_post[0:no_of_post]
        del vote_data
        del hot_algo_dict

        data={"uuid": uuid_list_to_post}
        header = {"Content-type": "application/json",}
        post_resp = requests.post('http://localhost:{}/get_uuids'.format(POST_PORT_NO), data=json.dumps(data), headers=header)

        dict_post_resp = (post_resp.json())

        # generate RSS
        rss_list=[]
        for dic in dict_post_resp:
            date = datetime.fromtimestamp(int(dic['published']))

            item1 = Item(
                title = dic.get('title',"") or "", # get title form dict or empty string
                link = dic.get('url',"") or "",
                description = dic.get('description',"") or "",
                author = dic.get('username',"") or "",
                guid = Guid(dic.get('url',"") or ""),
                categories= dic.get('community_name',"") or "",
                pubDate = date)
            rss_list.append(item1)

        feed = Feed(
            title = "Reddit clone RSS Feed",
            link = "http://www.example.com/rss",
            description = "This is project-2 for CPSC-449 an RSS 2.0 feed",
            language = "en-US",
            lastBuildDate = datetime.now(),
            items = rss_list)

        response = make_response(feed.rss())
        response.headers.set('Content-Type', 'application/rss+xml')
        return response

    else:
        return custom_error("Enter value of n",404)




if __name__ == "__main__":
    app.run()
