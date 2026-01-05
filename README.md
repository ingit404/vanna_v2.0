This repo contains the working code+ docker image of the vanna ai for rupeek.
As of on november 12 2025

#Clone the Repository.
1. clone the repo
2. set your own environement variables
3. docker image is at  dockerhub username:ingit2025   "https://hub.docker.com/repositories/ingit2025"

# Use of docker image
1.pull the docker image (ingit2025/vanna:x.xv)
2.run the docker image with the command the command in terminal
     docker run --name vanna --env-file <path_to_env_file> -p 5000:5000 vanna:x.xv
3. for the first run it will take time
4. for next runs after starting the container wait for 10-15 seconds and go to [http://localhost:5000/](http://localhost:5000/) to use the vanna FlaskUI
   
