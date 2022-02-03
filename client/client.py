import socket
import os
import sys
import argparse
from urllib.parse import urlparse

# Define a constant for our buffer size.
BUFFER_SIZE = 1024

# Define a constant for location where file gets saved.
SAVE_DESTINATION = "./"

# Function for retrieving the command line arguments.
def get_server_parameters():
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="URL to fetch with an HTTP GET request")
    args = parser.parse_args()

    # Check the URL passed in and make sure it's valid.  If so, keep track of
    # things for later.
    try:
        parsed_url = urlparse(args.url)
        if ((parsed_url.scheme != 'http') or (parsed_url.port == None) or (parsed_url.path == '') or (parsed_url.path == '/') or (parsed_url.hostname == None)):
            raise ValueError
        host = parsed_url.hostname
        port = parsed_url.port
        file_name = parsed_url.path
    except ValueError:
        print('Error:  Invalid URL.  Enter a URL of the form:  http://host:port/file')
        sys.exit(1)
    
    return host, port, file_name


# Function for setting up a socket and sending a request to the server.
def connect_to_server(host, port, file_name):
    print('Connecting to server ...')
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((host, port))
    except ConnectionRefusedError:
        print('Error:  That host or port is not accepting connections.')
        sys.exit(1)

    # The connection was successful, so we can prep and send our message.
    print('Connection to server established. Sending message...\n')
    message = prepare_get_message(host, port, file_name)
    client_socket.send(message.encode())

    return client_socket


# A function for creating HTTP GET messages.
def prepare_get_message(host, port, file_name):
    request = f'GET {file_name} HTTP/1.1\r\nHost: {host}:{port}\r\n\r\n' 
    return request


# Read a single line (ending with \n) from a socket and return it.
# We will strip out the \r and the \n in the process.
def get_line_from_socket(sock):
    done = False
    line = ''
    while (not done):
        char = sock.recv(1).decode()
        if (char == '\r'):
            pass
        elif (char == '\n'):
            done = True
        else:
            line = line + char
    return line


# Function to handle error messages sent by the server.
def handle_error_response(response_line, response_list, client_socket):
    headers_done = False
    bytes_to_read = 0
    location = ''

    print('Error:  An error response was received from the server.  Details:\n')
    print(response_line)
    
    while (not headers_done):
        header_line = get_line_from_socket(client_socket)
        print(header_line)
        header_list = header_line.split(' ')
        if (header_line == ''):
            headers_done = True
        elif (header_list[0] == 'Content-Length:'):
            bytes_to_read = int(header_list[1])
        elif (header_list[0] == 'Location:'):
            location = header_list[1]
    print_file_from_socket(client_socket, bytes_to_read)

    return location


# Read a file from the socket and print it out.  (For errors primarily.)
def print_file_from_socket(sock, bytes_to_read):
    bytes_read = 0
    while (bytes_read < bytes_to_read):
        chunk = sock.recv(BUFFER_SIZE)
        bytes_read += len(chunk)
        print(chunk.decode())


# Function to redirect the message to the right server upon recieving a 301 error.
def redirect_request(location):
    print('New server address recieved! Redirecting ...\n')

    # Parse the location returned from the balancer.
    parsed_url = urlparse(location)
    host = parsed_url.hostname
    port = parsed_url.port
    file_name = parsed_url.path

    # Now we try to make a connection to the server.
    client_socket = connect_to_server(host, port, file_name)

    # Receive the response from the server and start taking a look at it
    response_line = get_line_from_socket(client_socket)
    response_list = response_line.split(' ')

    # If an error is returned from the server, we dump everything sent and
    # exit right away.  
    if response_list[1] != '200':
        handle_error_response(response_line, response_list, client_socket)
        sys.exit(1)

    # If it's OK, we retrieve and write the file out.
    else:
        download_file(file_name, client_socket)


# Function to download the file from the socket connection.
def download_file(file_name, client_socket):
    headers_done = False
    print('Success:  Server is sending file.  Downloading it now.')

    # If requested file begins with a / we strip it off.
    while (file_name[0] == '/'):
        file_name = file_name[1:]

    # Go through headers and find the size of the file, then save it.
    bytes_to_read = 0
    while (not headers_done):
        header_line = get_line_from_socket(client_socket)
        header_list = header_line.split(' ')
        if (header_line == ''):
            headers_done = True
        elif (header_list[0] == 'Content-Length:'):
            bytes_to_read = int(header_list[1])
    save_file_from_socket(client_socket, bytes_to_read, file_name)


# Read a file from the socket and save it out.
def save_file_from_socket(sock, bytes_to_read, req_file):
    file_name = os.path.basename(req_file)

    with open(SAVE_DESTINATION + file_name, 'wb') as file_to_write:
        bytes_read = 0
        while (bytes_read < bytes_to_read):
            chunk = sock.recv(BUFFER_SIZE)
            bytes_read += len(chunk)
            file_to_write.write(chunk)
        file_to_write.close()


# Our main function.
def main():
    # Check command line arguments to retrieve a URL.
    host, port, file_name = get_server_parameters()

    # Now we try to make a connection to the server.
    client_socket = connect_to_server(host, port, file_name)

    # Receive the response from the server and start taking a look at it.
    response_line = get_line_from_socket(client_socket)
    response_list = response_line.split(' ')
    
    # If an error is returned from the server, we dump everything sent and
    # exit right away.  
    if response_list[1] != '200':
        location = handle_error_response(response_line, response_list, client_socket)
        
        # Handle a 301 redirection response differently than others.
        if response_list[1] != '301':
            sys.exit(1)
        else:
            redirect_request(location)

    # If it's OK, we retrieve and write the file out.
    else:
        download_file(file_name, client_socket)


if __name__ == '__main__':
    main()
