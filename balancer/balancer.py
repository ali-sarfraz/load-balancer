import socket
import os
import sys
import time
import random
import signal
import datetime

# Define a constant for our buffer size.
BUFFER_SIZE = 1024

# Define constant location for server config file.
SERVER_CONFIG_FILE = './balancer_server_list.txt'

# Define a constant test server file for checking server response times.
TEST_FILE = 'files/plshelp.txt'

# Define a constant timeout in seconds for the balancer to redo its performance calculations.
BALANCER_TIMEOUT = 120


# Signal handler for graceful exiting.
def signal_handler(sig, frame):
    print('Interrupt received, shutting down ...')
    sys.exit(0)


# Funtion for building and populating a list of server tuples based on their current
# availability and response times.
def analyze_server_performance():
    # Read the list of servers from the config file.
    server_list = init_server_list()

    # Populate the response times for each active server in the list.
    server_list = record_response_times(server_list)

    # Assign a priority to the servers based on response times.
    server_list = compute_server_availability(server_list)

    return server_list


# Function for reading in the server list config file.
def init_server_list():
    server_list = []
    server_count = 0
    
    with open(SERVER_CONFIG_FILE, 'r') as file_:
        while True: 
            server_count += 1
        
            # Get next line from file.
            line = file_.readline() 
        
            # if line is empty, end of file is reached.
            if not line: 
                break

            # Preliminary error checking to ensure format is valid to be split.
            if ':' not in line:
                print('Warning: Unable to store server at index',server_count,'because of invalid syntax!\n')
                continue
            
            # Split the config file based on its specific formatting.
            host_name = line.split(':')[0]
            port_number = line.split(':')[1][:-1]

            # Append each server hostname and port number, with an initial response
            # time and ratio coverage of 0.
            server_list.append((host_name, port_number, 0, 0))

    file_.close()
    return server_list

    
# Funtion for recording the response times for each server in the list.
# Does this by sending a request for a file and recording the time it 
# takes to recieve the response header.
def record_response_times(server_list):
    sorted_server_list = []

    for i, server in enumerate(server_list, start=1):
        print(f'Computing response time for server {i} ...')

        # Get the current time before making the request.
        time_before_request = time.time()
        
        # Attempt connecting to each server to see if they are valid/active.
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.connect((server[0], int(server[1])))
        except ConnectionRefusedError:
            print('Error:  That host or port is not accepting connections!')
            print('Removing server from active list...\n')
            continue

        # The connection was successful, so we can prep and send our message.
        message = prepare_get_message(server[0], server[1], TEST_FILE)
        server_socket.send(message.encode())
   
        # Receive the request response and body from the server.
        read_file_from_socket(server_socket)
        
        # Get the current time after making the request.
        time_after_request = time.time()
        
        # Evaluate the differnce to get the request execution time.
        time_delta = time_after_request - time_before_request

        print(f'Response time from server {i}: {time_delta}\n')

        # Update the response time in the tuple and add it to the sorted list.
        # Keep the ratio coverage at 0.
        sorted_server_list.append((server[0], server[1], time_delta, 0))
    
    # Sort the list in descending order of response times using the custom funtion get_time.
    sorted_server_list.sort(reverse = True, key = get_time)
    return sorted_server_list


# A function for creating HTTP GET messages.
def prepare_get_message(host, port, file_name):
    request = f'GET {file_name} HTTP/1.1\r\nHost: {host}:{port}\r\n\r\n' 
    return request


# Function for retrieving the contents of the test file sent by the server.
def read_file_from_socket(server_socket):
    headers_done = False

    # Retrieve the size of the file.
    while(not headers_done):
        # Receive the response from the server.
        header_line = get_line_from_socket(server_socket)
        header_list = header_line.split(' ')

        if (header_line == ''):
            headers_done = True
        elif (header_list[0] == 'Content-Length:'):
            bytes_to_read = int(header_list[1])
    
    # Loop through the file contents from the server to emulate a download.
    bytes_read = 0
    while (bytes_read < bytes_to_read):
        chunk = server_socket.recv(BUFFER_SIZE)
        bytes_read += len(chunk)


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


# Helper funtion for sorting the servers based on the response time.
def get_time(server):
    return server[2]


# Funtion for assigning the availability ratio values to the servers based on their response
# times. These ratios will depend on the number of active servers in the list.
def compute_server_availability(server_list):
    availability_factor = 0
    server_ratio_list = []

    # Increase the availability factor by the summation of the total on each iteration.
    # Will follow the sequence like: 1, 3, 6, 10 ...
    for i, server in enumerate(server_list, start=1):
        availability_factor += i

        # Append the availability factor to the last tuple index to complete the list.
        server_ratio_list.append((server[0], server[1], server[2], availability_factor))

    return server_ratio_list


# Function for setting up socket for accepting client requests.
def init_socket():
    # Create the socket.  We will ask this to work on any interface and to pick
    # a free port at random.  We'll print this out for clients to use.
    balancer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    balancer_socket.bind(('', 0))

    print('Will wait for client connections at port ' + str(balancer_socket.getsockname()[1]))
    balancer_socket.listen(1)

    return balancer_socket


# Function for processing the client request for clearing out headers and retrieving the filename.
def process_request(connection):
    print('Connection to client established, waiting to receive message...\n')

    # We obtain our request from the socket.  We look at the request to
    # figure out the requested filename.
    request = get_line_from_socket(connection)
    request_list = request.split()

    # This balnacer server doesn't care about headers, so we just clean them up.
    while (get_line_from_socket(connection) != ''):
        pass

    # If the requested file begins with a / character, we strip it off.
    req_file = request_list[1]
    while (req_file[0] == '/'):
        req_file = req_file[1:]
    
    return req_file


# Function for assigning a server by generating a random number and comparing it to the 
# server availability ratios.
def assign_server(server_list):
    # Ensure that there is atleast one server in the list.
    if not server_list:
        print('Warning: No active servers could be mapped from the config file!')
        print('Responding with error ...\n')
        return None

    # Retrieve the availability ratio of the last server.
    last_server = list(server_list[len(server_list)-1])

    # Generate a random number between the availability limits.
    random_number = random.randint(1, last_server[3])
    print(f'Randomly generated number is: {random_number}')

    # Each server has its own range based on its availability, so the selected server will
    # be the one whose range is hit by the random number.
    for i, server in enumerate(server_list, start=1):
        if random_number <= server[3]:
            print(f'Assigned to server {server[0]} on port {server[1]}\n')
            selected_server = server_list[i-1]
            break
    
    return selected_server


# Function for preparing and sending the redirection response to the client.
def redirect_request(selected_server, req_file, connection):
    # Retrieve the hostname and port number for the server to redirect to.
    new_host = selected_server[0]
    new_port = selected_server[1]

    # Concatenate the new URL location.
    new_location = f'http://{new_host}:{new_port}/{req_file}'
    print('Will redirect to:', new_location)

    # Respond with a 301 error to the client with the new location added into the headers.
    send_response_to_client(connection, '301', 'errors/301.html', new_location)


# Send the given response and file back to the client.
def send_response_to_client(sock, code, file_name, location=''):
    # Determine content type of file.
    if ((file_name.endswith('.html')) or (file_name.endswith('.htm'))):
        type = 'text/html'
    else:
        type = 'application/octet-stream'
    
    # Get size of file.
    file_size = os.path.getsize(file_name)

    # Construct header and send it.
    header = prepare_response_message(code) + 'Content-Type: ' + type + \
    '\r\nContent-Length: ' + str(file_size) + '\r\nLocation: ' + location + '\r\n\r\n'
    sock.send(header.encode())

    # Open the file, read it, and send it.
    with open(file_name, 'rb') as file_to_send:
        while True:
            chunk = file_to_send.read(BUFFER_SIZE)
            if chunk:
                sock.send(chunk)
            else:
                break


# Create an HTTP response.
def prepare_response_message(value):
    date = datetime.datetime.now()
    date_string = 'Date: ' + date.strftime('%a, %d %b %Y %H:%M:%S EDT')
    message = 'HTTP/1.1 '
    if value == '301':
        message = message + value + ' Moved Permanently\r\n' + date_string + '\r\n'
    elif value == '503':
        message = message + value + ' Service Unavailable\r\n' + date_string + '\r\n'
    return message


# Our main function.
def main():
    # Register our signal handler for shutting down.
    signal.signal(signal.SIGINT, signal_handler)

    # Analyze and sort the initial server performance metrics.
    server_list = analyze_server_performance()

    # Set up socket for accepting client requests within the timeout frame.
    balancer_socket = init_socket()
    balancer_socket.settimeout(BALANCER_TIMEOUT)

    # Keep the balancer running forever.
    while(1):
        try:
            print('Waiting for incoming client connection ...\n')
            conn, addr = balancer_socket.accept()
            print('Accepted connection from client address:', addr)

            # Retrieve the requested file's name, as this is the only parameter we care about.
            req_file = process_request(conn)
            
            # Assign a server from the list to handle the request.
            selected_server = assign_server(server_list)

            # If no server could be assigned, then respond with 503 error.
            if not selected_server:
                send_response_to_client(conn, '503', 'errors/503.html')
            else:
                # Prepare and perform the redirection operation.
                redirect_request(selected_server, req_file, conn)
            
            conn.close()

        except socket.timeout:
            print('Balancer timed out! Recalculating performance metrics ...\n')

            # Update the server list based on current server performance metrics.
            server_list = analyze_server_performance()


if __name__ == '__main__':
    main()
