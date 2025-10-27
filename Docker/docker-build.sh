docker rm -f pybakd-docker
docker rm -f pybakd
docker build -t pybakd -f Dockerfile.pybakd
docker build -t pybak-client -f Dockerfile.client
