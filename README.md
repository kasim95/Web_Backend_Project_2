# CPSC 449 Web Backend Engineering
## Project-2
### Project Members:
* Raj Chhatbar (chhatbarraj@csu.fullerton.edu) | Role: Ops
* Mohammed Kasim Panjri (kasimp@csu.fullerton.edu) | Role: Dev 1 Post API
* Harlik Shah (shahharlik@csu.fullerton.edu) | Role: Dev 2 Vote API


### Note
Here we have used a scrapper to get the following values from Reddit, which is further divided into two seperate json file called posts.json and votes.json.
-- Posts --
```
uuid (unique ID) | username | title | url | description | published (timestamp) | community_name
```
-- Votes --
```
uuid (unique ID) | score (upvote-downvote) | community_name | published (timestamp)
```

Names of community available in database
```
csuf | news | Coronavirus | Python | computerscience | bitcoin
```

Total number of posts in database: 10,000

#### ---------------------Dev 3 - Aggregating posts and votes with a BFF---------------------------
1) Use this code for generating 1 instance each for post_db, post_api, vote_api and front_BFF
```
foreman start -m post_db=1,post=1,vote=1,front=1
```

2) Use the following URL for getting RSS feeds

* The 25 most recent posts to a particular community
```
http://localhost:5000/get?n=25&community_name=csuf
```
* The 25 most recent posts to any community
```
http://localhost:5000/get?n=25
```
* The top 25 posts to a particular community, sorted by score
```
http://localhost:5000/get_sorted?n=25&community_name=csuf
```
* The top 25 posts to any community, sorted by score
```
http://localhost:5000/get_sorted?n=25
```
* The hot 25 posts to any community, ranked using Reddit’s “hot ranking” algorithm.
```
http://localhost:5000/get_hot?n=25
```
