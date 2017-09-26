
The easiest way to get a test instance of Elasticsearch running is via docker. Once you've installed docker run the following commands to bring up an instance with persistent index data.

Create a directory to mount into the container for elastaticsearch to write index data to

`mkdir es_data`

Run the container (in the foreground, Ctrl+C to quit)

`docker run -t -i -p 9200:9200 -v $(pwd)/es_data:/usr/share/elasticsearch/data elasticsearch:2.4.6`

Or alternatively run the container in the background. You'll need to run `docker stop [container-id]` to quit

`docker run -d -p 9200:9200 -v $(pwd)/es_data:/usr/share/elasticsearch/data elasticsearch:2.4.6`

In a separate terminal get the container id

`docker ps`

Install kopf plugin; do this each time you start the container

`docker exec -t -i [container-id] bin/plugin install lmenezes/elasticsearch-kopf`

Try indexing a document to make sure things are working

    curl -XPUT "http://localhost:9200/movies/movie/1" -d'
    {
        "title": "The Godfather",
        "director": "Francis Ford Coppola",
        "year": 1972
    }'
    
Go to http://localhost:9200/_plugin/kopf to confirm that the `movies` index was created with 1 doc

Stop the container and start it again (remember to reinstall kopf), and check that the `movies` index is still there.

### index templates

example:

    curl -XPUT "http://localhost:9200/_template/sessions" -d @index_templates/sessions.json
