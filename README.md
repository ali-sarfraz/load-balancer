# Server Load Balancer
Load balancer to distribute client requests among a dynamic list of servers.

## Features

- Run HTTP Requests
- Controls Server Traffic
- Rnder Error Pages
- Download Server Files
  
## Run Locally

Clone the project

```bash
  git clone https://github.com/ali-sarfraz/load-balancer
```

## Demo

### Server
-------------------------------------------------------------------------------

To run an instance of a server, in the appropriate directory execute:

```bash
  python3 server.py
```

The server will report the port number that it is listening on for your client to use.
Place any files to transfer into the same directory as the server under the 'files' folder.
You may run multiple instances of this using multiple terminals.

### Balancer
-------------------------------------------------------------------------------

Before running the balancer, we need to add in the list of active servers to the
server configuration file, 'balancer_server_list.txt' in the balancer directory.
Note that the example I have in the submission highlights how it must be formatted,
but the basic syntax is as follows:

```
  hostname:port\n
  hostname:port\n
        .
        .
        .
  hostname:port\n
```

The newline character MUST be present after the last server, otherwise the formatting
will be incorrect and the final server will not be parsed correctly so please be vary 
of this and have a new line at the end of the config file.

Note that if there are no active servers that can be mapped properly from the config file
then the balancer will print out a warning and respond to the client with a 503 error
message in order to keep itself running and attempt to reconfigure the servers after the 
socket times out. With all the servers running and added to the config file, we can now
run the balancer.

To run the balancer in the appropriate directory, execute:

```bash
  python3 balancer.py
```

The balancer has a configurable timeout constant defined at the top called
'BALANCER_TIMEOUT' which is currently set at two minutes. It also uses the config file
so do not rename or move the file anywhere else. The balancer requests the 'plshelp.txt'
file from the server for computing their response times and recomputes this metric on
every socket timeout for efficient load balancing.

### Client
-------------------------------------------------------------------------------

To run the client, in the appropriate directory execute:

```bash
  python3 client.py http://host:port/file
```

where host is where the balancer is running (e.g. localhost), port is the port 
number reported by the balancer where it is running and file is the name of the 
file you want to retrieve. You can also request files straight from the servers themselves.

Note that the client will either print out the 301 error dialog and then proceed to 
reconnect with the appropriate server for downloading the file as intended, or
it might recieve the 503 error response if the config file is empty or doesn't
have any valid active servers.
