# CPSC 449 Web Backend Engineering
## Project-2
### Project Members:
* Mohammed Kasim Panjri (kasimp@csu.fullerton.edu) | Role: Dev 1
* Harlik Shah (shahharlik@csu.fullerton.edu) | Role: Dev 2
* Raj Chhatbar (chhatbarraj@csu.fullerton.edu) | Role: Dev 3


Here we have used Reddit API to retrieve posts from Reddit. These posts are used to populate the DynamoDB posts table and Redis votes table key-value store.

The uuid used is generated using Python uuid module and then converted to base36 encoding similar to how Reddit generates their ids.
All other attributes are retrieved from the API itself.

Attributes for post database in DynamoDB
```
uuid (unique ID) | username | title | url | description | published (timestamp) sort_key | community_name
```
Attributes for vote database in Redis
```
uuid (unique ID) | score (upvote-downvote) sort_key | community_name | published (timestamp) sort_key
```

Names of communities available in database
```
csuf | news | Coronavirus | Python | computerscience | bitcoin
```

Total number of posts in database: 10,000

#### Note by Dev-1

We have found inconsistent behavior of DynamoDB local populated on one computer having issues running on another computer.

In order to fix it, delete all the files in dynamodb/ dir and replace it with files from dynamodb_local_latest.zip
Run dynamodb instance in 1 terminal using dynamo.sh script and run `flask init` on another terminal. This will repopulate the DynamoDB posts table.
The whole process will take around 20 minutes on a HDD and 5 minutes on an SSD.


#### -----------------Dev 1 - Porting the posting microservice to Amazon DynamoDB Local----------------------
* Create a new post
```shell script
curl -i -X POST -H 'Content-Type:application/json' -d '{"title":"Test post", "description":"This is a test post", "username":"some_guy_or_gal", "community_name":"449", "uuid":"9H1TQXRQQ8JAL7HE1OSWN6K5Z", "published":"1588265108"}' http://localhost:5100/create
```
* Delete an existing post
```shell script
curl -i -X DELETE http://localhost:5100/delete?uuid=9H1TQXRQQ8JAL7HE1OSWN6K5Z&published=1588265108
```
* Retrieve an existing post
```shell script
curl -i http://localhost:5100/get?uuid=CFXBWE9BP5VO51HNA0DE1QNIV
```
* List n most recent posts to a particular community
```shell script
curl -i http://localhost:5100/get?n=10&community_name=csuf&recent=True
```
* List n most recent posts to any community
```shell script
curl -i http://localhost:5100/get?n=10&recent=True
```
* Retrieve multiple posts using a list of uuids
```shell script
curl -i -X POST -H 'Content-Type:application/json' -d '{"uuid":["CQHYO2LBB1GFRIYVTH28TUEMV", "BAOL4MNKJWB2L04BC48IMKE53", "BAOL4EZ1LALJXK49HTOL84FBR", "CYBDDVCRY049BOWC2G0U2432V", "C36AVEOBBYY9BVV6LQBF74H3R"]}' http://localhost:5100/get_uuids
```

#### ---------------------Dev 2 - Porting to the voting microservice to Redis---------------------------
1. Upvote a post
```shell script
curl -i -X POST -H 'Content-Type:application/json' -d '{"uuid":"QWERTYMXW3TICIOQBCND86Z0D3"}' http://localhost:5200/upvotes
```
2. Downvote a post
```shell script
curl -i -X POST -H 'Content-Type:application/json' -d '{"uuid":"QWERTYMXW3TICIOQBCND86Z0D3"}' http://localhost:5200/downvotes
```
3. Report the number of scores (downvotes-upvotes) for a post:
```shell script
curl -i -X GET 'http://localhost:5200/get?uuid=HARLIKMXW3TICIOQBCND86Z0D3'
```
4. List the n top-scoring posts to any community:
```shell script
curl -i -X GET 'http://localhost:5200/get?n=25&community_name=csuf'
```
5. Given a list of post identifiers, return the list sorted by score.:
```shell script
curl -i -X POST -H 'Content-Type:application/json' -d '{"n":3, "sorted":"True", "uuid":["HARLIKMXW3TICIOQBCND86Z0D3", "C59OGYZWADQVRCCOREWSOUP3R", "ASD3C3PH204FAQ2EEHZY8IG7R"]}' http://localhost:5200/getlist;
```
6. Create operation
```shell script
curl -i -X POST -H 'Content-Type:application/json' -d '{"uuid":"HARLIKMXW3TICIOQBCND86Z0D3", "community_name":"csuf", "score":"0", "published":"15058265108"}' http://localhost:5200/create_vote
```
7. Delete operation
```shell script
curl -i -X DELETE 'http://localhost:5200/delete_vote?uuid=CAEPJIPK49FSWZ4K02JBAFYJB'
```
8. Retrieve all operations
```shell script
curl -i -X GET 'http://localhost:5200/get_all'
```


#### ---------------------Dev 3 - Aggregating posts and votes with a BFF---------------------------
* As mail reader was giving output scored by published date, I have used a crome extension called "Slick RSS" to verify the RSS feeds.

1) Use this code for generating 1 instance each for post_db, post_api, vote_api and front_BFF
```shell script
foreman start -m post_db=1,post=1,vote=1,front=1
```

2) Use the following URL to get RSS feeds

  * The 25 most recent posts to a particular community
```
http://localhost:5000/get?n=25&community_name=csuf
```
![rss_e_5](https://user-images.githubusercontent.com/33519807/81129401-0b8cd000-8ef9-11ea-8f93-2c5bf6bedf39.PNG)

  * The 25 most recent posts to any community
```
http://localhost:5000/get?n=25
```
![rss_e_4](https://user-images.githubusercontent.com/33519807/81129399-0891df80-8ef9-11ea-9443-d9de7005b7dd.PNG)
  * The top 25 posts to a particular community, sorted by score
```
http://localhost:5000/get_sorted?n=25&community_name=csuf
```
![rss_e_2](https://user-images.githubusercontent.com/13769406/81118357-8d6f0000-8edd-11ea-8daa-d2532512b85a.PNG)


  * The top 25 posts to any community, sorted by score
```
http://localhost:5000/get_sorted?n=25
```
![rss_e_1](https://user-images.githubusercontent.com/13769406/81118367-8fd15a00-8edd-11ea-8526-5711d9498d71.PNG)
  * The hot 25 posts to any community, ranked using Reddit’s “hot ranking” algorithm.
```
http://localhost:5000/get_hot?n=25
```
![rss_e_3](https://user-images.githubusercontent.com/13769406/81118346-8b0ca600-8edd-11ea-8462-718c9c08a310.PNG)


## License
[MIT](https://choosealicense.com/licenses/mit/)
