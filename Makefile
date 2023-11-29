build:
	docker build -t pw/url-shortener:latest .

run: build
	docker run -it --network pocket-network --rm -p 8000:8000/tcp --name url-shortener pw/url-shortener:latest
