# formation-lab-docker

This project contains several labs, each demonstrating a different Docker configuration. Follow the instructions below for each lab.

## Lab 1: Socket Lab

1. Change to the socket folder:
`cd 1.socket`

2. Build the Docker image:
`docker build -t socket-lab .`

3. Run the container while mounting the current folder (which exposes the socket):
`docker run -v /var/run/docker.sock:/var/run/docker.sock -p 8080:8080 socket-lab`

Go to http://localhost:8080 and try to exploit a misconfiguration to escape the Docker container and exec into the host.

- [ ] I can execute commands on my local machine through the webapp: for example, I can read files on my local machine.

## Lab 2: Root Lab

1. Change to the root folder:
`cd 2.root`
2. Build the Docker image (ensure you have a valid Dockerfile in the folder):
`docker build -t root-lab .`
3. Run the container with privileged mode and using the root user:
`docker run --rm --privileged --security-opt apparmor=unconfined -p 8080:8080 root-lab`

Go to http://localhost:8080 and try to exploit a misconfiguration to escape the Docker container and exec into the host.

- [ ] I can execute commands on my local machine through the webapp: for example, I can read files on my local machine.

## Lab 3: Capabilities Lab

1. Change to the capabilities folder:
`cd 3.capabilities`

2. Build the Docker image:
`docker build -t capabilities-lab .`

3. Run the container with permissive capabilities:
`docker run --rm --cap-add=ALL --pid=host --security-opt apparmor=unconfined --name capabilities-lab -p 8080:8080 capabilities-lab`

Go to http://localhost:8080 and try to exploit a misconfiguration to escape the Docker container and exec into the host.

- [ ] I can execute commands on my local machine through the webapp: for example, I can read files on my local machine.
