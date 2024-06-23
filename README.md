# 

Run `source setup.sh` on your linux machine to install a virtual environment with necessary dependencies
and activate a venv on the shell.

## Recommended environment variable values
Refer to .env.example to create a .env file

## Database
By default, this app requires a postgresql database to run with the following properties below:
* port = 5433
* user = bottas
* db name = shitcoins

The app can run without a database by setting an environment variable in .env.

### How to run a database with docker
Instantiate a postgres docker instance with (in the docker directory):
`docker build -t wallet-db:latest .`
`docker run -d -p 5333:5432 -e POSTGRES_USER=bottas -e POSTGRES_HOST_AUTH_METHOD=trust --name wallet-db wallet-db:latest`

### Testing
Some tests require a test database to run:
`docker run -d -p 5332:5432 -e POSTGRES_USER=tests -e POSTGRES_HOST_AUTH_METHOD=trust --name test-wallet-db wallet-db:latest`

### How to check database records
Might need to make docker run sudoless
`docker exec -it wallet-db sh`
`psql -U bottas -d shitcoins`
`Select count(*) from wallet;` or `Select * from wallet;`
