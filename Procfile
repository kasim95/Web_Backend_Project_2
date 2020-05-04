front: gunicorn3 --bind 127.0.0.1:5000 --access-logfile - --error-logfile - --log-level debug front_server:app
post: gunicorn3 --bind 127.0.0.1:5100 --access-logfile - --error-logfile - --log-level debug post_api:app
vote: gunicorn3 --bind 127.0.0.1:5200 --access-logfile - --error-logfile - --log-level debug vote_api:app
post_db: java -Djava.library.path=./dynamodb/DynamoDBLocal_lib -jar dynamodb/DynamoDBLocal.jar -sharedDb
