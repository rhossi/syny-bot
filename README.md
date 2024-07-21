# syny-bot


aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 851725530653.dkr.ecr.us-east-1.amazonaws.com/syny && docker run -it --name debug-fast-api 1e0c57a416b7 bash