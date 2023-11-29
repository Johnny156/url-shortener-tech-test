## Getting Started - John Muniz Implementation

To begin the project, clone this repository to your local machine:

```commandline
git clone https://github.com/Johnny156/url-shortener-tech-test.git
```

This repository contains the implementation of a URL Shortener web service written in Python 3.11
using the [FastAPI](https://fastapi.tiangolo.com/) framework.

The API endpoints found in `server.py` have been implemented with proper business logic supported by a Redis datastore.

A Makefile, Dockerfile, and docker-compose.yml are also included for your convenience to run and test the web service.

While Docker is not required to run this service, this implementation utilized Docker to help manage multiple instances
and a running service of Redis from the [Redis Docker Official Image](https://www.docker.com/blog/how-to-use-the-redis-docker-official-image/).

### Prerequisites

The Redis Docker Official Image needs to be pulled in order to create the Redis container this can be achieved with a simple pull:
```commandline
docker pull redis
```

If you are not running the services with docker-compose a custom network will need to created so the service containers can communicate with the Redis container:

```commandline
docker create network pocket-network
```

This `pocket-network` should be referred to in any standalone containers run commands. 

### Running the service

#### docker-compose

Included in the project is a `docker-compose.yml` file that should encapsulate a running demo with two instances of the shortener container running on ports `8000` and `8001`, and the running Redis container:
```commandline
docker compose up
```
Included, is also a Makefile target which does the same thing:
```commandline
make compose
```

#### Makefile
I have modified the Makefile to include the custom network in the Docker run commands, and another target to spin up the Redis container:

```commandline
make redis
make run
```

This command will build a new Docker image (`pw/url-shortener:latest`) and start a container
instance in interactive mode.

The web service will run on port 8000, and the default Redis port is 6379.

### Testing

The Swagger UI was leveraged as a means of testing the endpoints, although any HTTP client (e.g. Postman, Browser/Dev tools) should suffice:
* `POST /url/shorten`
   *  Request Body, Content-Type: application/json, example request
   *  ```commandline
      {
        "url": "https://www.pocketworlds.com"
      }
      ```
* `GET /r/{short_url}`
   * The endpoint should return a 404, if the `short_url` is unknown
   * To test a known `short_url`, I recommend input the fully qualified short URL in the browser as this endpoint should return a redirect.

#### Expected Behaviors
* Known URLs shortened previous SHOULD return back the same shortened URL
* the `/url/shorten` endpoint SHOULD validate for proper URL formatting. (But not specifically http!)
* Reusing the included models and endpoint, the endpoints respond in JSON.

### Known Quirks
* While the Redis container is configured to have persistence, it will only have persistence across startup/shutdown of the SAME container. 
If the container is destroyed and remade, it will lose all its data. Proper mounting of Docker volumes would solve this issue, or moving to some sort of cloud Redis server (e.g. AWS Elasticache)
* The keys stored in Redis currently do not expire, this could be configured have tokens have a certain time-to-live and expire.
* The URL shortener tries to generate a (configurable) 8-character random unique token to shorten the URL up to 10 times, and will error out if the attempts are exceeded.

